"""FastAPI application with async endpoints and caching"""
from fastapi import FastAPI, Depends, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from sqlalchemy.orm import selectinload
from typing import Optional
import redis.asyncio as aioredis
import json
import os
import logging
import subprocess
import uuid
from contextlib import asynccontextmanager
from urllib.parse import urlparse
from datetime import datetime, timezone

from .config import get_settings
from .database import get_db, init_db, close_db, engine
from .models import MediaPost, ChildPost, User, Collection, CollectionItem, UserPreference
from .schemas import (
    MediaPostSchema, StatsResponse, PromptGalleryItem, PromptStatsResponse,
    CollectionCreate, CollectionUpdate, CollectionSchema, CollectionWithItemsSchema,
    UserPreferenceSchema, UserPreferenceUpdate,
    ImportRequest, ImportResponse
)
from .services.wan_service import get_wan_service
from .services.rife_service import get_rife_service
from .video_frame_utils import extract_first_and_last_frame_hashes, frames_match

# Setup logging
logger = logging.getLogger(__name__)

settings = get_settings()

# Redis client
redis_client: Optional[aioredis.Redis] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle management for database and Redis"""
    global redis_client
    
    # Startup
    print("🚀 Starting up...")
    
    # Initialize database
    await init_db()
    print("✅ Database initialized")
    
    # Initialize Redis
    try:
        redis_client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        await redis_client.ping()
        print("✅ Redis connected")
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")
        print("⚠️  Continuing without cache")
        redis_client = None
    
    yield
    
    # Shutdown
    print("🛑 Shutting down...")
    
    if redis_client:
        await redis_client.close()
        print("✅ Redis closed")
    
    await close_db()
    print("✅ Database closed")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# CORS middleware - allow all origins for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins including file:// protocol
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_cache(key: str) -> Optional[str]:
    """Get value from Redis cache"""
    if redis_client is None:
        return None
    try:
        return await redis_client.get(key)
    except Exception as e:
        print(f"Cache get error: {e}")
        return None


async def set_cache(key: str, value: str, ttl: int = None) -> None:
    """Set value in Redis cache"""
    if redis_client is None:
        return
    try:
        if ttl is None:
            ttl = settings.cache_ttl
        await redis_client.setex(key, ttl, value)
    except Exception as e:
        logger.error(f"Cache set error: {e}")


async def get_default_user(db: AsyncSession) -> User:
    """Get the first/default user (single-user app)"""
    result = await db.execute(select(User).limit(1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=500, detail="No user found. Run import first.")
    return user


def make_naive_utc(dt: datetime) -> datetime:
    """Convert timezone-aware datetime to naive UTC"""
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "docs": "/api/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    health = {
        "status": "healthy",
        "database": "unknown",
        "redis": "unknown"
    }
    
    # Check database
    try:
        async with engine.begin() as conn:
            await conn.execute(select(1))
        health["database"] = "connected"
    except Exception as e:
        health["database"] = f"error: {str(e)}"
        health["status"] = "unhealthy"
    
    # Check Redis
    if redis_client:
        try:
            await redis_client.ping()
            health["redis"] = "connected"
        except Exception as e:
            health["redis"] = f"error: {str(e)}"
    else:
        health["redis"] = "not configured"
    
    return health


@app.get(f"{settings.api_prefix}/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Get gallery statistics with caching"""
    
    # Try cache first
    cache_key = "stats"
    cached = await get_cache(cache_key)
    if cached:
        return json.loads(cached)
    
    # Query database
    total_items = await db.scalar(select(func.count(MediaPost.id)))
    total_videos = await db.scalar(select(func.count(ChildPost.id)))
    liked_items = await db.scalar(
        select(func.count(MediaPost.id)).where(MediaPost.like_status == True)
    )
    
    # Get model statistics
    model_query = select(
        MediaPost.model_name,
        func.count(MediaPost.id).label('count')
    ).where(
        MediaPost.model_name.isnot(None)
    ).group_by(
        MediaPost.model_name
    ).order_by(
        func.count(MediaPost.id).desc()
    )
    
    result = await db.execute(model_query)
    models = [
        {"name": row[0], "count": row[1]}
        for row in result.all()
    ]
    
    stats = {
        "totalItems": total_items or 0,
        "totalVideos": total_videos or 0,
        "likedItems": liked_items or 0,
        "models": models
    }
    
    # Cache for 5 minutes
    await set_cache(cache_key, json.dumps(stats))

    return stats


@app.get(f"{settings.api_prefix}/users")
async def get_users(db: AsyncSession = Depends(get_db)):
    """Get all users"""
    result = await db.execute(select(User))
    users = result.scalars().all()
    return [{"id": str(user.id), "username": user.username, "email": user.email} for user in users]


@app.get(f"{settings.api_prefix}/media", response_model=list[MediaPostSchema])
async def get_media(
    media_type: Optional[str] = Query(None, alias="type", description="Filter by media type (or 'all')"),
    liked: Optional[str] = Query(None, description="Filter by like status ('all', 'liked', 'unliked')"),
    model: Optional[str] = Query(None, description="Filter by model name (or 'all')"),
    mode: Optional[str] = Query(None, description="Filter by child mode ('all', 'custom', 'normal')"),
    has_custom_videos: Optional[bool] = Query(None, description="Filter posts with custom child videos"),
    search: Optional[str] = Query(None, description="Search in prompts"),
    sort: Optional[str] = Query("date_desc", description="Sort order: date_desc, date_asc, likes, model, random"),
    skip: int = Query(0, ge=0, description="Skip N records"),
    limit: int = Query(50, ge=1, le=100, description="Limit results"),
    db: AsyncSession = Depends(get_db)
):
    """Get media posts with filters and pagination"""

    # Build query with eager loading to prevent N+1
    query = select(MediaPost).options(
        selectinload(MediaPost.child_posts)
    )

    # Apply filters - handle "all" as no filter
    if media_type and media_type != "all":
        query = query.where(MediaPost.media_type == media_type)

    # Handle liked filter: "all", "liked", "unliked", or empty
    if liked and liked != "all":
        if liked == "liked":
            query = query.where(MediaPost.like_status == True)
        elif liked == "unliked":
            query = query.where(MediaPost.like_status == False)

    if model and model != "all":
        query = query.where(MediaPost.model_name == model)

    # Filter by child post mode
    if mode and mode != "all":
        query = query.join(MediaPost.child_posts).where(ChildPost.mode == mode).distinct()

    # Filter posts that have custom child videos
    if has_custom_videos:
        query = query.join(MediaPost.child_posts).where(ChildPost.mode == "custom").distinct()

    if search:
        search_term = f"%{search}%"
        # Search in both parent prompts and child custom prompts
        query = query.outerjoin(MediaPost.child_posts).where(
            (MediaPost.prompt.ilike(search_term)) |
            (MediaPost.original_prompt.ilike(search_term)) |
            (ChildPost.original_prompt.ilike(search_term))
        ).distinct()

    # Apply sorting
    if sort == "date_asc":
        query = query.order_by(MediaPost.create_time.asc())
    elif sort == "likes":
        query = query.order_by(MediaPost.like_status.desc(), MediaPost.create_time.desc())
    elif sort == "model":
        query = query.order_by(MediaPost.model_name.asc(), MediaPost.create_time.desc())
    elif sort == "random":
        query = query.order_by(func.random())
    else:  # date_desc (default)
        query = query.order_by(MediaPost.create_time.desc())
    
    # Apply pagination
    query = query.offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    posts = result.scalars().all()

    # Merge identical images (same media_url) and consolidate their children
    media_url_map = {}
    merged_posts = []

    for post in posts:
        if post.media_url in media_url_map:
            # Found duplicate - merge children into the existing post
            primary_post = media_url_map[post.media_url]
            # Add all children from this duplicate to the primary
            for child in post.child_posts:
                # Avoid duplicates based on child ID
                if not any(c.id == child.id for c in primary_post.child_posts):
                    primary_post.child_posts.append(child)
        else:
            # First occurrence - mark as primary
            media_url_map[post.media_url] = post
            merged_posts.append(post)

    return merged_posts


