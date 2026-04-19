import os

# Ryuk (testcontainers cleanup daemon) requires pulling an image from Docker Hub.
# Disable it — the context manager handles container cleanup correctly without it.
os.environ.setdefault("TESTCONTAINERS_RYUK_DISABLED", "true")

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.pool import NullPool
from testcontainers.postgres import PostgresContainer


def _run_migrations(sync_url: str) -> None:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(cfg, "head")


@pytest.fixture(scope="session")
def pg_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


@pytest.fixture(scope="session")
def db_urls(pg_container):
    sync_url = pg_container.get_connection_url()
    async_url = sync_url.replace("+psycopg2", "+asyncpg")
    _run_migrations(sync_url)
    return {"sync": sync_url, "async": async_url}


# Synchronous fixture avoids async teardown running after event loop is closed.
# NullPool gives each AsyncSession its own connection — no shared pool state
# between tests, which avoids "another operation is in progress" errors from
# asyncpg when connections are reused across async fixtures.
@pytest.fixture(scope="session")
def db_engine(db_urls):
    engine = create_async_engine(db_urls["async"], poolclass=NullPool)
    yield engine


@pytest.fixture
async def db_session(db_engine):
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        yield session


@pytest.fixture
def db_client(db_urls, monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "database_url", db_urls["async"])
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        yield client


@pytest.fixture
def no_db_client(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(
        settings,
        "database_url",
        "postgresql+asyncpg://nobody:nopass@127.0.0.1:9999/nodb",
    )
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as client:
        yield client
