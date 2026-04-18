# Architecture — Iteration 1: Bootstrap + CI/CD

## Overview

Minimal runnable service with a health endpoint and Postgres, with automated CI and SSH-based deployment to the production server.

## Component diagram

```
┌─────────────────────────────────────────────────────┐
│                   Docker Compose                    │
│                                                     │
│  ┌─────────────────────┐   ┌─────────────────────┐  │
│  │      app            │   │       db            │  │
│  │  FastAPI / uvicorn  │──▶│   PostgreSQL 16     │  │
│  │  :8000              │   │   :5432             │  │
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
│  CI (ci.yml)      │  ← triggers on every push / PR
│  pytest tests     │
└────────┬──────────┘
         │ pass
         ▼
   PR merged to main
         │
         ▼
┌──────────────────────────────────────────────────────┐
│  GitHub Actions Deploy (deploy.yml)                  │
│  triggers on push to main                            │
│                                                      │
│  1. Write deploy private key + known_hosts           │
│  2. SSH to 77.42.72.36:22 as deploy                  │
│  3. git clone (first run) or git fetch+reset (update)│
│  4. docker compose up -d --build                     │
│  5. curl http://77.42.72.36:8000/health              │
│     → fails workflow if unhealthy                    │
└──────────────────────────────────────────────────────┘
         │
         ▼
  Production server — 77.42.72.36
  Ubuntu 24.04 / Docker 29.x
  repo at /opt/vt-clickfix-vmray
```

## Endpoints

| Method | Path      | Description        |
|--------|-----------|--------------------|
| GET    | /health   | Liveness check     |

## Directory structure

```
app/
  main.py          # FastAPI application entry point
  config.py        # Environment-based configuration (pydantic-settings)
  api/
    health.py      # GET /health router
  db/              # (placeholder — Postgres integration in iteration 3)
  models/          # (placeholder — ORM models in iteration 3)
  schemas/         # (placeholder — Pydantic schemas in iteration 3)
  services/        # (placeholder — business logic in later iterations)
  workers/         # (placeholder — background workers in later iterations)
tests/
  test_health.py   # API tests for /health
docs/
  architecture.md  # this file
.github/workflows/
  ci.yml           # pytest on all branches
  deploy.yml       # SSH deploy on push to main
```

## Configuration

All settings are read from environment variables (or `.env` file locally):

| Variable       | Default                                  | Description         |
|----------------|------------------------------------------|---------------------|
| APP_NAME       | vt-clickfix-vmray                        | Application name    |
| APP_ENV        | development                              | Runtime environment |
| DATABASE_URL   | postgresql://app:app@db:5432/app         | Postgres DSN        |

## GitHub Actions secrets (deploy)

| Secret           | Description                               |
|------------------|-------------------------------------------|
| DEPLOY_HOST      | Server public IP (77.42.72.36)            |
| DEPLOY_PORT      | SSH port (22)                             |
| DEPLOY_USER      | Linux username on server (deploy)         |
| DEPLOY_KEY       | Ed25519 private key (PEM)                 |
| DEPLOY_HOST_KEY  | Server ed25519 host key for known_hosts   |

## What is NOT in this iteration

- VirusTotal polling
- VMRay integration
- Database migrations / ORM models
- Any business logic
