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
┌───────────────────────────────────────────────────┐
│  GitHub Actions Deploy (deploy.yml)               │
│  triggers on push to main                         │
│                                                   │
│  1. SSH into production server                    │
│  2. git reset --hard origin/main                  │
│  3. docker-compose up -d --build                  │
│  4. curl /health (fails workflow if unhealthy)    │
└───────────────────────────────────────────────────┘
         │
         ▼
  Production server (85.243.239.92)
  WSL2 / Ubuntu 24.04
  SSH port: 2222
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

| Secret       | Description                  |
|--------------|------------------------------|
| DEPLOY_HOST  | Server public IP             |
| DEPLOY_PORT  | SSH port (2222)              |
| DEPLOY_USER  | Linux username on server     |
| DEPLOY_KEY   | Ed25519 private key (PEM)    |

## What is NOT in this iteration

- VirusTotal polling
- VMRay integration
- Database migrations / ORM models
- Any business logic
