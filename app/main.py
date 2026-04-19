from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.internal import router as internal_router
from app.api.stats import router as stats_router
from app.api.urls import router as urls_router
from app.config import settings
from app.db.session import make_engine
from app.services.vt_client import VTClient
from app.services.vmray_client import VMRayClient
from app.workers.scheduler import attach_jobs, make_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_engine = make_engine(settings.database_url)
    app.state.http_client = httpx.AsyncClient(timeout=30.0)
    app.state.vt_client = VTClient(settings.vt_api_key, app.state.http_client)
    app.state.vmray_client = VMRayClient(
        settings.vmray_url, settings.vmray_api_key, app.state.http_client
    )

    scheduler = make_scheduler()
    attach_jobs(scheduler, app)
    if settings.pipeline_autostart:
        scheduler.start()
    app.state.scheduler = scheduler

    yield

    if scheduler.running:
        scheduler.shutdown(wait=False)
    await app.state.http_client.aclose()
    await app.state.db_engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(health_router)
app.include_router(internal_router)
app.include_router(stats_router)
app.include_router(urls_router)