@app.get(f"{settings.api_prefix}/models")
async def get_models(db: AsyncSession = Depends(get_db)):
    """Get list of available models with counts"""
    
    # Try cache first
    cache_key = "models:all"
    cached = await get_cache(cache_key)
    if cached:
        return json.loads(cached)
    
    # Query for parent post models
    parent_query = select(
        MediaPost.model_name,
        func.count(MediaPost.id).label('count')
    ).where(
        MediaPost.model_name.isnot(None)
    ).group_by(
        MediaPost.model_name
    )
    
    # Query for child post models
    child_query = select(
        ChildPost.model_name,
        func.count(ChildPost.id).label('count')
    ).where(
        ChildPost.model_name.isnot(None)
    ).group_by(
        ChildPost.model_name
    )
    
    parent_result = await db.execute(parent_query)
    child_result = await db.execute(child_query)
    
    # Combine results
    models = {}
    for row in parent_result.all():
        if row[0]:
            models[row[0]] = models.get(row[0], 0) + row[1]
    
    for row in child_result.all():
        if row[0]:
            models[row[0]] = models.get(row[0], 0) + row[1]
    
    # Sort by count
    sorted_models = [
        {"name": name, "count": count}
        for name, count in sorted(models.items(), key=lambda x: x[1], reverse=True)
    ]
    
    result = {"models": sorted_models}
    
    # Cache for 10 minutes
    await set_cache(cache_key, json.dumps(result), ttl=600)
    
    return result


@app.get(f"{settings.api_prefix}/models/status")
async def get_models_status():
    """Check availability and installation status of AI models"""
    from pathlib import Path
    import torch

    status = {
        "wan": {
            "name": "Wan 2.1 Image-to-Video",
            "available": False,
            "installed": False,
            "size_gb": 28,
            "description": "14B parameter model for generating 3-7 second videos from images"
        },
        "svd": {
            "name": "Stable Video Diffusion",
            "available": False,
            "installed": False,
            "size_gb": 12,
            "description": "Generates 2 second videos from images (14 frames)"
        },
        "rife": {
            "name": "RIFE Frame Interpolation",
            "available": False,
            "installed": False,
            "size_mb": 800,
            "description": "AI-powered smooth transitions for video merging"
        },
        "gpu": {
            "cuda_available": torch.cuda.is_available(),
            "mps_available": torch.backends.mps.is_available() if hasattr(torch.backends, 'mps') else False,
            "device": "cpu"
        }
    }

    # Check Wan availability
    try:
        from app.services.wan_service import WAN_AVAILABLE
        status["wan"]["available"] = WAN_AVAILABLE
        # Check if model is actually downloaded (try to find model cache)
        from transformers import AutoModel
        from pathlib import Path
        cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
        wan_models = list(cache_dir.glob("models--Wan-AI--Wan*"))
        status["wan"]["installed"] = len(wan_models) > 0 if cache_dir.exists() else False
    except Exception as e:
        logger.warning(f"Error checking Wan status: {e}")

    # Check SVD availability
    try:
        from app.services.svd_service import SVDService
        status["svd"]["available"] = True
        # Check if model is downloaded
        cache_dir = Path.home() / ".cache" / "huggingface" / "hub"
        svd_models = list(cache_dir.glob("models--stabilityai--stable-video*"))
        status["svd"]["installed"] = len(svd_models) > 0 if cache_dir.exists() else False
    except Exception as e:
        logger.warning(f"Error checking SVD status: {e}")

    # Check RIFE availability
    try:
        rife_path = Path(__file__).parent / "services" / "Practical-RIFE"
        train_log = rife_path / "train_log"
        flownet = train_log / "flownet.pkl"

        status["rife"]["available"] = train_log.exists() and flownet.exists()
        status["rife"]["installed"] = status["rife"]["available"]

        # Try to import RIFE model
        if status["rife"]["available"]:
            try:
                import sys
                sys.path.insert(0, str(rife_path))
                from model.RIFE import Model
                status["rife"]["can_import"] = True
            except:
                status["rife"]["can_import"] = False
                status["rife"]["available"] = False
    except Exception as e:
        logger.warning(f"Error checking RIFE status: {e}")

    # Determine best GPU device
    if status["gpu"]["cuda_available"]:
        status["gpu"]["device"] = "cuda"
    elif status["gpu"]["mps_available"]:
        status["gpu"]["device"] = "mps"

    return status


@app.get(f"{settings.api_prefix}/search")
async def search_media(
    q: str = Query(..., min_length=2, description="Search query"),
    db: AsyncSession = Depends(get_db)
):
    """Full-text search across prompts"""
    
    search_term = f"%{q}%"
    
    # Search in media posts
    query = select(MediaPost).options(
        selectinload(MediaPost.child_posts)
    ).where(
        (MediaPost.prompt.ilike(search_term)) |
        (MediaPost.original_prompt.ilike(search_term))
    ).order_by(
        MediaPost.create_time.desc()
    ).limit(50)
    
    result = await db.execute(query)
    posts = result.scalars().all()
    
    return {
        "query": q,
        "results": [MediaPostSchema.model_validate(post) for post in posts],
        "count": len(posts)
    }


@app.get(f"{settings.api_prefix}/prompts")
async def get_prompts(
    limit: int = Query(100, ge=1, le=500, description="Limit results"),
    sort: str = Query("usage", description="Sort by: usage, recent, alpha"),
    db: AsyncSession = Depends(get_db)
):
    """Get all unique prompts with usage statistics"""

    # Try cache first
    cache_key = f"prompts:list:{limit}:{sort}"
    cached = await get_cache(cache_key)
    if cached:
        return json.loads(cached)

    # Collect all prompts from parent posts and custom child posts
    prompts_data = {}

    # Get parent post prompts
    parent_query = select(
        MediaPost.original_prompt,
        func.count(MediaPost.id).label('count'),
        func.min(MediaPost.create_time).label('first_used'),
        func.max(MediaPost.create_time).label('last_used')
    ).where(
        MediaPost.original_prompt.isnot(None),
        MediaPost.original_prompt != ''
    ).group_by(MediaPost.original_prompt)

    parent_result = await db.execute(parent_query)
    for row in parent_result.all():
        prompt, count, first, last = row
        if prompt and prompt.strip():
            prompts_data[prompt] = {
                "prompt": prompt,
                "usage_count": count,
                "mode_type": "parent",
                "first_used": first,
                "last_used": last
            }

    # Get custom child post prompts
    child_query = select(
        ChildPost.original_prompt,
        func.count(ChildPost.id).label('count'),
        func.min(ChildPost.create_time).label('first_used'),
        func.max(ChildPost.create_time).label('last_used')
    ).where(
        ChildPost.mode == 'custom',
        ChildPost.original_prompt.isnot(None),
        ChildPost.original_prompt != ''
    ).group_by(ChildPost.original_prompt)

    child_result = await db.execute(child_query)
    for row in child_result.all():
        prompt, count, first, last = row
        if prompt and prompt.strip():
            if prompt in prompts_data:
                prompts_data[prompt]["usage_count"] += count
                prompts_data[prompt]["mode_type"] = "both"
                prompts_data[prompt]["first_used"] = min(prompts_data[prompt]["first_used"], first)
                prompts_data[prompt]["last_used"] = max(prompts_data[prompt]["last_used"], last)
            else:
                prompts_data[prompt] = {
                    "prompt": prompt,
                    "usage_count": count,
                    "mode_type": "custom",
                    "first_used": first,
                    "last_used": last
                }

    # Sort prompts
    prompts_list = list(prompts_data.values())
    if sort == "usage":
        prompts_list.sort(key=lambda x: x["usage_count"], reverse=True)
    elif sort == "recent":
        prompts_list.sort(key=lambda x: x["last_used"], reverse=True)
    elif sort == "alpha":
        prompts_list.sort(key=lambda x: x["prompt"].lower())

    # Limit results
    prompts_list = prompts_list[:limit]

    result = {"prompts": prompts_list, "total": len(prompts_data)}

    # Cache for 10 minutes
    await set_cache(cache_key, json.dumps(result, default=str), ttl=600)

    return result


