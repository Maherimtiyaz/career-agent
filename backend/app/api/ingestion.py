"""Ingestion trigger endpoints - run scrapers on demand."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import get_current_user
from app.db.session import get_db
from app.ingestion.scrapers import SCRAPERS
from app.models.user import User

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post("/run")
async def run_scraper(
    source: str = Query(..., description="gsoc | yc_jobs | mlh | devfolio | all"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """Trigger a scraper manually. Requires authentication."""
    if source == "all":
        results = []
        for name, fn in SCRAPERS.items():
            result = await fn(db)
            results.append(result)
        return {"results": results}

    if source not in SCRAPERS:
        return {"error": f"Unknown source '{source}'. Valid: {list(SCRAPERS.keys())} or 'all'"}

    result = await SCRAPERS[source](db)
    return result


@router.get("/sources")
async def list_sources() -> dict:
    return {"sources": list(SCRAPERS.keys()) + ["all"]}
