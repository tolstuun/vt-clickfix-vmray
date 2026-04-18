from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.config import settings
from app.db.session import make_engine


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db_engine = make_engine(settings.database_url)
    yield
    await app.state.db_engine.dispose()


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(health_router)
