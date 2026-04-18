# Architecture — Iteration 2: Postgres Integration

## Overview

FastAPI service with async Postgres connectivity, Alembic migrations, and a health endpoint that reports both application and database status.

## Component diagram

```
┌─────────────────────────────────────────────────────┐
│                   Docker Compose                    │
│                                                     │
│  ┌─────────────────────┐   ┌─────────────────────┐  │
│  │      app            │   │       db            │  │
│  │  FastAPI / uvicorn  │──▶│   PostgreSQL 16     │  │
│  │  :8000 (host:8001)  │   │   :5432             │  │
│  └─────────────────────┘   └─────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## CI/CD flow

```
Developer pushes branch
        │
        ▼
┌───────────────────┐
│  GitHub Actions   │
│  CI (ci.yml)      │  ← runs pytest (testcontainers spins up Postgres)
└────────┬──────────┘
         │ pass
         ▼
   PR merged to main
         │
         ▼
┌──────────────────────────────────────────────────────┐
│  GitHub Actions Deploy (deploy.yml)                  │
│                                                      │
│  1. SSH to 77.42.72.36:22 as deploy                  │
│  2. git clone (first run) or git fetch+reset         │
│  3. docker compose up -d --build                     │
│  4. curl localhost:8001/health via SSH               │
│     → fails workflow if unhealthy                    │
└──────────────────────────────────────────────────────┘
         │
         ▼
  Production server — 77.42.72.36
  repo at /opt/vt-clickfix-vmray
```

## Endpoints

| Method | Path      | Healthy response (200)                    | DB down (503)                        |
|--------|-----------|-------------------------------------------|--------------------------------------|
| GET    | /health   | `{"status":"healthy","db":"ok"}`          | `{"status":"healthy","db":"error"}`  |

## Directory structure

```
app/
  main.py          # FastAPI app + async lifespan (engine init/dispose)
  config.py        # pydantic-settings (DATABASE_URL, APP_ENV, APP_NAME)
  api/
    health.py      # GET /health — async, checks DB with SELECT 1
  db/
    base.py        # SQLAlchemy DeclarativeBase (shared by all models)
    session.py     # make_engine(url) → AsyncEngine
  models/          # (placeholder — ORM models in iteration 3)
  schemas/         # (placeholder — Pydantic schemas in iteration 3)
  services/        # (placeholder — business logic in later iterations)
  workers/         # (placeholder — background workers in later iterations)
alembic/
  env.py           # reads DATABASE_URL env var, strips +asyncpg for sync
  versions/
    0001_initial.py  # baseline (empty)
alembic.ini        # script location, fallback sync URL
tests/
  conftest.py      # disables testcontainers Ryuk (no Docker Hub needed)
  test_health.py   # integration tests: DB ok → 200, DB down → 503
docs/
  architecture.md  # this file
.github/workflows/
  ci.yml           # pytest on all branches
  deploy.yml       # SSH deploy on push to main
```

## Configuration

| Variable       | Default                                      | Description           |
|----------------|----------------------------------------------|-----------------------|
| APP_NAME       | vt-clickfix-vmray                            | Application name      |
| APP_ENV        | development                                  | Runtime environment   |
| DATABASE_URL   | postgresql+asyncpg://app:app@db:5432/app     | Postgres DSN (async)  |

Alembic derives its sync URL from `DATABASE_URL` by stripping `+asyncpg`.

## GitHub Actions secrets (deploy)

| Secret           | Description                               |
|------------------|-------------------------------------------|
| DEPLOY_HOST      | Server public IP (77.42.72.36)            |
| DEPLOY_PORT      | SSH port (22)                             |
| DEPLOY_USER      | Linux username on server (deploy)         |
| DEPLOY_KEY       | Ed25519 private key (PEM)                 |
| DEPLOY_HOST_KEY  | Server ed25519 host key (known_hosts)     |

## What is NOT in this iteration

- VirusTotal polling
- VMRay integration
- ORM models (next iteration)
- Any business logic
