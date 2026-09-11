"""Production configuration and authz regression tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from formal_api.settings import Settings, get_settings


def test_production_settings_reject_dev_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("PLATFORM_ENV", "production")
    monkeypatch.setenv("API_KEYS", "")
    monkeypatch.setenv("CERTIFICATE_SIGNING_SECRET", "dev_signing_secret_change_me_before_prod")
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://formal:formal_dev_change_me@db/x")
    monkeypatch.setenv("AUTO_CREATE_TABLES", "true")
    monkeypatch.setenv("ALLOW_UNVERIFIED_ISSUANCE", "true")
    monkeypatch.setenv("REQUIRE_LEAN_FOR_ISSUANCE", "false")
    monkeypatch.setenv("OPENAPI_ENABLED", "true")
    with pytest.raises(ValidationError):
        Settings()
    get_settings.cache_clear()


def test_production_settings_accept_hardened_config(monkeypatch: pytest.MonkeyPatch) -> None:
    get_settings.cache_clear()
    monkeypatch.setenv("PLATFORM_ENV", "production")
    monkeypatch.setenv("API_KEYS", "super-secret-api-key-value")
    monkeypatch.setenv(
        "CERTIFICATE_SIGNING_SECRET", "production-signing-secret-at-least-32b"
    )
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql+psycopg://formal:StrongPassw0rd!@db:5432/formal"
    )
    monkeypatch.setenv("AUTO_CREATE_TABLES", "false")
    monkeypatch.setenv("ALLOW_UNVERIFIED_ISSUANCE", "false")
    monkeypatch.setenv("REQUIRE_LEAN_FOR_ISSUANCE", "true")
    monkeypatch.setenv("S3_ENDPOINT_URL", "https://s3.example.com")
    monkeypatch.setenv("DEFAULT_PRINCIPAL_ID", "svc-bootstrap")
    monkeypatch.setenv("API_CORS_ORIGINS", "https://studio.example.com")
    monkeypatch.setenv("OPENAPI_ENABLED", "false")
    monkeypatch.setenv("PROOF_ALLOWED_ROOTS", "/lean")
    cfg = Settings()
    assert cfg.is_production is True
    assert "super-secret-api-key-value" in cfg.api_key_set
    get_settings.cache_clear()
