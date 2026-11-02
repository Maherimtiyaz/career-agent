"""Infrastructure health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict:
    """Liveness check - process is up. Does not touch the database."""
    return {"status": "ok"}


@router.get("/health/db")
async def health_db(db: AsyncSession = Depends(get_db)) -> dict:
    """Readiness check - confirms the database connection actually works."""
    result = await db.execute(text("SELECT 1"))
    value = result.scalar_one()
    return {"status": "ok", "database": "connected", "check": value}
