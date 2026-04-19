# Architecture — Iteration 4: Dashboard & Results

## Overview

FastAPI service with async Postgres connectivity, full ingestion-and-analysis pipeline, enriched
read APIs, and a built-in server-rendered HTML UI for analyst review.

Pipeline: VirusTotal comment polling → defanged URL extraction/normalization → VMRay
submission/polling → enriched verdict storage → dashboard & per-URL detail views.

Background jobs (APScheduler) only start when `PIPELINE_AUTOSTART=true`; the app deploys and
stays healthy without any VT/VMRay credentials configured.

## Component diagram

```
┌──────────────────────────────────────────────────────────────────┐
│                         Docker Compose                           │
│                                                                  │
│  ┌───────────────────────────┐   ┌────────────────────────────┐  │
│  │           app             │   │            db              │  │
│  │  FastAPI / uvicorn        │──▶│    PostgreSQL 16           │  │
│  │  :8000 (host:80)          │   │    :5432                   │  │
│  │  APScheduler (optional)   │   │                            │  │
│  └─────────────┬─────────────┘   └────────────────────────────┘  │
│                │                                                  │
└────────────────┼─────────────────────────────────────────────────┘
                 │ (optional, requires credentials)
       ┌─────────┴──────────┐
       │                    │
  VirusTotal API        VMRay API
  (v3/comments)         (rest/sample, rest/submission)
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
│  4. health check via SSH: /health, alembic.ini       │
│     presence, POST /internal/vt/poll                 │
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

| Method | Path              | Description                                          |
|--------|-------------------|------------------------------------------------------|
| GET    | /stats/summary    | Dashboard-ready aggregate (see fields below)         |
| GET    | /urls             | Paginated URL list with filters                      |
| GET    | /urls/{id}        | Enriched URL detail with source comment + VMRay data |

#### GET /stats/summary fields

| Field | Type | Description |
|-------|------|-------------|
| total_comments | int | VT comments ingested |
| total_urls | int | Unique normalized URLs |
| total_unique_normalized_urls | int | Same as total_urls (deduplicated on insert) |
| url_statuses | object | Counts per status: pending/submitted/analyzing/done/failed |
| total_submissions | int | VMRay submissions created |
| completed_submissions | int | Submissions with a final verdict |
| verdict_counts | object | malicious/suspicious/clean/unknown |
| top_domains | list[{domain, count}] | Top 10 domains by URL count |
| latest_comment_at | datetime\|null | Timestamp of last ingested comment |
| latest_url_at | datetime\|null | Timestamp of last extracted URL |
| latest_submission_at | datetime\|null | Timestamp of last VMRay submission |

#### GET /urls query parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| page | int (default 1) | Page number |
| page_size | int (default 20, max 100) | Items per page |
| status | string | Filter by URL status (pending/submitted/analyzing/done/failed) |
| verdict | string | Filter by VMRay verdict (malicious/suspicious/clean) |
| domain | string | Exact domain match |
| q | string | Substring search on normalized_url (case-insensitive) |
| sort | newest\|oldest\|updated | Sort order (default: newest) |

#### GET /urls/{id} response fields (URLDetailOut)

| Field | Description |
|-------|-------------|
| id, normalized_url, original_defanged | URL identifiers |
| domain, scheme | Parsed from normalized URL |
| status | Pipeline state |
| created_at, updated_at | Timestamps |
| source_comment.comment_id | VT comment ID |
| source_comment.content | Full comment text |
| source_comment.published_at | Comment timestamp |
| submission.submission_id | VMRay submission integer ID |
| submission.verdict | malicious/suspicious/clean/null |
| submission.score | VMRay score integer |
| submission.severity | VMRay severity string |
| submission.submission_status | VMRay status string (e.g. inwork/finished) |
| submission.report_url | submission_webif_url — direct link to VMRay report |
| submission.submitted_at, completed_at | Submission timestamps |

### Internal trigger endpoints

| Method | Path                  | Description                                   |
|--------|-----------------------|-----------------------------------------------|
| POST   | /internal/vt/poll     | Fetch VT comments + extract URLs              |
| POST   | /internal/urls/extract| Extract URLs from stored comments             |
| POST   | /internal/vmray/submit| Submit pending URLs to VMRay                 |
| POST   | /internal/vmray/poll  | Poll in-flight VMRay submissions for verdicts |

All internal endpoints return `{"status":"disabled"}` when credentials are absent.

### UI pages (HTML)

| Method | Path | Description |
|--------|------|-------------|
| GET | /dashboard | Summary counts, verdict stats, top domains, activity timestamps |
| GET | /urls/view | Paginated URL list with filter form (status/verdict/domain/search/sort) |
| GET | /urls/view/{id} | Full URL detail: source comment, VMRay verdict/score/severity/report |

## VMRay enrichment fields (iteration 4 additions)

Fields added to `vmray_submissions` table based on Cloud API Reference v2026.2.1 `Submission` schema:

| DB Column | API Field | Description |
|-----------|-----------|-------------|
| report_url | submission_webif_url | Direct link to VMRay web interface report |
| severity | submission_severity | Severity classification string |
| submission_status | submission_status | Current submission status (inwork/finished/etc.) |

Both submit and poll pipelines capture these fields when present in the API response.

## Screenshot support

VMRay API v2026.2.1 supports screenshot retrieval via analysis archives:
`GET /rest/analysis/<analysis_id>/archive?filename=screenshots`

**Intentionally not implemented** in this iteration because:
1. Screenshots require traversing submission → analysis (separate API call to resolve analysis_id)
2. Archive download returns a binary ZIP file — not a direct URL reference
3. Serving screenshots would require a binary proxy endpoint or external storage
4. No `screenshot_url` field exists anywhere in the Submission or Analysis schemas

This can be added in a future iteration by calling `GET /rest/analysis/submission/<submission_id>`
to resolve `analysis_id`, then constructing download links.

## Pipeline state machine

```
VTComment (stored)
      │ URLProcessPipeline  → stores domain, scheme
      ▼
