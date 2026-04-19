# Architecture — Iteration 3: Pipeline Foundation

## Overview

FastAPI service with async Postgres connectivity, full ingestion-and-analysis pipeline foundation:
VirusTotal comment polling → defanged URL extraction/normalization → VMRay submission/polling.
Background jobs are APScheduler-based and only start when `PIPELINE_AUTOSTART=true`; the app deploys
and stays healthy without any VT/VMRay credentials configured.

## Component diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         Docker Compose                           │
│                                                                  │
│  ┌───────────────────────────┐   ┌────────────────────────────┐  │
│  │           app             │   │            db              │  │
│  │  FastAPI / uvicorn        │──▶│    PostgreSQL 16           │  │
│  │  :8000 (host:8001)        │   │    :5432                   │  │
│  │  APScheduler (optional)   │   │                            │  │
│  └─────────────┬─────────────┘   └────────────────────────────┘  │
│                │                                                  │
└────────────────┼─────────────────────────────────────────────────┘
                 │ (optional, requires credentials)
       ┌─────────┴──────────┐
       │                    │
  VirusTotal API        VMRay API
  (v3/comments)         (v2/sample/url)
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

### Health

| Method | Path      | Healthy (200)                             | DB down (503)                        |
|--------|-----------|-------------------------------------------|--------------------------------------|
| GET    | /health   | `{"status":"healthy","db":"ok"}`          | `{"status":"healthy","db":"error"}`  |

### Read APIs

| Method | Path              | Description                                 |
|--------|-------------------|---------------------------------------------|
| GET    | /stats/summary    | Aggregate counts (comments, URLs, verdicts) |
| GET    | /urls             | Paginated URL list (`?page=1&page_size=20`) |
| GET    | /urls/{id}        | Single URL with VMRay submission detail     |

### Internal trigger endpoints (manual pipeline invocation)

| Method | Path                  | Description                                   |
|--------|-----------------------|-----------------------------------------------|
| POST   | /internal/vt/poll     | Fetch VT comments + extract URLs              |
| POST   | /internal/urls/extract| Extract URLs from stored comments             |
| POST   | /internal/vmray/submit| Submit pending URLs to VMRay                 |
| POST   | /internal/vmray/poll  | Poll in-flight VMRay submissions for verdicts |

All internal endpoints return `{"status":"disabled"}` when the relevant credentials are absent.

## Pipeline state machine

```
VTComment (stored)
      │ URLProcessPipeline
      ▼
URL.status = pending
      │ VMRaySubmitPipeline
      ▼
URL.status = submitted ── VMRaySubmission created
      │ VMRayPollPipeline
      ▼
URL.status = done  (verdict + score stored in VMRaySubmission)
     or
URL.status = failed
```

## Directory structure

```
app/
  main.py          # FastAPI app + async lifespan (engine, httpx, clients, scheduler)
  config.py        # pydantic-settings (all env vars with safe defaults)
  deps.py          # FastAPI dependency functions (get_session, get_vt_client, get_vmray_client)
  api/
    health.py      # GET /health — async, checks DB with SELECT 1
    internal.py    # POST /internal/* — pipeline trigger endpoints
    stats.py       # GET /stats/summary
    urls.py        # GET /urls, GET /urls/{id}
  db/
    base.py        # SQLAlchemy DeclarativeBase
    session.py     # make_engine(url) → AsyncEngine
  models/
    __init__.py    # imports all models (needed by Alembic autogenerate)
    vt_comment.py  # VTComment ORM model
    url.py         # URL ORM model (url_hash dedup, status state machine)
    vmray_submission.py  # VMRaySubmission ORM model
  schemas/
    stats.py       # StatsSummary pydantic response model
    url.py         # URLOut, URLListResponse pydantic response models
  services/
    url_extractor.py   # extract_urls(), url_hash() — pure functions, no I/O
    vt_client.py       # VTClient (httpx-based, is_configured guard)
    vmray_client.py    # VMRayClient (httpx-based, is_configured guard)
    pipeline.py        # VTPipeline, URLProcessPipeline, VMRaySubmitPipeline, VMRayPollPipeline
  workers/
    scheduler.py   # APScheduler setup; jobs attached only when pipeline_autostart=True
alembic/
  env.py           # reads DATABASE_URL env var, strips +asyncpg for sync
  versions/
    0001_initial.py  # baseline (empty)
    0002_add_pipeline_tables.py  # vt_comments, urls, vmray_submissions
alembic.ini        # script location, fallback sync URL
tests/
  conftest.py      # pg_container, db_urls, db_engine, db_session, db_client, no_db_client
  test_health.py   # health endpoint smoke tests
  test_url_extractor.py  # 15 unit tests for url_extractor (pure, no DB)
  test_pipeline.py       # 9 async pipeline tests with mocked VT/VMRay clients
  test_api.py            # 10 API endpoint tests via TestClient
docs/
  architecture.md  # this file
pytest.ini         # asyncio_mode=auto, session-scoped event loop
.github/workflows/
  ci.yml           # pytest on all branches
  deploy.yml       # SSH deploy on push to main
```

## Configuration

| Variable                    | Default                                      | Description                          |
|-----------------------------|----------------------------------------------|--------------------------------------|
| APP_NAME                    | vt-clickfix-vmray                            | Application name                     |
| APP_ENV                     | development                                  | Runtime environment                  |
| DATABASE_URL                | postgresql+asyncpg://app:app@db:5432/app     | Postgres DSN (async)                 |
| VT_API_KEY                  | ""                                           | VirusTotal API key (empty = disabled)|
| VT_POLL_INTERVAL_SECONDS    | 300                                          | VT polling interval                  |
| VT_ENABLED                  | false                                        | Enable VT scheduler job              |
| VMRAY_URL                   | ""                                           | VMRay base URL (empty = disabled)    |
| VMRAY_API_KEY               | ""                                           | VMRay API key                        |
| VMRAY_POLL_INTERVAL_SECONDS | 60                                           | VMRay polling interval               |
| VMRAY_ENABLED               | false                                        | Enable VMRay scheduler jobs          |
| PIPELINE_AUTOSTART          | false                                        | Start scheduler on app startup       |

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

- Dashboard UI
- Authentication / authorization on internal endpoints
- Pagination cursor for VT comment polling
- ORM relationships (lazy loading) — queries use explicit joins/subqueries
