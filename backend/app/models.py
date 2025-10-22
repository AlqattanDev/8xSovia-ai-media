"""SQLAlchemy models"""
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from .database import Base


def utc_now():
    """Get current UTC time as naive datetime"""
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    """User model"""
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    media_posts = relationship("MediaPost", back_populates="user", cascade="all, delete-orphan")
    child_posts = relationship("ChildPost", back_populates="user", cascade="all, delete-orphan")


class MediaPost(Base):
    """Media post model (parent posts)"""
    __tablename__ = "media_posts"

    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    create_time = Column(DateTime, nullable=False, default=utc_now, index=True)
    prompt = Column(Text)
    original_prompt = Column(Text)
    media_type = Column(String(50), nullable=False, index=True)
    media_url = Column(Text, nullable=False)
    mime_type = Column(String(100))
    model_name = Column(String(100), index=True)
    like_status = Column(Boolean, default=False, index=True)
    extra_metadata = Column(JSONB, default={})
    first_frame_hash = Column(String(64), index=True)  # Perceptual hash of first frame
    last_frame_hash = Column(String(64), index=True)  # Perceptual hash of last frame
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    user = relationship("User", back_populates="media_posts")
    child_posts = relationship("ChildPost", back_populates="parent_post", cascade="all, delete-orphan", lazy="selectin")

    # Indexes
    __table_args__ = (
        Index('idx_media_user_time', 'user_id', 'create_time'),
    )


class ChildPost(Base):
    """Child post model (generated videos)"""
    __tablename__ = "child_posts"

    id = Column(UUID(as_uuid=True), primary_key=True)
    parent_post_id = Column(UUID(as_uuid=True), ForeignKey("media_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    create_time = Column(DateTime, nullable=False, default=utc_now, index=True)
    prompt = Column(Text)
    original_prompt = Column(Text)
    media_type = Column(String(50), nullable=False)
    media_url = Column(Text, nullable=False)
    mime_type = Column(String(100))
    model_name = Column(String(100), index=True)
    mode = Column(String(50), index=True)
    extra_metadata = Column(JSONB, default={})
    first_frame_hash = Column(String(64), index=True)  # Perceptual hash of first frame
    last_frame_hash = Column(String(64), index=True)  # Perceptual hash of last frame
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    parent_post = relationship("MediaPost", back_populates="child_posts")
    user = relationship("User", back_populates="child_posts")

    # Indexes for prompt features
    # Note: original_prompt cannot be indexed due to PostgreSQL B-tree size limit
    __table_args__ = (
        Index('idx_child_mode_model', 'mode', 'model_name'),
    )


class Collection(Base):
    """Collection model for organizing media posts"""
    __tablename__ = "collections"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_smart = Column(Boolean, default=False, nullable=False)
    smart_filters = Column(JSONB)  # Stores filter criteria for smart collections
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    user = relationship("User", backref="collections")
    items = relationship("CollectionItem", back_populates="collection", cascade="all, delete-orphan")


class CollectionItem(Base):
    """Collection item model - links media posts to collections"""
    __tablename__ = "collection_items"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    collection_id = Column(UUID(as_uuid=True), ForeignKey("collections.id", ondelete="CASCADE"), nullable=False, index=True)
    media_post_id = Column(UUID(as_uuid=True), ForeignKey("media_posts.id", ondelete="CASCADE"), nullable=False, index=True)
    added_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    collection = relationship("Collection", back_populates="items")
    media_post = relationship("MediaPost", backref="collection_items")

    # Unique constraint - a post can only be in a collection once
    __table_args__ = (
        Index('idx_unique_collection_post', 'collection_id', 'media_post_id', unique=True),
    )


class UserPreference(Base):
    """User preferences model for storing UI/UX customizations"""
    __tablename__ = "user_preferences"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    preferences = Column(JSONB, nullable=False, default={
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
    })
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    user = relationship("User", backref="preferences")
