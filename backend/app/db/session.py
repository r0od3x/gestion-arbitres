"""Moteur et sessions SQLAlchemy asynchrones."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings


def _engine_kwargs() -> dict[str, Any]:
    if settings.is_sqlite:
        # SQLite n'a pas de pool réseau ; pas d'options de pool à passer.
        return {"echo": settings.DEBUG}
    return {
        "echo": settings.DEBUG,
        "pool_size": 10,
        "max_overflow": 20,
        "pool_pre_ping": True,
    }


engine: AsyncEngine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs())

SessionFactory = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dépendance FastAPI : une session par requête, rollback en cas d'erreur."""
    async with SessionFactory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
