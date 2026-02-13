"""
Database connection and session management
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)

from ..config import get_settings

# Global engine and session factory
_engine = None
_session_factory = None


def get_database_url() -> str:
    """Build async database URL"""
    settings = get_settings()
    return (
        f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
        f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
    )


async def init_db() -> None:
    """Initialize database connection"""
    global _engine, _session_factory
    
    if _engine is not None:
        return
    
    database_url = get_database_url()
    
    _engine = create_async_engine(
        database_url,
        echo=get_settings().debug,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True
    )
    
    _session_factory = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False
    )


async def close_db() -> None:
    """Close database connection"""
    global _engine, _session_factory
    
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _session_factory = None


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session context manager"""
    if _session_factory is None:
        await init_db()
    
    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database session"""
    async with get_session() as session:
        yield session