URL.status = pending
      │ VMRaySubmitPipeline → creates VMRaySubmission with report_url, severity, submission_status
      ▼
URL.status = submitted
      │ VMRayPollPipeline   → updates verdict, score, severity, submission_status, report_url
      ▼
URL.status = done  (completed_at set, verdict/score/report_url stored)
     or
URL.status = failed
```

## Directory structure

```
app/
  main.py          # FastAPI app + async lifespan (engine, httpx, clients, scheduler)
  config.py        # pydantic-settings (all env vars with safe defaults)
  deps.py          # FastAPI dependency functions
  api/
    health.py      # GET /health
    internal.py    # POST /internal/* — pipeline trigger endpoints
    stats.py       # GET /stats/summary — dashboard-ready aggregation
    urls.py        # GET /urls (filtered/sorted/paginated), GET /urls/{id} (enriched detail)
    ui.py          # GET /dashboard, GET /urls/view, GET /urls/view/{id} — HTML pages
  db/
    base.py        # SQLAlchemy DeclarativeBase
    session.py     # make_engine(url) → AsyncEngine
  models/
    __init__.py
    vt_comment.py  # VTComment: comment_id, content, published_at, raw_response
    url.py         # URL: url_hash, normalized_url, domain, scheme, status
    vmray_submission.py  # VMRaySubmission: verdict, score, severity, report_url, submission_status
  schemas/
    stats.py       # StatsSummary, URLStatusCounts, VerdictCounts, TopDomain
    url.py         # URLOut, URLDetailOut, VMRaySubmissionOut, VTCommentRef, URLListResponse
  services/
    url_extractor.py   # extract_urls(), extract_domain_scheme(), url_hash()
    vt_client.py       # VTClient
    vmray_client.py    # VMRayClient
    pipeline.py        # VTPipeline, URLProcessPipeline, VMRaySubmitPipeline, VMRayPollPipeline
  workers/
    scheduler.py   # APScheduler setup
  templates/
    dashboard.html     # /dashboard — stats + top domains
    urls_list.html     # /urls/view — paginated list with filters
    url_detail.html    # /urls/view/{id} — analyst detail view
alembic/
  versions/
    0001_initial.py
    0002_add_pipeline_tables.py
    0003_add_enrichment_columns.py  # domain, scheme, report_url, severity, submission_status
tests/
  conftest.py
  test_url_extractor.py
  test_pipeline.py      # includes domain/scheme extraction and VMRay enrichment field tests
  test_api.py           # includes filter/sort, detail shape, UI page tests
docs/
  architecture.md
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

## Exact API contracts

### VirusTotal (source: https://docs.virustotal.com/reference/overview)

| Property | Value |
|----------|-------|
| Endpoint | `GET https://www.virustotal.com/api/v3/comments` |
| Auth | `x-apikey: <key>` header |
| Parameters | `limit` (int), `filter` (string), `cursor` (string) |
| Filter | `filter=tag:clickfix` — TAG-BASED. Returns only comments explicitly tagged "clickfix". |
| Pagination | `meta.cursor` in response |
| Comment fields | `attributes.text`, `attributes.date` (Unix timestamp), `attributes.tags`, `attributes.votes`, `attributes.html`. No `author` field. |

### VMRay (source: .local_docs/vmray — Cloud API Reference v2026.2.1)

**Submit URL** — `POST /rest/sample/submit`
- Auth: `Authorization: api_key <key>` header
- Body: multipart form, field `sample_url=<url>`
- Response: `SampleSubmit → SubmisssionResult → submissions[0]` (Submission object)
- Fields used: `submission_id` (int), `submission_webif_url` (str), `submission_severity`, `submission_status`

**Get Submission** — `GET /rest/submission/<submission_id>`
- Auth: `Authorization: api_key <key>` header
- Response: `SubmissionItem → data` (Submission object)
- Fields used: `submission_finished` (bool), `submission_verdict` (VerdictTypeEnum|null),
  `submission_score` (int|null), `submission_severity` (SeverityTypeEnum|null),
  `submission_status` (SubmissionStatusEnum), `submission_webif_url` (str)
