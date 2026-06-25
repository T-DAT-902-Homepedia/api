"""Pool de connexions asyncpg (cycle de vie géré par le lifespan FastAPI)."""

from collections.abc import AsyncIterator

import asyncpg
from fastapi import HTTPException, Request

from .config import settings


async def create_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(
        dsn=settings.database_url,
        min_size=settings.pool_min_size,
        max_size=settings.pool_max_size,
    )


async def get_connection(request: Request) -> AsyncIterator[asyncpg.Connection]:
    """Dépendance FastAPI : fournit une connexion empruntée au pool."""
    pool: asyncpg.Pool | None = getattr(request.app.state, "pool", None)
    if pool is None:
        # Lifespan non terminé / pool indisponible : 503 plutôt qu'AttributeError.
        raise HTTPException(status_code=503, detail="Database pool not ready")
    async with pool.acquire() as conn:
        yield conn
