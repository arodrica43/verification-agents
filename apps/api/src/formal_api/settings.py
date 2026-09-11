"""API settings with fail-closed production validation."""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEV_SECRETS = {
    "dev_signing_secret_change_me_before_prod",
    "formal_dev_change_me",
    "minioadmin",
    "dev-user",
    "change_me",
}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    platform_env: str = "development"  # development | staging | production
    database_url: str = (
        "postgresql+psycopg://formal:formal_dev_change_me@localhost:5432/formal_platform"
    )
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_cors_origins: str = "http://localhost:3000"
    api_keys: str = ""  # comma-separated; required in production
    proof_service_url: str = "http://127.0.0.1:8001"
    retrieval_service_url: str = "http://127.0.0.1:8003"
    certificate_signing_secret: str = "dev_signing_secret_change_me_before_prod"
    certificate_signing_key_id: str = "dev-key-1"
    certificate_ed25519_private_key_hex: str | None = None
    certificate_ed25519_public_key_hex: str | None = None
    require_lean_for_issuance: bool = False
    allow_unverified_issuance: bool = True
    auto_create_tables: bool = False
    blob_root: str = ".data/blobs"
    s3_endpoint_url: str | None = None
    s3_bucket: str = "formal-artifacts"
    s3_access_key: str | None = None
    s3_secret_key: str | None = None
    default_principal_id: str = "dev-user"
    openapi_enabled: bool = True
    log_level: str = "INFO"
    proof_allowed_roots: str = ""  # comma-separated absolute paths; empty = allow all (dev)

    @property
    def is_production(self) -> bool:
        return self.platform_env.lower() == "production"

    @property
    def api_key_set(self) -> set[str]:
        return {k.strip() for k in self.api_keys.split(",") if k.strip()}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]

    @property
    def proof_allowed_root_list(self) -> list[str]:
        return [p.strip() for p in self.proof_allowed_roots.split(",") if p.strip()]

    @field_validator("platform_env")
    @classmethod
    def _normalize_env(cls, value: str) -> str:
        v = value.strip().lower()
        if v not in {"development", "staging", "production"}:
            raise ValueError("PLATFORM_ENV must be development|staging|production")
        return v

    @model_validator(mode="after")
    def _production_guards(self) -> Settings:
        if not self.is_production:
            return self
        problems: list[str] = []
        if not self.api_key_set:
            problems.append("API_KEYS must be set in production")
        if self.certificate_signing_secret in _DEV_SECRETS or len(
            self.certificate_signing_secret
        ) < 32:
            problems.append("CERTIFICATE_SIGNING_SECRET must be a strong non-default secret")
        if "formal_dev_change_me" in self.database_url or "change_me" in self.database_url:
            problems.append("DATABASE_URL must not use development credentials")
        if self.auto_create_tables:
            problems.append("AUTO_CREATE_TABLES must be false in production (use Alembic)")
        if self.allow_unverified_issuance:
            problems.append("ALLOW_UNVERIFIED_ISSUANCE must be false in production")
        if not self.require_lean_for_issuance:
            problems.append("REQUIRE_LEAN_FOR_ISSUANCE must be true in production")
        if not self.s3_endpoint_url:
            problems.append("S3_ENDPOINT_URL is required in production")
        if self.default_principal_id in _DEV_SECRETS:
            problems.append("DEFAULT_PRINCIPAL_ID must not be the development default")
        if "*" in self.api_cors_origins:
            problems.append("API_CORS_ORIGINS must not include wildcard in production")
        if self.openapi_enabled:
            problems.append("OPENAPI_ENABLED must be false in production")
        if not self.proof_allowed_root_list:
            problems.append("PROOF_ALLOWED_ROOTS must restrict Lean project paths in production")
        if problems:
            raise ValueError("Production configuration invalid: " + "; ".join(problems))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