@app.get(f"{settings.api_prefix}/prompts/stats", response_model=PromptStatsResponse)
async def get_prompt_stats(db: AsyncSession = Depends(get_db)):
    """Get prompt usage statistics"""

    # Try cache first
    cache_key = "prompts:stats"
    cached = await get_cache(cache_key)
    if cached:
        return json.loads(cached)

    # Count unique parent prompts
    parent_count = await db.scalar(
        select(func.count(func.distinct(MediaPost.original_prompt))).where(
            MediaPost.original_prompt.isnot(None),
            MediaPost.original_prompt != ''
        )
    )

    # Count unique custom prompts
    custom_count = await db.scalar(
        select(func.count(func.distinct(ChildPost.original_prompt))).where(
            ChildPost.mode == 'custom',
            ChildPost.original_prompt.isnot(None),
            ChildPost.original_prompt != ''
        )
    )

    # Count child posts by mode
    custom_mode_count = await db.scalar(
        select(func.count(ChildPost.id)).where(ChildPost.mode == 'custom')
    ) or 0

    normal_mode_count = await db.scalar(
        select(func.count(ChildPost.id)).where(ChildPost.mode == 'normal')
    ) or 0

    total_child_posts = custom_mode_count + normal_mode_count
    custom_percentage = (custom_mode_count / total_child_posts * 100) if total_child_posts > 0 else 0

    # Get most used prompts (top 10)
    most_used_query = select(
        ChildPost.original_prompt,
        func.count(ChildPost.id).label('count')
    ).where(
        ChildPost.mode == 'custom',
        ChildPost.original_prompt.isnot(None),
        ChildPost.original_prompt != ''
    ).group_by(
        ChildPost.original_prompt
    ).order_by(
        func.count(ChildPost.id).desc()
    ).limit(10)

    result = await db.execute(most_used_query)
    most_used = [{"prompt": row[0], "count": row[1]} for row in result.all()]

    stats = {
        "total_unique_prompts": (parent_count or 0) + (custom_count or 0),
        "total_custom_prompts": custom_count or 0,
        "total_parent_prompts": parent_count or 0,
        "custom_mode_count": custom_mode_count,
        "normal_mode_count": normal_mode_count,
        "custom_mode_percentage": round(custom_percentage, 2),
        "most_used_prompts": most_used
    }

    # Cache for 10 minutes
    await set_cache(cache_key, json.dumps(stats), ttl=600)

    return stats


@app.get(f"{settings.api_prefix}/prompts/search")
async def search_prompts(
    q: str = Query(..., min_length=2, description="Search query"),
    db: AsyncSession = Depends(get_db)
):
    """Search for prompts matching query"""

    search_term = f"%{q}%"

    # Search in custom child prompts
    query = select(
        ChildPost.original_prompt,
        func.count(ChildPost.id).label('count')
    ).where(
        ChildPost.mode == 'custom',
        ChildPost.original_prompt.ilike(search_term)
    ).group_by(
        ChildPost.original_prompt
    ).order_by(
        func.count(ChildPost.id).desc()
    ).limit(50)

    result = await db.execute(query)
    prompts = [{"prompt": row[0], "count": row[1]} for row in result.all()]

    return {"query": q, "prompts": prompts, "count": len(prompts)}


@app.get(f"{settings.api_prefix}/videos/by-prompt")
async def get_videos_by_prompt(
    prompt: str = Query(..., min_length=2, description="Exact or partial prompt text"),
    exact: bool = Query(False, description="Exact match only"),
    db: AsyncSession = Depends(get_db)
):
    """Get all videos using a specific prompt"""

    if exact:
        # Exact match
        query = select(MediaPost).options(
            selectinload(MediaPost.child_posts)
        ).join(MediaPost.child_posts).where(
            ChildPost.mode == 'custom',
            ChildPost.original_prompt == prompt
        ).distinct().order_by(MediaPost.create_time.desc())
    else:
        # Partial match
        search_term = f"%{prompt}%"
        query = select(MediaPost).options(
            selectinload(MediaPost.child_posts)
        ).join(MediaPost.child_posts).where(
            ChildPost.mode == 'custom',
            ChildPost.original_prompt.ilike(search_term)
        ).distinct().order_by(MediaPost.create_time.desc())

    result = await db.execute(query)
    posts = result.scalars().all()

    return {
        "prompt": prompt,
        "exact_match": exact,
        "posts": [MediaPostSchema.model_validate(post) for post in posts],
        "count": len(posts)
    }


@app.post(f"{settings.api_prefix}/prompts/generate")
async def generate_prompts(
    base_prompt: str = Body(..., description="Base prompt to generate variations from"),
    num_variations: int = Body(5, ge=1, le=20, description="Number of variations to generate"),
    variation_type: str = Body("detailed", description="Type of variations: detailed, perspective, action, setting, mixed")
):
    """
    Generate prompt variations using Ollama (local LLM).
    Creates creative, AI-powered variations completely locally - no API costs!
    """
    import httpx

    # Build the system prompt based on variation type
    variation_instructions = {
        "detailed": "Add rich visual details, quality modifiers, and artistic descriptions",
        "perspective": "Vary camera angles, viewpoints, and compositional perspectives",
        "action": "Add movement, motion, and dynamic action descriptions",
        "setting": "Vary the environment, lighting, and atmospheric conditions",
        "mixed": "Combine different aspects: details, perspectives, actions, and settings"
    }

    instruction = variation_instructions.get(variation_type, variation_instructions["mixed"])

    system_prompt = f"""You are a creative prompt engineer for image/video generation.
Generate {num_variations} unique variations of the given prompt.

Variation type: {variation_type}
Instructions: {instruction}

Rules:
- Each variation should be distinct and creative
- Maintain the core concept of the original prompt
- Make variations suitable for image/video generation (Grok, DALL-E, etc.)
- Keep each variation concise (1-2 sentences max)
- Focus on visual, cinematic descriptions
- Return ONLY the variations, one per line, no numbering or extra text

Base prompt: {base_prompt}"""

    try:
        # Call Ollama API (local)
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2",
                    "prompt": system_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.9,  # High creativity
                        "num_predict": 1000
                    }
                }
            )

            if response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"Ollama API error: {response.text}"
                )

            result = response.json()
            variations_text = result.get("response", "").strip()

            # Parse variations from response
            variations = [v.strip() for v in variations_text.split('\n') if v.strip()]

            # Filter out any numbered lines or empty lines
            variations = [v for v in variations if v and not v[0].isdigit() or len(v) > 3]

            # Ensure we have the requested number of variations
            variations = variations[:num_variations]

            return {
                "base_prompt": base_prompt,
                "variations": variations,
                "count": len(variations),
                "type": variation_type,
                "ai_powered": True,
                "model": "llama3.2 (Ollama - Local)"
            }

    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Ollama is not running. Please start Ollama with 'ollama serve' or ensure it's running in the background."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate AI variations: {str(e)}"
        )


@app.get("/media/{file_path:path}")
async def serve_media(file_path: str):
    """Serve media files"""
    # Security: prevent directory traversal
    file_path = os.path.normpath(file_path)
    if ".." in file_path or file_path.startswith("/"):
        raise HTTPException(status_code=400, detail="Invalid file path")

    # Use configured media base directory
    full_path = os.path.join(settings.media_base_dir, file_path)
    
    # Check if file exists
    if not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    # Determine media type
    _, ext = os.path.splitext(file_path)
    ext = ext.lower()
    
    media_type_map = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".mp4": "video/mp4",
        ".webm": "video/webm",
        ".mov": "video/quicktime",
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
    }
    
    media_type = media_type_map.get(ext, "application/octet-stream")
    
    return FileResponse(full_path, media_type=media_type)


