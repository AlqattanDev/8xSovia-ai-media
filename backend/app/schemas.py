"""Pydantic schemas for request/response validation"""
from pydantic import BaseModel, Field, ConfigDict, field_validator
from datetime import datetime
from uuid import UUID
from typing import Optional


class ChildPostSchema(BaseModel):
    """Child post response schema"""
    id: UUID
    parent_post_id: UUID
    user_id: UUID
    create_time: datetime
    prompt: Optional[str] = None
    original_prompt: Optional[str] = None
    media_type: str
    media_url: str
    mime_type: Optional[str] = None
    model_name: Optional[str] = None
    mode: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator('media_url', mode='after')
    @classmethod
    def transform_media_url(cls, v: str) -> str:
        """Transform local https_/ paths to backend media URLs"""
        if v.startswith('https_/'):
            # Convert local path to backend media endpoint
            return f"http://localhost:8000/media/{v}"
        return v


class MediaPostSchema(BaseModel):
    """Media post response schema"""
    id: UUID
    user_id: UUID
    create_time: datetime
    prompt: Optional[str] = None
    original_prompt: Optional[str] = None
    media_type: str
    media_url: str
    mime_type: Optional[str] = None
    model_name: Optional[str] = None
    like_status: bool = False
    child_posts: list[ChildPostSchema] = []

    model_config = ConfigDict(from_attributes=True)

    @field_validator('media_url', mode='after')
    @classmethod
    def transform_media_url(cls, v: str) -> str:
        """Transform local https_/ paths to backend media URLs"""
        if v.startswith('https_/'):
            # Convert local path to backend media endpoint
            return f"http://localhost:8000/media/{v}"
        return v


class StatsResponse(BaseModel):
    """Statistics response schema"""
    total_items: int = Field(..., alias="totalItems")
    total_videos: int = Field(..., alias="totalVideos")
    liked_items: int = Field(..., alias="likedItems")
    models: list[dict] = []

    model_config = ConfigDict(populate_by_name=True)


class PromptGalleryItem(BaseModel):
    """Prompt gallery entry with usage statistics"""
    prompt: str
    usage_count: int
    mode_type: str  # 'parent', 'custom', 'both'
    sample_posts: list[MediaPostSchema]
    first_used: datetime
    last_used: datetime

    model_config = ConfigDict(from_attributes=True)


class PromptStatsResponse(BaseModel):
    """Prompt usage statistics"""
    total_unique_prompts: int
    total_custom_prompts: int
    total_parent_prompts: int
    custom_mode_count: int
    normal_mode_count: int
    custom_mode_percentage: float
    most_used_prompts: list[dict]  # Simple dict for top prompts

    model_config = ConfigDict(from_attributes=True)


class CollectionCreate(BaseModel):
    """Collection creation request"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_smart: bool = False
    smart_filters: Optional[dict] = None


class CollectionUpdate(BaseModel):
    """Collection update request"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_smart: Optional[bool] = None
    smart_filters: Optional[dict] = None


class CollectionItemSchema(BaseModel):
    """Collection item response"""
    id: UUID
    collection_id: UUID
    media_post_id: UUID
    added_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CollectionSchema(BaseModel):
    """Collection response schema"""
    id: UUID
    user_id: UUID
    name: str
    description: Optional[str] = None
    is_smart: bool
    smart_filters: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    item_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CollectionWithItemsSchema(CollectionSchema):
    """Collection with media posts"""
    items: list[MediaPostSchema] = []

    model_config = ConfigDict(from_attributes=True)


class UserPreferenceSchema(BaseModel):
    """User preference response schema"""
    id: UUID
    user_id: UUID
    preferences: dict
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserPreferenceUpdate(BaseModel):
    """User preference update request"""
    preferences: dict


class ImportChildPost(BaseModel):
    """Child post import data"""
    id: UUID
    userId: UUID
    createTime: str
    prompt: str = ""
    originalPrompt: str = ""
    mediaType: str
    mediaUrl: str
    mimeType: str
    originalPostId: Optional[UUID] = None
    modelName: Optional[str] = None
    mode: Optional[str] = "normal"


class ImportMediaPost(BaseModel):
    """Media post import data"""
    id: UUID
    userId: UUID
    createTime: str
    prompt: str = ""
    originalPrompt: str = ""
    mediaType: str
    mediaUrl: str
    mimeType: str
    modelName: Optional[str] = None
    userInteractionStatus: Optional[dict] = None
    childPosts: list[ImportChildPost] = []


class ImportRequest(BaseModel):
    """Import request schema"""
    posts: list[ImportMediaPost]


class ImportResponse(BaseModel):
    """Import response schema"""
    posts_imported: int
    child_posts_imported: int
    posts_skipped: int
    total_processed: int
