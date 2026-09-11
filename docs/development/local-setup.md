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

## Verify demo certificate

```bash
uv run formal-cert verify examples/agent-policy-certificate/certificate-demo
```

## Troubleshooting

- If proof-service cannot find `lake`, ensure the proof container image built successfully.
- Reset local data: `docker compose down -v` (destructive).
