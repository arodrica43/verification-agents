# Local setup

## Prerequisites

- Docker Desktop (or compatible engine) with Compose v2
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Optional: [elan](https://github.com/leanprover/elan) for host-side Lean builds

## Bootstrap

```bash
cp .env.example .env
uv sync --all-extras
docker compose up -d --build
```

Services (default):

| Service | URL / port |
|---------|------------|
| API | http://localhost:8000 |
| Proof service | http://localhost:8001 |
| Certificate service | http://localhost:8002 |
| Web (when added) | http://localhost:3000 |
| PostgreSQL | localhost:5432 |
| MinIO API | localhost:9000 |
| MinIO Console | localhost:9001 |
| Redis | localhost:6379 |

## Tests

```bash
uv run pytest -q
uv run ruff check .
```

Lean-backed tests:

```bash
uv run pytest -m lean
```

Rebuild the demo certificate (fails closed unless lake succeeds):

```bash
uv run python scripts/build_demo_certificate.py
```

Offline scaffolding only:

```bash
uv run python scripts/build_demo_certificate.py --allow-unverified
```

## Database migrations

```bash
# Prefer Alembic in shared/staging environments:
cd apps/api
alembic upgrade head

# Local compose may set AUTO_CREATE_TABLES=true for bootstrap without running Alembic.
```

## Artifact API (Phase 2)

```bash
curl -s http://localhost:8000/api/v1/meta | jq
# POST /api/v1/artifacts  — content-addressed upsert
# POST /api/v1/provenance/edges
# GET  /api/v1/workspaces/{org}/{ws}/audit
```

## Troubleshooting

- If proof-service cannot find `lake`, ensure the proof container image built successfully.
- Reset local data: `docker compose down -v` (destructive).
