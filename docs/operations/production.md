# Production operations

## First production release bar

This document is the operator checklist for a first production deploy of the Formal Platform.

### Required secrets / env

| Variable | Notes |
|----------|--------|
| `PLATFORM_ENV=production` | Enables fail-closed settings validation |
| `API_KEYS` | Comma-separated Bearer tokens |
| `API_CORS_ORIGINS` | Explicit studio origins (no `*`) |
| `DATABASE_URL` / `POSTGRES_PASSWORD` | Strong credentials; never `formal_dev_change_me` |
| `CERTIFICATE_SIGNING_SECRET` | ≥32 chars, non-default (HMAC fallback) |
| `CERTIFICATE_ED25519_PRIVATE_KEY_HEX` / `PUBLIC` | Preferred production signing |
| `S3_*` | Object store endpoint + credentials |
| `PROOF_ALLOWED_ROOTS` | Absolute Lean project roots only |
| `PROOF_SERVICE_TOKEN` | Shared secret for proof-service |
| `DEFAULT_PRINCIPAL_ID` | Non-dev principal bootstrap |
| `OPENAPI_ENABLED=false` | Disable `/docs` |
| `REQUIRE_LEAN_FOR_ISSUANCE=true` | |
| `ALLOW_UNVERIFIED_ISSUANCE=false` | |
| `AUTO_CREATE_TABLES=false` | Always use Alembic |

Generate an Ed25519 keypair:

```bash
python - <<'PY'
from formal_certificate_sdk.signing import ed25519_generate_keypair
priv, pub = ed25519_generate_keypair()
print("CERTIFICATE_ED25519_PRIVATE_KEY_HEX=" + priv.hex())
print("CERTIFICATE_ED25519_PUBLIC_KEY_HEX=" + pub.hex())
PY
```

### Deploy

```bash
cp .env.example .env
# fill production values
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

API entrypoint runs `alembic upgrade head` then serves traffic. Confirm readiness:

```bash
curl -fsS http://localhost:8000/ready
```

### Database migrations

```bash
cd apps/api
DATABASE_URL=postgresql+psycopg://... alembic upgrade head
alembic current
```

Never enable `AUTO_CREATE_TABLES` in production — it skips RLS policies.

### Backups

1. **PostgreSQL**: nightly `pg_dump` (or managed snapshot) of the primary database; retain PITR if available.
2. **Object store**: enable versioning on the artifacts bucket; replicate to a second region if RPO requires it.
3. **Certificates**: keep issued bundles in S3 with object-lock/WORM when available (platform records hashes + signatures regardless).

Restore drill at least quarterly.

### Lean verification workers

- Proof-service must not publish a public port in production overlays.
- Set `PROOF_ALLOWED_ROOTS` to the mounted Lean trees only.
- Prefer network isolation (no egress) for production proof workers; current image is path-restricted + token-gated, not yet cgroup-isolated.

### Auth model (v1)

- Clients send `Authorization: Bearer <api-key>` and `X-Principal-Id: <user-id>`.
- Memberships gate org/workspace access; Postgres RLS uses `app.organization_id`.
- OIDC/SSO is the next hardening step after this release.

### Rollback

1. Roll API/web images to previous digest.
2. Do **not** downgrade Alembic unless a tested downgrade path exists for that revision.
3. Invalidate compromised API keys and signing material immediately.
