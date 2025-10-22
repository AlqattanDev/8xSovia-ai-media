"""Application configuration using Pydantic settings"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # Application
    app_name: str = "Media Gallery API"
    app_version: str = "2.0.0"
    debug: bool = False

    # Database
    database_url: str = "postgresql+asyncpg://gallery_user:password@localhost:5432/media_gallery"
    db_pool_size: int = 20
    db_max_overflow: int = 40

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    cache_ttl: int = 300  # 5 minutes

    # CORS
    allowed_origins: list[str] = ["*"]

    # API
    api_prefix: str = "/api"
    max_page_size: int = 100
    default_page_size: int = 50

    # Local Media Storage
    media_base_dir: str = "/Users/alialqattan/Downloads/8xSovia"

    # HuggingFace
    hf_token: str | None = None

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
