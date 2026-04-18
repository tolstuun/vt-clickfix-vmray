# CLAUDE.md

## Project
VT ClickFix → VMRay pipeline with dashboards.

## Goal
Build a service that:
1. polls VirusTotal latest comments via API,
2. finds comments containing clickfix-related content,
3. extracts defanged URLs such as hxxp/hxxps,
4. normalizes and deduplicates URLs,
5. submits URLs to VMRay,
6. polls VMRay results,
7. stores raw and normalized results,
8. shows dashboards and per-URL details.

## Engineering rules
- Test-driven development.
- One small iteration at a time.
- Do not break existing behavior.
- Keep architecture simple and boring.
- Prefer Python, FastAPI, Postgres, Docker Compose.
- Every implementation change must include:
  - tests,
  - documentation updates,
  - architecture diagram or scheme update when applicable.
- No manual GitHub UI steps when avoidable.
- Use GitHub CLI where possible.
- After finishing a task:
  1. run tests,
  2. commit,
  3. push branch,
  4. create PR,
  5. enable auto-merge when checks pass.
- Never merge with failing tests.
- Never leave completed work without a PR.

## Initial target architecture
- app/api
- app/services
- app/db
- app/models
- app/schemas
- app/workers
- tests
- docs

## Initial delivery priority
1. repository bootstrap
2. CI
3. Docker Compose
4. Postgres integration
5. VT comment polling
6. URL extraction/normalization
7. VMRay submission/polling
8. dashboard API/UI

## Constraints
- Use VT API comments endpoint, not GUI scraping.
- Store raw API responses for traceability.
- Deduplicate normalized URLs.
- Make configuration environment-based.
- Healthcheck endpoint required.
