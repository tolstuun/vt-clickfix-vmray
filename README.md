# vt-clickfix-vmray

A service that polls VirusTotal for ClickFix-related comments, extracts and normalizes defanged URLs, submits them to VMRay, and presents results via dashboards.

## Requirements

- Python 3.12+
- Docker and Docker Compose

## Setup

```bash
# Clone the repo
git clone https://github.com/tolstuun/vt-clickfix-vmray.git
cd vt-clickfix-vmray

# Install dependencies (for local development)
make install
```

## Run locally (Docker Compose)

```bash
# Start app + Postgres
make up

# View logs
make logs

# Stop
make down
```

The API will be available at http://localhost:8000.

## Run locally (without Docker)

```bash
# Copy and adjust environment variables if needed
cp .env.example .env  # (not required for defaults)

make run
```

## Test

```bash
make test
```

## Health check

```
GET /health
→ {"status": "healthy"}
```

## Architecture

See [docs/architecture.md](docs/architecture.md).
