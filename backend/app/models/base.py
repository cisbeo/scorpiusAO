"""
SQLAlchemy base model and database session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

# Base class for models
Base = declarative_base()

# Async engine for API operations
async_engine = create_async_engine(
    settings.database_url,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,
)

# Sync engine for Alembic migrations
sync_engine = create_engine(
    settings.database_url_sync,
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    echo=settings.debug,
)

# Session factories
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync session for Alembic migrations
SessionLocal = sessionmaker(
    sync_engine,
    autocommit=False,
    autoflush=False,
)

# Dedicated sync session for Celery tasks (using psycopg2)
# Create a separate engine to avoid fork issues
_celery_engine = None

def get_celery_session():
    """
    Get a sync database session for Celery tasks.
    Lazy initialization to avoid fork() issues with connection pools.
    """
    global _celery_engine
    if _celery_engine is None:
        _celery_engine = create_engine(
            settings.database_url_sync,
            pool_size=5,
            max_overflow=10,
            echo=settings.debug,
            pool_pre_ping=True,  # Verify connections before using them
        )
    return sessionmaker(
        _celery_engine,
        autocommit=False,
        autoflush=False,
    )()


async def get_db():
    """Dependency for getting async database sessions."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
