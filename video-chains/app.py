"""
Smart Video Chain Finder - AI-powered chain discovery
Supports both basic frame matching and advanced semantic understanding
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import os
from video_analyzer import VideoAnalyzer
from utils.error_handler import handle_api_error
import subprocess
from typing import List, Optional
import sys

# Try to import smart analyzer
SMART_MODE = False
try:
    from video_analyzer_smart import SmartVideoAnalyzer
    SMART_MODE = True
except ImportError as e:
    print(f"⚠️  Smart features not available: {e}")
    print("💡 Install dependencies: pip install -r requirements.txt")

app = FastAPI(
    title="Smart Video Chain Finder" if SMART_MODE else "Video Chain Finder",
    description="AI-powered video chain discovery with semantic understanding" if SMART_MODE else "Frame-based video chain discovery",
    version="2.0.0" if SMART_MODE else "1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize analyzer
VIDEO_DIR = "/Users/alialqattan/Downloads/8xSovia/https_"
CACHE_FILE = "video_data.json"
SMART_CACHE_FILE = "video_data_smart.json"
OUTPUT_DIR = "/Users/alialqattan/Downloads/8xSovia/video-chains/merged"

# Use smart analyzer if available
if SMART_MODE:
    try:
        analyzer = SmartVideoAnalyzer(VIDEO_DIR, SMART_CACHE_FILE, use_smart_features=True)
        print("🧠 Running in SMART mode with AI features")
    except Exception as e:
        print(f"⚠️  Failed to initialize smart analyzer: {e}")
        analyzer = VideoAnalyzer(VIDEO_DIR, CACHE_FILE)
        SMART_MODE = False
        print("📊 Falling back to BASIC mode")
else:
    analyzer = VideoAnalyzer(VIDEO_DIR, CACHE_FILE)
    print("📊 Running in BASIC mode")

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Load cached data on startup
if os.path.exists(CACHE_FILE):
    analyzer.analyze_all(force_refresh=False)


@app.get("/")
async def root():
    """Serve the main HTML page"""
    return FileResponse("index.html")


@app.get("/api/info")
async def api_info():
    """Get API status and video count"""
    return {
        "message": "Smart Video Chain Finder API" if SMART_MODE else "Video Chain Finder API",
        "version": "2.0.0" if SMART_MODE else "1.0.0",
        "smart_mode": SMART_MODE,
        "videos": len(analyzer.videos),
        "features": {
            "frame_matching": True,
            "semantic_matching": SMART_MODE,
            "scene_detection": SMART_MODE,
            "multi_modal_scoring": SMART_MODE
        }
    }


@app.get("/api/progress")
async def get_progress():
    """Get current scan progress"""
    return analyzer.scan_progress


@app.post("/api/scan")
async def scan_videos(force_refresh: bool = False, smart: bool = True, sample_size: Optional[int] = None):
    """
    Scan and analyze all videos

    Args:
        force_refresh: Re-analyze even if cache exists
        smart: Use smart analysis if available (CLIP, scenes, etc.)
        sample_size: Only analyze first N videos (for testing)
    """
    import threading

    def scan_task():
        try:
            if SMART_MODE and smart:
                analyzer.analyze_all_smart(force_refresh=force_refresh, sample_size=sample_size)
            else:
                analyzer.analyze_all(force_refresh=force_refresh)
        except Exception as e:
            analyzer.scan_progress["status"] = "error"
            analyzer.scan_progress["message"] = str(e)

    # Run in background thread
    thread = threading.Thread(target=scan_task)
    thread.daemon = True
    thread.start()

    return {
        "message": "Smart scan started" if (SMART_MODE and smart) else "Scan started",
        "status": "running",
        "smart_mode": SMART_MODE and smart,
        "sample_size": sample_size
    }


# Cache for chains
chains_cache = {}

@app.get("/api/chains")
async def get_chains(min_length: int = 2, threshold: int = 15):
    """
    Find video chains using basic frame matching

    Args:
        min_length: Minimum number of videos in chain
        threshold: Hamming distance threshold for frame matching
    """
    try:
        if not analyzer.videos:
            raise HTTPException(status_code=400,
                               detail="No videos analyzed. Run /api/scan first")

        # Check cache
        cache_key = f"chains_basic_{min_length}_{threshold}"
        if cache_key in chains_cache:
            print(f"Returning cached chains for min_length={min_length}, threshold={threshold}")
            return chains_cache[cache_key]

        print(f"Finding chains with min_length={min_length}, threshold={threshold}...")

        # Run in thread pool to avoid blocking
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(analyzer.find_chains, threshold, min_length)
            chains = future.result(timeout=30)  # 30 second timeout

        # Implement diversity sampling - group ALL chains by first video
        from collections import defaultdict
        chains_by_first_frame = defaultdict(list)

        # Sample across ALL chains to find different starting frames
        # Use step sampling to spread across the entire list
        sample_step = max(1, len(chains) // 5000)  # Sample ~5000 chains evenly distributed
        for i in range(0, len(chains), sample_step):
            chain = chains[i]
            first_video = chain[0]
            first_hash = analyzer.videos[first_video]['first_hash']
            chains_by_first_frame[first_hash].append(chain)

        # Take the longest chain from each unique starting frame
        diverse_chains = []
        for first_hash, chain_group in chains_by_first_frame.items():
            # Sort by length and take the longest
            best_chain = max(chain_group, key=len)
            diverse_chains.append(best_chain)

        # Sort diverse chains by length and take top 100
        diverse_chains.sort(key=len, reverse=True)

        print(f"✨ Found {len(diverse_chains)} unique starting frames from {len(chains)} total chains (sampled every {sample_step} chains)")

        # Get detailed info for each diverse chain
        chain_data = []
        for chain in diverse_chains[:100]:  # Return top 100 diverse chains
            info = analyzer.get_chain_info(chain)

            # Calculate quality score based on frame similarity
            scores = []
            for i in range(len(chain) - 1):
                last_hash = analyzer.videos[chain[i]]['last_hash']
                first_hash = analyzer.videos[chain[i+1]]['first_hash']
                distance = analyzer.hash_distance(last_hash, first_hash)
                # Convert distance to similarity score (0-1, lower distance = higher quality)
                quality = max(0, 1 - (distance / 64.0))  # 64 is max hash distance for 16-bit hash
                scores.append(quality)
                info['videos'][i+1]['score'] = quality

            # Average quality for the whole chain
            info['avg_quality'] = sum(scores) / len(scores) if scores else 0.0

            chain_data.append(info)

        result = {
            "mode": "basic",
            "total_videos": len(analyzer.videos),
            "total_chains": len(chains),
            "chains": chain_data
        }

        # Cache result
        chains_cache[cache_key] = result

        return result
    except Exception as e:
        handle_api_error(e, timeout_message="Chain finding timed out.")


@app.get("/api/chains/smart")
async def get_smart_chains(min_score: float = 0.6, min_length: int = 2):
    """
    Find video chains using AI-powered multi-modal matching (SMART MODE ONLY)

    Args:
        min_score: Minimum chain quality score (0-1)
        min_length: Minimum number of videos in chain

    Returns:
        Chains ranked by quality with semantic similarity scores
    """
    if not SMART_MODE:
        raise HTTPException(
            status_code=501,
            detail="Smart features not available. Install dependencies: pip install -r requirements.txt"
        )

    try:
        if not analyzer.videos:
            raise HTTPException(status_code=400,
                               detail="No videos analyzed. Run /api/scan first")

        # Check cache
        cache_key = f"chains_smart_{min_score}_{min_length}"
        if cache_key in chains_cache:
            print(f"Returning cached smart chains for min_score={min_score}, min_length={min_length}")
            return chains_cache[cache_key]

        print(f"Finding SMART chains with min_score={min_score}, min_length={min_length}...")

        # Run in thread pool to avoid blocking
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(analyzer.find_smart_chains, min_score, min_length)
            chains = future.result(timeout=60)  # 60 second timeout for smart analysis

        # Format chain data
        chain_data = []
        for chain_info in chains[:20]:  # Top 20 chains
            videos = chain_info['videos']
            scores = chain_info['scores']

            # Get detailed video info
            video_details = []
            for i, video_path in enumerate(videos):
                video_data = analyzer.videos[video_path]
                detail = {
                    "path": video_path,
                    "filename": video_data['filename'],
                    "duration": video_data['duration'],
                }

                # Add transition score to next video
                if i < len(scores):
                    detail['transition_score'] = {
                        'frame_similarity': scores[i]['frame_similarity'],
                        'semantic_similarity': scores[i]['semantic_similarity'],
                        'color_continuity': scores[i]['color_continuity'],
                        'motion_continuity': scores[i]['motion_continuity'],
                        'final_score': scores[i]['final_score']
                    }

                video_details.append(detail)

            chain_data.append({
                "length": chain_info['length'],
                "avg_quality": chain_info['avg_quality'],
                "total_duration": sum(v['duration'] for v in video_details),
                "videos": video_details
            })

        result = {
            "mode": "smart",
            "total_videos": len(analyzer.videos),
            "total_chains": len(chains),
            "chains": chain_data
        }

        # Cache result
        chains_cache[cache_key] = result

        return result
    except Exception as e:
        handle_api_error(e, timeout_message="Smart chain finding timed out.")


@app.get("/api/video/{path:path}")
async def serve_video(path: str):
    """Serve video file"""
    full_path = os.path.join(VIDEO_DIR, path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Video not found")

    return FileResponse(full_path, media_type="video/mp4")


class MergeRequest(BaseModel):
    video_paths: List[str]
    output_name: Optional[str] = None


@app.post("/api/merge")
async def merge_videos(request: MergeRequest):
    """Merge videos into a single file"""
    try:
        if len(request.video_paths) < 2:
            raise HTTPException(status_code=400, detail="Need at least 2 videos")

        # Create output directory
        os.makedirs(OUTPUT_DIR, exist_ok=True)

        # Generate output filename
        if request.output_name:
            output_filename = request.output_name if request.output_name.endswith('.mp4') else f"{request.output_name}.mp4"
        else:
            import time
            output_filename = f"chain_{int(time.time())}.mp4"

        output_path = os.path.join(OUTPUT_DIR, output_filename)

        # Create concat file
        concat_file = os.path.join(OUTPUT_DIR, f"concat_{int(time.time())}.txt")

        with open(concat_file, 'w') as f:
            for rel_path in request.video_paths:
                full_path = os.path.join(VIDEO_DIR, rel_path)
                if not os.path.exists(full_path):
                    raise HTTPException(status_code=404,
                                       detail=f"Video not found: {rel_path}")
                f.write(f"file '{full_path}'\n")

        # Run ffmpeg
        cmd = [
            'ffmpeg', '-f', 'concat', '-safe', '0', '-i', concat_file,
            '-c', 'copy', '-y', output_path
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=300)

        # Clean up concat file
        os.remove(concat_file)

        if result.returncode != 0:
            raise Exception(f"ffmpeg failed: {result.stderr.decode()}")

        return {
            "output_path": output_path,
            "output_filename": output_filename,
            "num_videos": len(request.video_paths)
        }

    except Exception as e:
        handle_api_error(e)


@app.get("/api/merged/{filename}")
async def serve_merged_video(filename: str):
    """Serve merged video file"""
    full_path = os.path.join(OUTPUT_DIR, filename)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Merged video not found")

    return FileResponse(full_path, media_type="video/mp4")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
