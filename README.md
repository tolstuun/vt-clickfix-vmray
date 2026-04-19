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

The API is available at http://localhost:8001.

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
  - Response schema: `SubmissionItem` → `data.submission_finished` (bool),
    `data.submission_verdict` (`"malicious"` | `"suspicious"` | `"clean"` | null),
    `data.submission_score` (int | null)
- Analysis is considered complete when `submission_finished == true`.
- Credentials are optional: the app starts and stays healthy without `VMRAY_URL` /
  `VMRAY_API_KEY`. Submission/polling only runs when `VMRAY_ENABLED=true` and
  `PIPELINE_AUTOSTART=true`.

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://app:app@db:5432/app` | Postgres DSN |
| `VT_API_KEY` | `""` | VirusTotal API key (empty = disabled) |
| `VT_POLL_INTERVAL_SECONDS` | `300` | VT polling interval |
| `VT_ENABLED` | `false` | Enable VT scheduler job |
| `VMRAY_URL` | `""` | VMRay base URL (empty = disabled) |
| `VMRAY_API_KEY` | `""` | VMRay API key |
| `VMRAY_POLL_INTERVAL_SECONDS` | `60` | VMRay polling interval |
| `VMRAY_ENABLED` | `false` | Enable VMRay scheduler jobs |
| `PIPELINE_AUTOSTART` | `false` | Start scheduler on app startup |

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
