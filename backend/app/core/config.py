"""
Application configuration settings.
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = "ScorpiusAO"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Database
    database_url: str = "postgresql+asyncpg://scorpius:scorpius_password@localhost:5433/scorpius_db"
    database_pool_size: int = 20
    database_max_overflow: int = 10

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Celery
    celery_broker_url: str = "amqp://guest:guest@localhost:5672//"
    celery_result_backend: str = "redis://localhost:6379/1"

    # AI APIs
    anthropic_api_key: str = "your_anthropic_key_here"
    openai_api_key: str | None = None

    # AI Configuration
    llm_model: str = "claude-sonnet-4-20241022"
    embedding_model: str = "text-embedding-3-small"
    max_tokens: int = 4096
    temperature: float = 0.7
    chunk_size: int = 1024
    chunk_overlap: int = 200

    # Security
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    # MinIO / S3
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "scorpius-documents"
    minio_secure: bool = False

    # Logging
    log_level: str = "INFO"
    sentry_dsn: str | None = None

    # Rate Limiting
    rate_limit_per_minute: int = 60

    @property
    def database_url_sync(self) -> str:
        """Return synchronous database URL for Alembic and Celery (psycopg2)."""
        # Replace +asyncpg with +psycopg2 for sync operations
        return self.database_url.replace("+asyncpg", "+psycopg2")


settings = Settings()