@app.post(f"{settings.api_prefix}/media/{{post_id}}/like")
async def toggle_like(post_id: str, db: AsyncSession = Depends(get_db)):
    """Toggle like status for a media post"""
    
    # Find post
    result = await db.execute(
        select(MediaPost).where(MediaPost.id == post_id)
    )
    post = result.scalar_one_or_none()
    
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Toggle like status
    post.like_status = not post.like_status
    await db.commit()
    
    # Invalidate stats cache
    if redis_client:
        await redis_client.delete("stats")
    
    return {"id": str(post.id), "like_status": post.like_status}


@app.get(f"{settings.api_prefix}/media/{{post_id}}/similar", response_model=list[MediaPostSchema])
async def get_similar_items(
    post_id: str,
    limit: int = Query(6, ge=1, le=20, description="Number of similar items to return"),
    db: AsyncSession = Depends(get_db)
):
    """Get similar items using hybrid approach: TF-IDF similarity + metadata matching"""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np

    # Find the current post
    result = await db.execute(
        select(MediaPost).options(
            selectinload(MediaPost.child_posts)
        ).where(MediaPost.id == post_id)
    )
    current_post = result.scalar_one_or_none()

    if not current_post:
        raise HTTPException(status_code=404, detail="Post not found")

    # Get all posts except the current one
    result = await db.execute(
        select(MediaPost).options(
            selectinload(MediaPost.child_posts)
        ).where(MediaPost.id != post_id)
    )
    all_posts = result.scalars().all()

    if not all_posts:
        return []

    # Extract prompts for TF-IDF
    current_prompt = current_post.original_prompt or current_post.prompt or ""
    prompts = [post.original_prompt or post.prompt or "" for post in all_posts]

    # Add current prompt to the beginning for comparison
    all_prompts = [current_prompt] + prompts

    # Calculate TF-IDF similarity
    try:
        vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2),
            min_df=1
        )
        tfidf_matrix = vectorizer.fit_transform(all_prompts)

        # Calculate cosine similarity with current post (index 0)
        similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
    except Exception as e:
        print(f"TF-IDF calculation error: {e}")
        # Fallback to simple string matching
        similarities = np.array([
            len(set(current_prompt.lower().split()) & set(p.lower().split())) /
            max(len(current_prompt.split()), len(p.split()), 1)
            for p in prompts
        ])

    # Apply metadata boosting
    boosted_scores = []
    for i, post in enumerate(all_posts):
        score = similarities[i]

        # Boost by 1.5x if same model
        if post.model_name == current_post.model_name:
            score *= 1.5

        # Boost by 1.2x if has similar child post modes
        current_modes = {child.mode for child in current_post.child_posts if child.mode}
        post_modes = {child.mode for child in post.child_posts if child.mode}
        if current_modes and post_modes and current_modes & post_modes:
            score *= 1.2

        boosted_scores.append((score, post))

    # Sort by score descending and return top N
    boosted_scores.sort(key=lambda x: x[0], reverse=True)
    similar_posts = [post for score, post in boosted_scores[:limit]]

    return similar_posts


# ===== COLLECTIONS ENDPOINTS =====

