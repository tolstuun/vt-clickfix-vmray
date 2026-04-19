# vt-clickfix-vmray

A service that polls VirusTotal for ClickFix-related comments, extracts and normalizes defanged URLs, submits them to VMRay for analysis, and presents results via dashboards.

## Requirements

- Python 3.12+
- Docker and Docker Compose

## Setup

```bash
git clone https://github.com/tolstuun/vt-clickfix-vmray.git
cd vt-clickfix-vmray
make install
```

## Run locally (Docker Compose)

```bash
make up    # start app + Postgres
make logs  # view logs
make down  # stop
```

The API is available at http://localhost:8080.

## Test

```bash
make test
```

## Database migrations

```bash
make migrate
```

## Health check

```
GET /health
→ 200 {"status": "healthy", "db": "ok"}    — app and DB healthy
→ 503 {"status": "healthy", "db": "error"} — DB unreachable
```

## Dashboard and UI

The service ships a built-in HTML UI (no external frontend framework):

| URL | Description |
|-----|-------------|
| `/dashboard` | Summary counts, verdict stats, top domains, activity timestamps |
| `/urls/view` | Paginated URL list with filters (status, verdict, domain, search, sort) |
| `/urls/view/{id}` | Full analyst detail: source comment, VMRay verdict/score/severity/report link |

## API reference

### Stats summary — `GET /stats/summary`

Returns dashboard-ready aggregation including:
- `total_comments`, `total_urls`, `total_unique_normalized_urls`
- `url_statuses`: pending/submitted/analyzing/done/failed counts
- `total_submissions`, `completed_submissions`
- `verdict_counts`: malicious/suspicious/clean/unknown
- `top_domains`: top 10 domains by URL count
- `latest_comment_at`, `latest_url_at`, `latest_submission_at`

### URL list — `GET /urls`

| Parameter | Default | Description |
|-----------|---------|-------------|
| `page` | 1 | Page number |
| `page_size` | 20 | Items per page (max 100) |
| `status` | — | Filter by pipeline status |
| `verdict` | — | Filter by VMRay verdict |
| `domain` | — | Exact domain match |
| `q` | — | Substring search on normalized URL |
| `sort` | newest | newest / oldest / updated |

### URL detail — `GET /urls/{id}`

Returns enriched analyst view including: `original_defanged`, `normalized_url`, `domain`,
`scheme`, `status`, `source_comment` (with full comment text), and `submission` with
`verdict`, `score`, `severity`, `submission_status`, and `report_url` (direct VMRay link).

## API assumptions and limitations

### VirusTotal

- **Endpoint**: `GET /api/v3/comments` with `filter=tag:clickfix`
- **Authentication**: `x-apikey` request header
- **Pagination**: cursor-based via `meta.cursor` in response
- **`filter=tag:clickfix` is a TAG-BASED filter, not full-text search.** It returns
  only comments that VT users have explicitly tagged with the `clickfix` tag. Comments
  that mention "clickfix" in their body but carry no such tag are NOT returned.
- The documented comment attributes are `text`, `date` (Unix timestamp), `tags`, `votes`,
  and `html`. There is no `author` field in the documented API; it is always stored as
  empty string internally.
- Credentials are optional: the app starts and stays healthy without `VT_API_KEY`.
  Background polling only runs when `VT_ENABLED=true` and `PIPELINE_AUTOSTART=true`.

### VMRay

- **Submit URL**: `POST /rest/sample/submit` with form field `sample_url=<url>`
  - Auth: `Authorization: api_key <key>` header
  - Response schema: `SampleSubmit` → `data.submissions[0].submission_id` (integer)
- **Get submission**: `GET /rest/submission/<submission_id>`
  - Response schema: `SubmissionItem` → `data` (Submission object)
  - Fields used: `submission_finished` (bool), `submission_verdict` (`"malicious"` | `"suspicious"` | `"clean"` | null),
    `submission_score` (int | null), `submission_severity` (string | null),
    `submission_status` (string), `submission_webif_url` (string — stored as `report_url`)
- Analysis is considered complete when `submission_finished == true`.
- Screenshot support: VMRay API supports screenshots via `GET /rest/analysis/<id>/archive?filename=screenshots`
  but this requires resolving analysis_id from submission (extra API call) and downloading a binary ZIP.
  **Not implemented** — see architecture.md for details.
- Credentials are optional: the app starts and stays healthy without `VMRAY_URL` /
  `VMRAY_API_KEY`. Submission/polling only runs when `VMRAY_ENABLED=true` and
  `PIPELINE_AUTOSTART=true`.

## Configuration

All configuration is read from environment variables. Docker Compose loads them
from `/opt/vt-clickfix-vmray/.env` on the server (or `.env` in the project root
locally). See `.env.example` for every variable with documentation.

| Variable | Default | Secret? | Description |
|----------|---------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://app:app@db:5432/app` | No | Postgres DSN |
| `APP_ENV` | `development` | No | Runtime environment |
| `VT_API_KEY` | `""` | **Yes** | VirusTotal API key (empty = disabled) |
| `VT_POLL_INTERVAL_SECONDS` | `300` | No | VT polling interval |
| `VT_ENABLED` | `false` | No | Enable VT scheduler job |
| `VMRAY_URL` | `""` | **Yes** | VMRay instance base URL (empty = disabled) |
| `VMRAY_API_KEY` | `""` | **Yes** | VMRay API key |
| `VMRAY_POLL_INTERVAL_SECONDS` | `60` | No | VMRay polling interval |
| `VMRAY_ENABLED` | `false` | No | Enable VMRay scheduler jobs |
| `PIPELINE_AUTOSTART` | `false` | No | Start scheduler on app startup |

### Server-side secret file

Secrets live only on the server at `/opt/vt-clickfix-vmray/.env`.
This file is **never committed** (covered by `.gitignore`).
The deploy workflow creates an empty `.env` on first deploy so Docker Compose
never fails; you then populate it manually once.

To enable live integration testing, run this once on the server:

```bash
cat > /opt/vt-clickfix-vmray/.env <<'EOF'
APP_ENV=production
VT_API_KEY=<your-virustotal-api-key>
VT_POLL_INTERVAL_SECONDS=300
VT_ENABLED=true
VMRAY_URL=<your-vmray-instance-url>
VMRAY_API_KEY=<your-vmray-api-key>
VMRAY_POLL_INTERVAL_SECONDS=60
VMRAY_ENABLED=true
PIPELINE_AUTOSTART=true
EOF
chmod 600 /opt/vt-clickfix-vmray/.env
cd /opt/vt-clickfix-vmray && docker compose up -d
```

Replace the `<placeholder>` values with real credentials. After writing the file,
restart the service with `docker compose up -d` (no rebuild needed for env-only
changes).

## Architecture

See [docs/architecture.md](docs/architecture.md).

## CI/CD

| Workflow | Trigger | Action |
|----------|---------|--------|
| CI (`ci.yml`) | push / PR on any branch | Run `pytest` |
| Deploy (`deploy.yml`) | push to `main` | SSH, `git reset --hard origin/main`, `docker compose up -d --build`, health check |

### Required GitHub Actions secrets

| Secret | Value |
|--------|-------|
| `DEPLOY_HOST` | Server public IP (77.42.72.36) |
| `DEPLOY_PORT` | SSH port (22) |
| `DEPLOY_USER` | SSH username (deploy) |
| `DEPLOY_KEY` | Ed25519 private key (PEM) |
| `DEPLOY_HOST_KEY` | Server ed25519 host key (known_hosts line) |
