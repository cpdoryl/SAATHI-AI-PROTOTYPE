"""
SAATHI AI — Database Engine & Session Factory
Supports SQLite (local dev) and PostgreSQL (production).
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from config import settings

# ─── Sync engine (for Alembic migrations) ────────────────────────────────────
sync_engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=settings.DEBUG_MODE,
)

# ─── Async engine (for FastAPI endpoints) ────────────────────────────────────
async_db_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://").replace(
    "sqlite:///", "sqlite+aiosqlite:///"
)
async_engine = create_async_engine(async_db_url, echo=settings.DEBUG_MODE)

AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db():
    """FastAPI dependency — yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
