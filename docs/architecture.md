# Architecture — Iteration 1: Bootstrap

## Overview

Minimal runnable service with a health endpoint and Postgres, ready for business logic in subsequent iterations.

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
  db/              # (placeholder — Postgres integration in iteration 2)
  models/          # (placeholder — ORM models in iteration 2)
  schemas/         # (placeholder — Pydantic schemas in iteration 2)
  services/        # (placeholder — business logic in later iterations)
  workers/         # (placeholder — background workers in later iterations)
tests/
  test_health.py   # API tests for /health
docs/
  architecture.md  # this file
```

## Configuration

All settings are read from environment variables (or `.env` file locally):

| Variable       | Default                                  | Description         |
|----------------|------------------------------------------|---------------------|
| APP_NAME       | vt-clickfix-vmray                        | Application name    |
| APP_ENV        | development                              | Runtime environment |
| DATABASE_URL   | postgresql://app:app@db:5432/app         | Postgres DSN        |

## What is NOT in this iteration

- VirusTotal polling
- VMRay integration
- Database migrations / ORM models
- Any business logic
