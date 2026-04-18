import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from testcontainers.postgres import PostgresContainer

from app.config import settings
from app.main import app


@pytest.fixture(scope="session")
def pg_container():
    with PostgresContainer("postgres:16-alpine") as pg:
        yield pg


def _run_migrations(sync_url: str) -> None:
    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", sync_url)
    command.upgrade(cfg, "head")


@pytest.fixture
def db_client(pg_container, monkeypatch):
    sync_url = pg_container.get_connection_url()
    async_url = sync_url.replace("+psycopg2", "+asyncpg")
    _run_migrations(sync_url)
    monkeypatch.setattr(settings, "database_url", async_url)
    with TestClient(app) as client:
        yield client


@pytest.fixture
def no_db_client(monkeypatch):
    monkeypatch.setattr(
        settings,
        "database_url",
        "postgresql+asyncpg://nobody:nopass@127.0.0.1:9999/nodb",
    )
    with TestClient(app) as client:
        yield client


def test_health_db_ok(db_client):
    response = db_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "db": "ok"}


def test_health_db_down(no_db_client):
    response = no_db_client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "healthy", "db": "error"}
