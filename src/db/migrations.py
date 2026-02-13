"""
Database migrations
Run with: python -m src.db.migrations
"""
import asyncio
from sqlalchemy import text

from .session import init_db, close_db, get_session
from .models import Base


async def create_tables():
    """Create all tables"""
    from .session import _engine
    
    await init_db()
    
    async with _engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ Tables created successfully")


async def drop_tables():
    """Drop all tables (DANGER!)"""
    from .session import _engine
    
    await init_db()
    
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    print("⚠️ All tables dropped")


async def run_migrations():
    """Run database migrations"""
    try:
        await create_tables()
    finally:
        await close_db()


if __name__ == "__main__":
    asyncio.run(run_migrations())