@app.post(f"{settings.api_prefix}/collections", response_model=CollectionSchema, status_code=201)
async def create_collection(
    collection: CollectionCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new collection"""
    user = await get_default_user(db)

    new_collection = Collection(
        user_id=user.id,
        name=collection.name,
        description=collection.description,
        is_smart=collection.is_smart,
        smart_filters=collection.smart_filters
    )

    db.add(new_collection)
    await db.commit()
    await db.refresh(new_collection)

    # Add item_count
    response = CollectionSchema.model_validate(new_collection)
    response.item_count = 0

    return response


@app.get(f"{settings.api_prefix}/collections", response_model=list[CollectionSchema])
async def get_collections(db: AsyncSession = Depends(get_db)):
    """Get all collections for the user"""
    user = await get_default_user(db)

    # Get collections with item counts
    result = await db.execute(
        select(Collection)
        .where(Collection.user_id == user.id)
        .order_by(Collection.updated_at.desc())
    )
    collections = result.scalars().all()

    # Add item counts
    response = []
    for collection in collections:
        collection_data = CollectionSchema.model_validate(collection)
        # Count items
        count_result = await db.execute(
            select(func.count(CollectionItem.id))
            .where(CollectionItem.collection_id == collection.id)
        )
        collection_data.item_count = count_result.scalar() or 0
        response.append(collection_data)

    return response


@app.get(f"{settings.api_prefix}/collections/{{collection_id}}", response_model=CollectionWithItemsSchema)
async def get_collection(collection_id: str, db: AsyncSession = Depends(get_db)):
    """Get a collection with all its items"""
    result = await db.execute(
        select(Collection).where(Collection.id == collection_id)
    )
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Get collection items with media posts
    items_result = await db.execute(
        select(MediaPost)
        .join(CollectionItem, CollectionItem.media_post_id == MediaPost.id)
        .where(CollectionItem.collection_id == collection_id)
        .options(selectinload(MediaPost.child_posts))
        .order_by(CollectionItem.added_at.desc())
    )
    media_posts = items_result.scalars().all()

    # Build response
    response_data = {
        **CollectionSchema.model_validate(collection).model_dump(),
        'items': media_posts,
        'item_count': len(media_posts)
    }

    return response_data


@app.put(f"{settings.api_prefix}/collections/{{collection_id}}", response_model=CollectionSchema)
async def update_collection(
    collection_id: str,
    updates: CollectionUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update a collection"""
    result = await db.execute(
        select(Collection).where(Collection.id == collection_id)
    )
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Apply updates
    update_data = updates.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(collection, field, value)

    await db.commit()
    await db.refresh(collection)

    # Add item count
    count_result = await db.execute(
        select(func.count(CollectionItem.id))
        .where(CollectionItem.collection_id == collection.id)
    )

    response = CollectionSchema.model_validate(collection)
    response.item_count = count_result.scalar() or 0

    return response


@app.delete(f"{settings.api_prefix}/collections/{{collection_id}}")
async def delete_collection(collection_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a collection"""
    result = await db.execute(
        select(Collection).where(Collection.id == collection_id)
    )
    collection = result.scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    await db.delete(collection)
    await db.commit()

    return {"message": "Collection deleted successfully"}


@app.post(f"{settings.api_prefix}/collections/{{collection_id}}/items")
async def add_item_to_collection(
    collection_id: str,
    media_post_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Add a media post to a collection"""
    # Verify collection exists
    collection_result = await db.execute(
        select(Collection).where(Collection.id == collection_id)
    )
    collection = collection_result.scalar_one_or_none()

    if not collection:
        raise HTTPException(status_code=404, detail="Collection not found")

    # Verify media post exists
    post_result = await db.execute(
        select(MediaPost).where(MediaPost.id == media_post_id)
    )
    post = post_result.scalar_one_or_none()

    if not post:
        raise HTTPException(status_code=404, detail="Media post not found")

    # Check if already in collection
    existing_result = await db.execute(
        select(CollectionItem)
        .where(
            CollectionItem.collection_id == collection_id,
            CollectionItem.media_post_id == media_post_id
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        raise HTTPException(status_code=400, detail="Item already in collection")

    # Add to collection
    collection_item = CollectionItem(
        collection_id=collection.id,
        media_post_id=post.id
    )

    db.add(collection_item)
    await db.commit()

    return {"message": "Item added to collection successfully"}


@app.delete(f"{settings.api_prefix}/collections/{{collection_id}}/items/{{post_id}}")
async def remove_item_from_collection(
    collection_id: str,
    post_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Remove a media post from a collection"""
    result = await db.execute(
        select(CollectionItem)
        .where(
            CollectionItem.collection_id == collection_id,
            CollectionItem.media_post_id == post_id
        )
    )
    item = result.scalar_one_or_none()

    if not item:
        raise HTTPException(status_code=404, detail="Item not in collection")

    await db.delete(item)
    await db.commit()

    return {"message": "Item removed from collection successfully"}


@app.get(f"{settings.api_prefix}/collections/smart/preview", response_model=list[MediaPostSchema])
async def preview_smart_collection(
    model: Optional[str] = Query(None),
    mode: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """Preview items that would match a smart collection's filters"""
    query = select(MediaPost).options(
        selectinload(MediaPost.child_posts)
    )

    # Apply filters
    if model and model != "all":
        query = query.where(MediaPost.model_name == model)

    if mode and mode != "all":
        query = query.join(MediaPost.child_posts).where(ChildPost.mode == mode).distinct()

    if search:
        search_term = f"%{search}%"
        query = query.where(
            (MediaPost.prompt.ilike(search_term)) |
            (MediaPost.original_prompt.ilike(search_term))
        )

    query = query.order_by(MediaPost.create_time.desc()).limit(limit)

    result = await db.execute(query)
    posts = result.scalars().all()

    return posts


# ===== USER PREFERENCES ENDPOINTS =====

@app.get(f"{settings.api_prefix}/users/{{user_id}}/preferences", response_model=UserPreferenceSchema)
async def get_user_preferences(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get user preferences with caching"""
    # Try cache first
    if redis_client:
        try:
            cache_key = f"preferences:{user_id}"
            cached = await redis_client.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Redis get error: {e}")

    # Query database
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )
    preferences = result.scalar_one_or_none()

    # If no preferences exist, create default ones
    if not preferences:
        # Get or create user
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Create default preferences
        preferences = UserPreference(
            user_id=user_id,
            preferences={
                "layout": {
                    "view_mode": "masonry",
                    "density": "comfortable",
                    "columns": "auto"
                },
                "filters": {
                    "last_used": {},
                    "presets": [],
                    "default_preset": None
                },
                "sorting": {
                    "default": "date_desc"
                },
                "ai_generator": {
                    "default_creativity": 0.7,
                    "favorite_styles": []
                }
            }
        )
        db.add(preferences)
        await db.commit()
        await db.refresh(preferences)

    # Cache the result
    if redis_client:
        try:
            cache_key = f"preferences:{user_id}"
            await redis_client.setex(
                cache_key,
                300,  # 5 minutes TTL
                json.dumps(UserPreferenceSchema.model_validate(preferences).model_dump(mode='json'), default=str)
            )
        except Exception as e:
            logger.error(f"Redis set error: {e}")

    return preferences


@app.put(f"{settings.api_prefix}/users/{{user_id}}/preferences", response_model=UserPreferenceSchema)
async def update_user_preferences(
    user_id: str,
    preferences_update: UserPreferenceUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update user preferences and invalidate cache"""
    # Get existing preferences
    result = await db.execute(
        select(UserPreference).where(UserPreference.user_id == user_id)
    )
    preferences = result.scalar_one_or_none()

    if not preferences:
        # Create new preferences if they don't exist
        user_result = await db.execute(select(User).where(User.id == user_id))
        user = user_result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        preferences = UserPreference(
            user_id=user_id,
            preferences=preferences_update.preferences
        )
        db.add(preferences)
    else:
        # Update existing preferences
        preferences.preferences = preferences_update.preferences

    await db.commit()
    await db.refresh(preferences)

    # Invalidate cache
    if redis_client:
        try:
            cache_key = f"preferences:{user_id}"
            await redis_client.delete(cache_key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

    return preferences


@app.post(f"{settings.api_prefix}/check-existing")
async def check_existing_posts(
    post_ids: list[str],
    db: AsyncSession = Depends(get_db)
):
    """Check which post IDs already exist in the database"""
    # Convert to UUIDs
    from uuid import UUID
    uuids = [UUID(pid) for pid in post_ids]

    # Query existing posts
    result = await db.execute(
        select(MediaPost.id).where(MediaPost.id.in_(uuids))
    )
    existing_ids = [str(row[0]) for row in result.all()]

    return {"existing_ids": existing_ids}


def url_to_local_path(url: str, base_dir: str = None) -> str:
    """
    Convert a Grok URL to local https_/ format for database storage.

    Example:
    https://assets.grok.com/users/.../video.mp4
    -> https_/assets.grok.com/users/.../video.mp4 (if file exists locally)
    -> https://assets.grok.com/users/.../video.mp4 (if file doesn't exist)
    """
    import os
    from urllib.parse import urlparse

    if base_dir is None:
        base_dir = settings.media_base_dir

    if not url.startswith('http'):
        return url  # Already a local path

    # Parse the URL
    parsed = urlparse(url)

    # Construct relative database path: https_/domain/path
    db_path = os.path.join(
        f"https_",
        parsed.netloc,
        parsed.path.lstrip('/')
    )

    # Construct full file system path to check if file exists
    full_path = os.path.join(base_dir, db_path)

    # Check if file exists locally
    if os.path.exists(full_path):
        return db_path  # Return https_/ format for database

    # If not found, return original URL
    return url


@app.post(f"{settings.api_prefix}/import/validate")
async def validate_import(
    import_request: ImportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Validate import data and return list of missing files.
    Checks which posts already exist and which media files are missing.
    Prevents duplicate URLs in the missing files list.
    """
    existing_posts = []
    missing_files = set()  # Use set to prevent duplicates
    valid_files = set()    # Use set to prevent duplicates

    base_dir = settings.media_base_dir

    for post_data in import_request.posts:
        # Check if post already exists
        try:
            result = await db.execute(
                select(MediaPost).where(MediaPost.id == post_data.id)
            )
            existing_post = result.scalar_one_or_none()

            if existing_post:
                existing_posts.append(str(post_data.id))
                continue
        except Exception as e:
            print(f"Database error checking post {post_data.id}: {e}")
            continue

        # Check if parent media file exists
        if post_data.mediaUrl.startswith('http'):
            try:
                parsed = urlparse(post_data.mediaUrl)
                local_path = os.path.join(base_dir, "https_", parsed.netloc, parsed.path.lstrip('/'))

                if os.path.exists(local_path):
                    valid_files.add(post_data.mediaUrl)
                else:
                    missing_files.add(post_data.mediaUrl)
            except Exception as e:
                print(f"Error checking parent file {post_data.mediaUrl}: {e}")
                missing_files.add(post_data.mediaUrl)

        # Check child post media files
        for child_data in post_data.childPosts:
            if child_data.mediaUrl.startswith('http'):
                try:
                    parsed = urlparse(child_data.mediaUrl)
                    local_path = os.path.join(base_dir, "https_", parsed.netloc, parsed.path.lstrip('/'))

                    if os.path.exists(local_path):
                        valid_files.add(child_data.mediaUrl)
                    else:
                        missing_files.add(child_data.mediaUrl)
                except Exception as e:
                    print(f"Error checking child file {child_data.mediaUrl}: {e}")
                    missing_files.add(child_data.mediaUrl)

    return {
        "existing_posts": len(existing_posts),
        "new_posts": len(import_request.posts) - len(existing_posts),
        "valid_files": len(valid_files),
        "missing_files": sorted(list(missing_files)),  # Convert set to sorted list
        "can_import": len(missing_files) == 0
    }


@app.post(f"{settings.api_prefix}/import", response_model=ImportResponse)
async def import_posts(
    import_request: ImportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Import media posts and child posts from JSON.
    Skips posts that already exist (by ID).
    Automatically converts URLs to local file paths if files exist.
    """
    from dateutil.parser import isoparse
    from datetime import timezone

    posts_imported = 0
    child_posts_imported = 0
    posts_skipped = 0

    for post_data in import_request.posts:
        # Check if post already exists
        result = await db.execute(
            select(MediaPost).where(MediaPost.id == post_data.id)
        )
        existing_post = result.scalar_one_or_none()

        if existing_post:
            posts_skipped += 1
            continue

        # Parse create time and ensure timezone-naive UTC
        create_time = make_naive_utc(isoparse(post_data.createTime))

        # Ensure user exists - create if not found
        user_result = await db.execute(
            select(User).where(User.id == post_data.userId)
        )
        existing_user = user_result.scalar_one_or_none()

        if not existing_user:
            # Create new user with default values
            new_user = User(
                id=post_data.userId,
                username=f"user_{str(post_data.userId)[:8]}",
                email=f"{str(post_data.userId)[:8]}@imported.local"
            )
            db.add(new_user)
            await db.flush()  # Ensure user is created before adding posts

        # Get like status
        like_status = False
        if post_data.userInteractionStatus:
            like_status = post_data.userInteractionStatus.get('likeStatus', False)

        # Convert media URL to local path if file exists
        media_url = url_to_local_path(post_data.mediaUrl)

        # Create media post
        new_post = MediaPost(
            id=post_data.id,
            user_id=post_data.userId,
            create_time=create_time,
            prompt=post_data.prompt or "",
            original_prompt=post_data.originalPrompt or "",
            media_type=post_data.mediaType,
            media_url=media_url,
            mime_type=post_data.mimeType,
            model_name=post_data.modelName,
            like_status=like_status
        )
        db.add(new_post)
        posts_imported += 1

        # Create child posts
        for child_data in post_data.childPosts:
            # Check if child already exists
            child_result = await db.execute(
                select(ChildPost).where(ChildPost.id == child_data.id)
            )
            existing_child = child_result.scalar_one_or_none()

            if existing_child:
                continue

            # Parse child create time and ensure timezone-naive UTC
            child_create_time = make_naive_utc(isoparse(child_data.createTime))

            # Convert child media URL to local path if file exists
            child_media_url = url_to_local_path(child_data.mediaUrl)

            new_child = ChildPost(
                id=child_data.id,
                parent_post_id=post_data.id,
                user_id=child_data.userId,
                create_time=child_create_time,
                prompt=child_data.prompt or "",
                original_prompt=child_data.originalPrompt or "",
                media_type=child_data.mediaType,
                media_url=child_media_url,
                mime_type=child_data.mimeType,
                model_name=child_data.modelName,
                mode=child_data.mode or "normal"
            )
            db.add(new_child)
            child_posts_imported += 1

    # Commit all changes
    await db.commit()

    # Clear caches
    if redis_client:
        try:
            await redis_client.delete("stats")
            await redis_client.delete("models:all")
        except Exception as e:
            logger.error(f"Redis cache clear error: {e}")

    return ImportResponse(
        posts_imported=posts_imported,
        child_posts_imported=child_posts_imported,
        posts_skipped=posts_skipped,
        total_processed=len(import_request.posts)
    )


@app.post(f"{settings.api_prefix}/media/{{post_id}}/generate-video")
async def generate_video_from_image(
    post_id: str,
    db: AsyncSession = Depends(get_db),
    model: str = Query("wan", description="Model to use: 'wan' or 'svd'"),
    num_frames: int = Query(49, description="Number of frames to generate"),
    fps: int = Query(16, ge=1, le=30, description="Frames per second"),
    prompt: str = Query("", description="Optional text prompt to guide generation (Wan only)"),
    guidance_scale: float = Query(5.0, ge=1.0, le=10.0, description="How closely to follow prompt (1-10)")
):
    """Generate a video from an image using AI models

    Args:
        post_id: UUID of the media post (must be an image)
        model: Which model to use ('wan' for Wan 2.1, 'svd' for Stable Video Diffusion)
        num_frames: Number of frames (Wan: 49/81/113, SVD: 14/25)
        fps: Frames per second for output video
        prompt: Optional text prompt to guide generation (Wan 2.1 only)
        guidance_scale: How closely to follow prompt (1.0-10.0)

    Returns:
        The generated child post with video
    """
    from uuid import UUID, uuid4

    # Get the media post
    result = await db.execute(
        select(MediaPost).where(MediaPost.id == UUID(post_id))
    )
    media_post = result.scalar_one_or_none()

    if not media_post:
        raise HTTPException(status_code=404, detail="Media post not found")

    # Check if post is an image (handle both "image" and "MEDIA_POST_TYPE_IMAGE" formats)
    if not (media_post.media_type == "image" or "IMAGE" in media_post.media_type.upper()):
        raise HTTPException(status_code=400, detail="Post must be an image to generate video")

    # Get input image path
    # Handle both absolute paths and relative URLs (e.g., "https_/assets.grok.com/...")
    if media_post.media_url.startswith('/'):
        # Absolute path - use as-is
        input_path = media_post.media_url
    else:
        # Relative path - join with base directory
        # Remove 'media/' prefix if present
        relative_path = media_post.media_url
        if relative_path.startswith('media/'):
            relative_path = relative_path.replace('media/', '', 1)
        input_path = os.path.join(settings.media_base_dir, relative_path)

    input_path = os.path.normpath(input_path)

    # Security check
    if ".." in input_path:
        raise HTTPException(status_code=400, detail="Invalid media path")

    if not os.path.exists(input_path):
        raise HTTPException(status_code=404, detail=f"Image file not found: {input_path}")

    # Generate output path
    generated_videos_dir = os.path.join(settings.media_base_dir, "generated_videos")
    os.makedirs(generated_videos_dir, exist_ok=True)

    video_filename = f"{uuid4()}.mp4"
    output_path = os.path.join(generated_videos_dir, video_filename)

    try:
        # Route to appropriate service based on model parameter
        model_name = ""

        if model.lower() == "svd":
            # Use Stable Video Diffusion
            from app.services.svd_service import get_svd_service
            svd_service = get_svd_service()
            logger.info(f"Generating video from image using SVD: {post_id}")

            await svd_service.generate_video(
                image_path=input_path,
                output_path=output_path,
                num_frames=num_frames if num_frames in [14, 25] else 14,
                fps=fps,
                motion_bucket_id=127,  # Motion intensity
                noise_aug_strength=0.02
            )
            model_name = "SVD-img2vid"
            prompt_desc = f"SVD image-to-video ({num_frames} frames)"

        else:  # Default to Wan 2.1
            # Use Wan 2.1
            from app.services.wan_service import get_wan_service
            wan_service = get_wan_service()
            logger.info(f"Generating video from image using Wan 2.1: {post_id}")

            await wan_service.generate_video(
                image_path=input_path,
                output_path=output_path,
                num_frames=num_frames if num_frames in [49, 81, 113] else 49,
                fps=fps,
                prompt=prompt,
                negative_prompt="worst quality, inconsistent motion, blurry, jittery, distorted",
                guidance_scale=guidance_scale,
                height=480,  # 480p for optimal memory usage
                width=832    # 16:9 aspect ratio
            )
            model_name = "Wan2.1-I2V-14B-480P"
            prompt_desc = f"Image-to-video: {prompt}" if prompt else f"Image-to-video ({num_frames} frames)"

        # Get user
        user = await get_default_user(db)

        # Create child post for the generated video
        # Convert absolute path to relative URL format for database
        relative_path = os.path.relpath(output_path, settings.media_base_dir)

        child_post = ChildPost(
            id=uuid4(),
            parent_post_id=media_post.id,
            user_id=user.id,
            create_time=datetime.now(timezone.utc).replace(tzinfo=None),
            prompt=prompt_desc,
            original_prompt=media_post.original_prompt or media_post.prompt or "",
            media_type="video",
            media_url=relative_path,
            mime_type="video/mp4",
            model_name=model_name,
            mode="generated"
        )

        db.add(child_post)
        await db.commit()
        await db.refresh(child_post)

        logger.info(f"Video generated successfully: {child_post.id}")

        return {
            "id": str(child_post.id),
            "parent_post_id": str(child_post.parent_post_id),
            "media_url": child_post.media_url,
            "media_type": child_post.media_type,
            "model_name": child_post.model_name,
            "prompt": child_post.prompt,
            "create_time": child_post.create_time.isoformat()
        }

    except Exception as e:
        logger.error(f"Video generation failed: {e}")
        # Clean up failed output if it exists
        if os.path.exists(output_path):
            os.remove(output_path)
        raise HTTPException(status_code=500, detail=f"Video generation failed: {str(e)}")


@app.get(f"{settings.api_prefix}/media/{{post_id}}/generated-videos")
async def get_generated_videos(
    post_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all generated videos for an image post"""
    from uuid import UUID

    # Get child posts for this parent
    result = await db.execute(
        select(ChildPost)
        .where(ChildPost.parent_post_id == UUID(post_id))
        .where(ChildPost.mode == "generated")
        .order_by(ChildPost.create_time.desc())
    )
    child_posts = result.scalars().all()

    return [
        {
            "id": str(cp.id),
            "media_url": cp.media_url,
            "media_type": cp.media_type,
            "model_name": cp.model_name,
            "prompt": cp.prompt,
            "create_time": cp.create_time.isoformat()
        }
        for cp in child_posts
    ]


@app.get(f"{settings.api_prefix}/media/{{post_id}}/collections")
async def get_media_collections(
    post_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get all collections that contain this media post"""
    from uuid import UUID

    # Get collection items for this post
    result = await db.execute(
        select(CollectionItem)
        .where(CollectionItem.media_post_id == UUID(post_id))
        .options(selectinload(CollectionItem.collection))
    )
    collection_items = result.scalars().all()

    # Return collection info
    return [
        {
            "id": str(item.collection.id),
            "name": item.collection.name,
            "added_at": item.added_at.isoformat() if item.added_at else None
        }
        for item in collection_items
        if item.collection is not None
    ]


@app.post(f"{settings.api_prefix}/videos/merge")
async def merge_videos(
    video_ids: list[str] = Body(..., description="List of child post IDs to merge"),
    use_transitions: bool = Body(True, description="Use AI transitions (RIFE) between videos"),
    transition_frames: int = Body(10, ge=0, le=30, description="Number of interpolated frames per transition"),
    fps: int = Body(30, ge=15, le=60, description="Output video FPS"),
    db: AsyncSession = Depends(get_db)
):
    """
    Merge multiple videos with optional AI smooth transitions

    Args:
        video_ids: List of child post UUIDs to merge (in order)
        use_transitions: Enable AI transitions using RIFE
        transition_frames: Number of interpolated frames between videos
        fps: Output frames per second

    Returns:
        New child post with merged video
    """
    from uuid import UUID, uuid4

    if len(video_ids) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 videos to merge")

    logger.info(f"Merging {len(video_ids)} videos (transitions={'enabled' if use_transitions else 'disabled'})")

    # Get all child posts
    video_posts = []
    for video_id in video_ids:
        result = await db.execute(
            select(ChildPost).where(ChildPost.id == UUID(video_id))
        )
        post = result.scalar_one_or_none()
        if not post:
            raise HTTPException(status_code=404, detail=f"Video {video_id} not found")
        if post.media_type not in ["video", "MEDIA_POST_TYPE_VIDEO"]:
            raise HTTPException(status_code=400, detail=f"Post {video_id} is not a video")
        video_posts.append(post)

    # Get video file paths
    video_paths = []
    for post in video_posts:
        # Handle both absolute and relative paths
        if post.media_url.startswith('/'):
            # Absolute path - use as-is
            path = post.media_url
        else:
            # Relative path - join with base directory
            # Remove 'media/' prefix if present
            relative_path = post.media_url
            if relative_path.startswith('media/'):
                relative_path = relative_path.replace('media/', '', 1)
            path = os.path.join(settings.media_base_dir, relative_path)

        path = os.path.normpath(path)

        if not os.path.exists(path):
            raise HTTPException(status_code=404, detail=f"Video file not found: {path}")

        video_paths.append(path)

    # Generate output path
    merged_videos_dir = os.path.join(settings.media_base_dir, "merged_videos")
    os.makedirs(merged_videos_dir, exist_ok=True)

    output_filename = f"{uuid4()}.mp4"
    output_path = os.path.join(merged_videos_dir, output_filename)

    try:
        # Get RIFE service
        rife_service = get_rife_service()

        if use_transitions:
            logger.info("Using RIFE for smooth transitions")
            await rife_service.merge_videos_with_transitions(
                video_paths=video_paths,
                output_path=output_path,
                transition_frames=transition_frames,
                fps=fps
            )
        else:
            logger.info("Using simple concatenation (no transitions)")
            await rife_service.simple_concatenate(
                video_paths=video_paths,
                output_path=output_path
            )

        # Get user
        user = await get_default_user(db)

        # Create child post for merged video
        # Convert absolute path to relative URL format for database
        relative_path = os.path.relpath(output_path, settings.media_base_dir)

        # Use first video's parent as parent for the merged video
        parent_id = video_posts[0].parent_post_id

        merged_post = ChildPost(
            id=uuid4(),
            parent_post_id=parent_id,
            user_id=user.id,
            create_time=datetime.now(timezone.utc).replace(tzinfo=None),
            prompt=f"Merged {len(video_ids)} videos" + (" with AI transitions" if use_transitions else ""),
            original_prompt=", ".join([p.prompt or "" for p in video_posts[:3]]) + ("..." if len(video_posts) > 3 else ""),
            media_type="video",
            media_url=relative_path,
            mime_type="video/mp4",
            model_name="rife-merge" if use_transitions else "ffmpeg-concat",
            mode="merged"
        )

        db.add(merged_post)
        await db.commit()
        await db.refresh(merged_post)

        logger.info(f"Videos merged successfully: {merged_post.id}")

        return {
            "id": str(merged_post.id),
            "parent_post_id": str(merged_post.parent_post_id),
            "media_url": merged_post.media_url,
            "media_type": merged_post.media_type,
            "model_name": merged_post.model_name,
            "prompt": merged_post.prompt,
            "create_time": merged_post.create_time.isoformat(),
            "num_videos_merged": len(video_ids),
            "used_transitions": use_transitions
        }

    except Exception as e:
        logger.error(f"Video merging failed: {e}")
        # Clean up failed output
        if os.path.exists(output_path):
            os.remove(output_path)
        raise HTTPException(status_code=500, detail=f"Video merging failed: {str(e)}")


@app.post("/api/analyze-videos")
async def analyze_videos(
    db: AsyncSession = Depends(get_db)
):
    """
    Analyze all videos in the database and extract first/last frame hashes.
    This is a one-time operation to populate the frame_hash fields.
    """
    try:
        # Get all videos (both media posts and child posts)
        media_result = await db.execute(
            select(MediaPost).where(MediaPost.media_type == "video")
        )
        media_videos = media_result.scalars().all()

        child_result = await db.execute(
            select(ChildPost).where(ChildPost.media_type == "video")
        )
        child_videos = child_result.scalars().all()

        total_videos = len(media_videos) + len(child_videos)
        processed = 0
        updated = 0
        errors = []

        # Process media posts
        for video in media_videos:
            try:
                # Skip if already processed
                if video.first_frame_hash and video.last_frame_hash:
                    processed += 1
                    continue

                # Convert URL to local path
                video_path = url_to_local_path(video.media_url)
                full_path = os.path.join(settings.media_base_dir, video_path)

                # Extract frame hashes
                first_hash, last_hash = extract_first_and_last_frame_hashes(full_path)

                if first_hash and last_hash:
                    video.first_frame_hash = first_hash
                    video.last_frame_hash = last_hash
                    updated += 1
                else:
                    errors.append(f"Failed to extract frames from {video.id}")

                processed += 1

                # Commit every 10 videos to avoid long transactions
                if processed % 10 == 0:
                    await db.commit()
                    logger.info(f"Processed {processed}/{total_videos} videos")

            except Exception as e:
                logger.error(f"Error processing video {video.id}: {str(e)}")
                errors.append(f"Error processing {video.id}: {str(e)}")

        # Process child posts
        for video in child_videos:
            try:
                # Skip if already processed
                if video.first_frame_hash and video.last_frame_hash:
                    processed += 1
                    continue

                # Convert URL to local path
                video_path = url_to_local_path(video.media_url)
                full_path = os.path.join(settings.media_base_dir, video_path)

                # Extract frame hashes
                first_hash, last_hash = extract_first_and_last_frame_hashes(full_path)

                if first_hash and last_hash:
                    video.first_frame_hash = first_hash
                    video.last_frame_hash = last_hash
                    updated += 1
                else:
                    errors.append(f"Failed to extract frames from {video.id}")

                processed += 1

                # Commit every 10 videos
                if processed % 10 == 0:
                    await db.commit()
                    logger.info(f"Processed {processed}/{total_videos} videos")

            except Exception as e:
                logger.error(f"Error processing video {video.id}: {str(e)}")
                errors.append(f"Error processing {video.id}: {str(e)}")

        # Final commit
        await db.commit()

        return {
            "total_videos": total_videos,
            "processed": processed,
            "updated": updated,
            "errors": errors[:10] if errors else []  # Return first 10 errors
        }

    except Exception as e:
        logger.error(f"Video analysis failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Video analysis failed: {str(e)}")


@app.get("/api/video-chains")
async def get_video_chains(
    threshold: int = Query(10, description="Hamming distance threshold for frame matching"),
    min_chain_length: int = Query(2, description="Minimum chain length to return"),
    db: AsyncSession = Depends(get_db)
):
    """
    Find chains of videos where the last frame of one video matches the first frame of another.
    Returns a list of video chains ordered by length (longest first).
    """
    try:
        # Get all videos with frame hashes
        media_result = await db.execute(
            select(MediaPost).where(
                MediaPost.media_type == "video",
                MediaPost.first_frame_hash.isnot(None),
                MediaPost.last_frame_hash.isnot(None)
            )
        )
        media_videos = media_result.scalars().all()

        child_result = await db.execute(
            select(ChildPost).where(
                ChildPost.media_type == "video",
                ChildPost.first_frame_hash.isnot(None),
                ChildPost.last_frame_hash.isnot(None)
            )
        )
        child_videos = child_result.scalars().all()

        # Create unified video list with type information
        all_videos = []
        for video in media_videos:
            all_videos.append({
                "id": str(video.id),
                "type": "media",
                "first_hash": video.first_frame_hash,
                "last_hash": video.last_frame_hash,
                "media_url": video.media_url,
                "prompt": video.prompt or video.original_prompt,
                "create_time": video.create_time.isoformat() if video.create_time else None
            })

        for video in child_videos:
            all_videos.append({
                "id": str(video.id),
                "type": "child",
                "first_hash": video.first_frame_hash,
                "last_hash": video.last_frame_hash,
                "media_url": video.media_url,
                "prompt": video.prompt or video.original_prompt,
                "create_time": video.create_time.isoformat() if video.create_time else None
            })

        # Build adjacency list for video chains
        # Key: video id, Value: list of videos that can follow it
        graph = {v["id"]: [] for v in all_videos}

        for v1 in all_videos:
            for v2 in all_videos:
                if v1["id"] != v2["id"]:
                    # Check if v1's last frame matches v2's first frame
                    if frames_match(v1["last_hash"], v2["first_hash"], threshold):
                        graph[v1["id"]].append(v2["id"])

        # Find all chains using DFS
        visited = set()
        chains = []

        def dfs(video_id, current_chain):
            """Depth-first search to find all possible chains"""
            visited.add(video_id)
            current_chain.append(video_id)

            # Check if we can extend this chain
            has_extension = False
            for next_id in graph[video_id]:
                if next_id not in visited:
                    has_extension = True
                    dfs(next_id, current_chain.copy())

            # If no extension or reached end, save chain if long enough
            if not has_extension and len(current_chain) >= min_chain_length:
                chains.append(current_chain.copy())

            visited.remove(video_id)

        # Start DFS from each video
        for video in all_videos:
            dfs(video["id"], [])

        # Create video lookup
        video_lookup = {v["id"]: v for v in all_videos}

        # Format chains with video details
        formatted_chains = []
        for chain in chains:
            chain_data = {
                "length": len(chain),
                "videos": [video_lookup[vid] for vid in chain],
                "total_duration_estimate": len(chain) * 6  # Estimate 6 seconds per video
            }
            formatted_chains.append(chain_data)

        # Sort by length (longest first)
        formatted_chains.sort(key=lambda x: x["length"], reverse=True)

        return {
            "total_videos": len(all_videos),
            "total_chains": len(formatted_chains),
            "chains": formatted_chains
        }

    except Exception as e:
        logger.error(f"Failed to find video chains: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to find video chains: {str(e)}")


@app.post("/api/merge-chain")
async def merge_video_chain(
    chain_video_ids: list[str] = Body(..., description="Ordered list of video IDs to merge"),
    use_transitions: bool = Body(False, description="Use RIFE frame interpolation for smooth transitions"),
    output_filename: str = Body(None, description="Optional output filename"),
    db: AsyncSession = Depends(get_db)
):
    """
    Merge a chain of videos into a single video file.
    The videos will be concatenated in the order provided.
    """
    try:
        if len(chain_video_ids) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 videos to merge")

        # Get all videos
        video_paths = []
        prompts = []

        for video_id in chain_video_ids:
            # Try to find in media posts
            media_result = await db.execute(
                select(MediaPost).where(MediaPost.id == video_id)
            )
            media_video = media_result.scalar_one_or_none()

            if media_video:
                video_path = url_to_local_path(media_video.media_url)
                full_path = os.path.join(settings.media_base_dir, video_path)
                video_paths.append(full_path)
                prompts.append(media_video.prompt or media_video.original_prompt or "")
                continue

            # Try to find in child posts
            child_result = await db.execute(
                select(ChildPost).where(ChildPost.id == video_id)
            )
            child_video = child_result.scalar_one_or_none()

            if child_video:
                video_path = url_to_local_path(child_video.media_url)
                full_path = os.path.join(settings.media_base_dir, video_path)
                video_paths.append(full_path)
                prompts.append(child_video.prompt or child_video.original_prompt or "")
            else:
                raise HTTPException(status_code=404, detail=f"Video {video_id} not found")

        # Verify all files exist
        for path in video_paths:
            if not os.path.exists(path):
                raise HTTPException(status_code=404, detail=f"Video file not found: {path}")

        # Generate output filename
        if not output_filename:
            output_filename = f"chain_{'_'.join(chain_video_ids[:3])}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"

        output_dir = os.path.join(settings.media_base_dir, "merged_chains")
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, output_filename)

        # Use RIFE service if transitions requested, otherwise simple concatenation
        if use_transitions:
            rife_service = get_rife_service()
            await rife_service.merge_videos_with_transitions(video_paths, output_path)
        else:
            # Simple concatenation using ffmpeg
            # Create concat file
            concat_file = os.path.join(output_dir, f"concat_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
            with open(concat_file, 'w') as f:
                for path in video_paths:
                    f.write(f"file '{path}'\n")

            # Run ffmpeg concat
            cmd = [
                'ffmpeg',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_file,
                '-c', 'copy',
                '-y',
                output_path
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=300)

            # Clean up concat file
            os.remove(concat_file)

            if result.returncode != 0:
                raise Exception(f"ffmpeg failed: {result.stderr.decode()}")

        # Create merged video post in database
        user_result = await db.execute(select(User).limit(1))
        user = user_result.scalar_one()

        # Generate combined prompt
        combined_prompt = " → ".join([p[:50] for p in prompts if p])

        merged_post = MediaPost(
            id=uuid.uuid4(),
            user_id=user.id,
            create_time=datetime.now(timezone.utc).replace(tzinfo=None),
            prompt=combined_prompt,
            original_prompt=combined_prompt,
            media_type="video",
            media_url=f"merged_chains/{output_filename}",
            mime_type="video/mp4",
            model_name="merged_chain",
            extra_metadata={
                "chain_video_ids": chain_video_ids,
                "chain_length": len(chain_video_ids),
                "used_transitions": use_transitions
            }
        )

        db.add(merged_post)
        await db.commit()
        await db.refresh(merged_post)

        # Clear cache
        await clear_cache("stats")

        return {
            "id": str(merged_post.id),
            "media_url": merged_post.media_url,
            "prompt": merged_post.prompt,
            "chain_length": len(chain_video_ids),
            "used_transitions": use_transitions
        }

    except Exception as e:
        logger.error(f"Chain merging failed: {str(e)}")
        if os.path.exists(output_path):
            os.remove(output_path)
        raise HTTPException(status_code=500, detail=f"Chain merging failed: {str(e)}")


# Mount static files (HTML pages) - must be last
# Serve static files from parent directory
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=5000,
        reload=settings.debug
    )
