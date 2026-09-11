# Ensure a local .env exists for docker compose / process deploy.
# Does NOT write secrets into git — only creates an untracked .env if missing.

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"
EXAMPLE = ROOT / ".env.example"

DEFAULTS = {
    "POSTGRES_PASSWORD": "local-only-postgres-pass",
    "DATABASE_URL": "postgresql+psycopg://formal:local-only-postgres-pass@localhost:5432/formal_platform",
    "S3_ACCESS_KEY": "local-only-minio-key",
    "S3_SECRET_KEY": "local-only-minio-secret",
    "CERTIFICATE_SIGNING_SECRET": "local-only-signing-secret-32chars-min",
}


def main() -> None:
    if ENV.exists():
        print(f"{ENV} already exists")
        return
    text = EXAMPLE.read_text(encoding="utf-8")
    for key, value in DEFAULTS.items():
        text = text.replace(f"{key}=<SET_ME>", f"{key}={value}")
        text = text.replace("formal:<SET_ME>@", f"formal:{DEFAULTS['POSTGRES_PASSWORD']}@")
    ENV.write_text(text, encoding="utf-8")
    print(f"Wrote {ENV} with local-only placeholders (not for production)")


if __name__ == "__main__":
    main()
