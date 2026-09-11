"""Formal Platform HTTP API — production-hardened surface."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import text

from formal_api.auth import PrincipalDep
from formal_api.logging_config import configure_logging
from formal_api.routes.agents import router as agents_router
from formal_api.routes.artifacts import router as artifacts_router
from formal_api.routes.blobs import router as blobs_router
from formal_api.routes.identity import router as identity_router
from formal_api.settings import Settings, get_settings
from formal_certificate_sdk.bundle import verify_bundle
from formal_certificate_service.issuer import issue_demo_certificate
from formal_shared.errors import FormalPlatformError
from formal_store.db import create_engine, create_session_factory


def _create_app(settings: Settings) -> FastAPI:
    configure_logging(settings.log_level)
    docs_url = "/docs" if settings.openapi_enabled else None
    redoc_url = "/redoc" if settings.openapi_enabled else None
    openapi_url = "/openapi.json" if settings.openapi_enabled else None

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = create_engine(settings.database_url, pool_pre_ping=True)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        if settings.auto_create_tables and not settings.is_production:
            from formal_store.db import init_db

            await init_db(engine)
        yield
        await engine.dispose()

    application = FastAPI(
        title="Formal Platform API",
        version="1.0.0",
        description="AI-assisted formal reasoning platform API.",
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
    )
    origins = settings.cors_origin_list
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins or ["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Principal-Id", "Accept"],
    )
    application.include_router(artifacts_router)
    application.include_router(identity_router)
    application.include_router(blobs_router)
    application.include_router(agents_router)
    return application


settings = get_settings()
app = _create_app(settings)


class IssueDemoBody(BaseModel):
    require_lean: bool | None = None
    allow_unverified: bool | None = None
    timeout_seconds: int = Field(default=600, ge=1, le=3600)


class VerifyBundleBody(BaseModel):
    bundle_path: str
    run_lean: bool = False


class ProofCheckProxyBody(BaseModel):
    project_path: str
    toolchain: str | None = None
    timeout_seconds: int = Field(default=300, ge=1, le=3600)


def _proof_service_url() -> str:
    return get_settings().proof_service_url.rstrip("/")


def _assert_proof_path_allowed(project_path: str, cfg: Settings) -> None:
    roots = cfg.proof_allowed_root_list
    if not roots:
        if cfg.is_production:
            raise HTTPException(
                status_code=403,
                detail={"code": "security_policy_denied", "message": "PROOF_ALLOWED_ROOTS unset"},
            )
        return
    resolved = Path(project_path).resolve()
    for root in roots:
        try:
            resolved.relative_to(Path(root).resolve())
            return
        except ValueError:
            continue
    raise HTTPException(
        status_code=403,
        detail={
            "code": "security_policy_denied",
            "message": "project_path outside allowed roots",
            "project_path": str(resolved),
        },
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.get("/ready")
async def ready() -> dict[str, Any]:
    """Readiness: database connectivity required."""
    engine = getattr(app.state, "engine", None)
    if engine is None:
        raise HTTPException(status_code=503, detail={"status": "not_ready", "db": "missing"})
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail={"status": "not_ready", "db": "unavailable", "error": str(exc)},
        ) from exc
    return {"status": "ready", "service": "api", "db": "ok"}


@app.get("/api/v1/meta")
async def meta() -> dict[str, Any]:
    cfg = get_settings()
    return {
        "api_version": "v1",
        "certificate_schema_version": "1.0",
        "problem_spec_schema_version": "1.0",
        "phase": "production",
        "platform_env": cfg.platform_env,
        "proof_service_url": _proof_service_url(),
        "features": {
            "artifacts": True,
            "provenance": True,
            "audit": True,
            "certificates": True,
            "identity": True,
            "blobs": True,
            "retrieval": True,
            "agents": True,
            "ed25519": bool(cfg.certificate_ed25519_private_key_hex),
            "require_lean_for_issuance": cfg.require_lean_for_issuance,
        },
    }


@app.post("/api/v1/certificates/demo/issue")
async def issue_demo_cert(
    body: IssueDemoBody,
    principal: PrincipalDep,
) -> dict:
    """Issue the agent-policy demo certificate (auth required; Lean-gated in production)."""
    cfg = get_settings()
    require_lean = (
        cfg.require_lean_for_issuance
        if body.require_lean is None
        else body.require_lean
    )
    allow_unverified = (
        cfg.allow_unverified_issuance
        if body.allow_unverified is None
        else body.allow_unverified
    )
    if cfg.is_production:
        require_lean = True
        allow_unverified = False
    if require_lean is False and allow_unverified is False:
        allow_unverified = True

    ed_priv = (
        bytes.fromhex(cfg.certificate_ed25519_private_key_hex)
        if cfg.certificate_ed25519_private_key_hex
        else None
    )
    try:
        with tempfile.TemporaryDirectory(prefix="formal-api-cert-") as tmp:
            bundle = issue_demo_certificate(
                Path(tmp) / "certificate-demo",
                signing_secret=cfg.certificate_signing_secret,
                require_lean=require_lean,
                allow_unverified=allow_unverified,
                timeout_seconds=body.timeout_seconds,
                ed25519_private_key=ed_priv,
                signing_key_id=cfg.certificate_signing_key_id,
            )
            certificate = json.loads((bundle / "certificate.json").read_text(encoding="utf-8"))
            verification = json.loads(
                (bundle / "verification" / "verification.json").read_text(encoding="utf-8")
            )
            return {
                "certificate_id": certificate.get("certificate_id"),
                "root_hash": certificate.get("root_hash"),
                "lean_verified": bool(verification.get("success")),
                "issued_by": principal.principal_id,
                "certificate": certificate,
                "verification": verification,
            }
    except FormalPlatformError as exc:
        raise HTTPException(status_code=400, detail=exc.to_dict()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@app.post("/api/v1/certificates/verify")
async def verify_cert_bundle(body: VerifyBundleBody, principal: PrincipalDep) -> dict:
    cfg = get_settings()
    ed_pub = (
        bytes.fromhex(cfg.certificate_ed25519_public_key_hex)
        if cfg.certificate_ed25519_public_key_hex
        else None
    )
    try:
        return verify_bundle(
            Path(body.bundle_path),
            signing_secret=cfg.certificate_signing_secret,
            ed25519_public_key=ed_pub,
            run_lean=body.run_lean or cfg.is_production,
        )
    except FormalPlatformError as exc:
        raise HTTPException(status_code=400, detail=exc.to_dict()) from exc


@app.post("/api/v1/proofs/check")
async def proxy_proof_check(body: ProofCheckProxyBody, principal: PrincipalDep) -> dict:
    """Proxy independent Lean checks to the proof-service (auth + path allowlist)."""
    cfg = get_settings()
    _assert_proof_path_allowed(body.project_path, cfg)
    url = f"{_proof_service_url()}/proofs/check"
    try:
        async with httpx.AsyncClient(timeout=body.timeout_seconds + 30) as client:
            response = await client.post(url, json=body.model_dump())
    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "proof_service_unreachable",
                "message": str(exc),
                "proof_service_url": _proof_service_url(),
            },
        ) from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.json())
    return response.json()


def main() -> None:
    import uvicorn

    cfg = get_settings()
    uvicorn.run(
        "formal_api.main:app",
        host=os.environ.get("API_HOST", cfg.api_host),
        port=int(os.environ.get("API_PORT", str(cfg.api_port))),
        reload=False,
    )


if __name__ == "__main__":
    main()
