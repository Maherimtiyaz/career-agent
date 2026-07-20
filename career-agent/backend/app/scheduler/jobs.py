"""Scheduled background jobs."""

from app.core.logging import get_logger

logger = get_logger(__name__)


async def run_all_scrapers() -> None:
    """Run all scrapers on schedule. Called by APScheduler."""
    from app.db.session import AsyncSessionLocal
    from app.ingestion.scrapers import SCRAPERS

    logger.info("scheduler.scraper_run.start")
    async with AsyncSessionLocal() as session:
        for name, fn in SCRAPERS.items():
            try:
                result = await fn(session)
                logger.info("scheduler.scraper_run.done", **result)
            except Exception as e:
                logger.error("scheduler.scraper_run.error", source=name, error=str(e))
    logger.info("scheduler.scraper_run.complete")
