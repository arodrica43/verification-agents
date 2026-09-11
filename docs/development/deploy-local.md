# Local process deploy (no Docker)

Use this when Docker/WSL is unavailable. Starts API + optional web against SQLite.

```powershell
# Terminal 1 — API
$env:PLATFORM_ENV="development"
$env:DATABASE_URL="sqlite+aiosqlite:///.data/local-demo.db"
$env:AUTO_CREATE_TABLES="true"
$env:ALLOW_UNVERIFIED_ISSUANCE="true"
$env:REQUIRE_LEAN_FOR_ISSUANCE="false"
$env:BLOB_ROOT=".data/blobs"
$env:API_CORS_ORIGINS="http://localhost:3000"
$env:PYTHONPATH="packages/shared/src;packages/schemas/src;packages/domain/src;packages/provenance/src;packages/certificate-sdk/src;packages/store/src;services/proof-service/src;services/certificate-service/src;services/retrieval-service/src;apps/api/src"
python -m uvicorn formal_api.main:app --host 127.0.0.1 --port 8000 --app-dir apps/api/src

# Terminal 2 — Studio (optional)
npm run dev:web

# Smoke
python scripts/smoke_system.py
```

Endpoints:

- API docs: http://127.0.0.1:8000/docs
- Health: http://127.0.0.1:8000/health
- Studio: http://localhost:3000

## Docker compose (preferred when WSL2 is available)

1. Install WSL2 + a distro, reboot if prompted.
2. Start Docker Desktop until `docker info` works.
3. Run:

```powershell
.\scripts\deploy_local.ps1
```

This brings up postgres, minio, redis, proof-service (with Lean), certificate-service, retrieval, API, and web.
