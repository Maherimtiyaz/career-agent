"""Career Agent v6 - FastAPI application entrypoint."""

from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from app.api.ai import router as ai_router
from app.api.analytics import router as analytics_router
from app.api.outreach import router as outreach_router
from app.api.auth import router as auth_router
from app.api.health import router as health_router
from app.api.ingestion import router as ingestion_router
from app.api.opportunities import router as opportunities_router
from app.api.sheet import router as sheet_router
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.scheduler.jobs import run_all_scrapers

settings = get_settings()
configure_logging(settings.environment)
logger = get_logger(__name__)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler.add_job(run_all_scrapers, "interval", hours=24, id="scrape_all")
    scheduler.start()
    logger.info("startup", environment=settings.environment, scheduler="started")
    yield
    scheduler.shutdown()
    logger.info("shutdown")


app = FastAPI(
    title="Career Agent v6",
    description="Autonomous Career Operating System API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(opportunities_router)
app.include_router(sheet_router)
app.include_router(ai_router)
app.include_router(ingestion_router)
app.include_router(analytics_router)
app.include_router(outreach_router)


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    for path in schema["paths"].values():
        for method in path.values():
            if "security" in method:
                method["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return schema


app.openapi = custom_openapi


@app.get("/")
async def root() -> dict:
    return {"service": "career-agent-backend", "status": "running"}
