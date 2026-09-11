"""Issue certificate bundles and persist them in the platform store."""

from __future__ import annotations

import io
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from formal_api.routes.blobs import get_blob_store
from formal_api.settings import Settings, get_settings
from formal_certificate_service import (
    issue_demo_certificate,
    issue_lean_project_certificate,
)
from formal_store.audit import AuditEventCreate, AuditStore
from formal_store.certificates import CertificateCreate, CertificateStore


def zip_directory(path: Path) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(path.rglob("*")):
            if file_path.is_file():
                zf.write(file_path, file_path.relative_to(path).as_posix())
    return buf.getvalue()


def _read_bundle_json(bundle: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    certificate = json.loads((bundle / "certificate.json").read_text(encoding="utf-8"))
    verification = json.loads(
        (bundle / "verification" / "verification.json").read_text(encoding="utf-8")
    )
    return certificate, verification


def _claim_and_theorem(certificate: dict[str, Any]) -> tuple[str, str]:
    claim = ""
    theorem = ""
    raw_claim = certificate.get("claim")
    if isinstance(raw_claim, dict):
        claim = str(raw_claim.get("statement") or "")
    raw_th = certificate.get("formal_theorem")
    if isinstance(raw_th, dict):
        theorem = str(raw_th.get("name") or "")
    return claim, theorem


async def _persist_bundle(
    session: AsyncSession,
    *,
    bundle: Path,
    organization_id: str,
    workspace_id: str,
    issued_by: str,
    project_id: str | None = None,
    run_id: str | None = None,
    source: str = "agent",
) -> dict[str, Any]:
    certificate, verification = _read_bundle_json(bundle)
    claim, theorem = _claim_and_theorem(certificate)
    certificate_id = str(certificate.get("certificate_id") or "")
    root_hash = str(certificate.get("root_hash") or "")
    lean_verified = bool(verification.get("success"))

    zipped = zip_directory(bundle)
    blob = await get_blob_store().put(
        zipped,
        content_type="application/zip",
        prefix="certificates",
    )

    record = await CertificateStore(session).create(
        CertificateCreate(
            id=certificate_id,
            organization_id=organization_id,
            workspace_id=workspace_id,
            project_id=project_id,
            run_id=run_id,
            root_hash=root_hash,
            lean_verified=lean_verified,
            claim_statement=claim,
            theorem_name=theorem,
            bundle_content_hash=blob.content_hash,
            bundle_uri=blob.uri,
            certificate_json=certificate,
            verification_json=verification,
            issued_by=issued_by,
            source=source,
        )
    )
    await AuditStore(session).append(
        AuditEventCreate(
            organization_id=organization_id,
            workspace_id=workspace_id,
            actor_type="principal",
            actor_id=issued_by,
            action="certificate.issued",
            resource_type="certificate",
            resource_id=certificate_id,
            content_hash=root_hash,
            payload={
                "lean_verified": lean_verified,
                "source": source,
                "project_id": project_id,
                "run_id": run_id,
                "bundle_content_hash": blob.content_hash,
            },
        )
    )
    return {
        "certificate_id": certificate_id,
        "root_hash": root_hash,
        "lean_verified": lean_verified,
        "issued_by": issued_by,
        "run_id": run_id,
        "project_id": project_id,
        "organization_id": organization_id,
        "workspace_id": workspace_id,
        "source": source,
        "bundle_content_hash": blob.content_hash,
        "bundle_uri": blob.uri,
        "claim_statement": claim,
        "theorem_name": theorem,
        "created_at": record.get("created_at"),
        "certificate": certificate,
        "verification": verification,
        "status": "issued",
    }


async def issue_and_persist_from_lean_project(
    session: AsyncSession,
    *,
    lean_project: Path,
    organization_id: str,
    workspace_id: str,
    issued_by: str,
    title: str,
    description: str,
    entities: list[dict[str, Any]] | None = None,
    goals: list[dict[str, Any]] | None = None,
    claims: list[dict[str, Any]] | None = None,
    assumptions: list[dict[str, Any]] | None = None,
    theorem_name: str | None = None,
    project_id: str | None = None,
    run_id: str | None = None,
    timeout_seconds: int = 600,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    ed_priv = (
        bytes.fromhex(cfg.certificate_ed25519_private_key_hex)
        if cfg.certificate_ed25519_private_key_hex
        else None
    )
    with tempfile.TemporaryDirectory(prefix="formal-agent-cert-") as tmp:
        bundle = issue_lean_project_certificate(
            lean_project,
            Path(tmp) / "certificate-demo",
            title=title,
            description=description,
            entities=entities,
            goals=goals,
            claims=claims,
            assumptions_in=assumptions,
            theorem_name=theorem_name,
            signing_secret=cfg.certificate_signing_secret,
            signing_key_id=cfg.certificate_signing_key_id,
            ed25519_private_key=ed_priv,
            require_lean=True,
            allow_unverified=False,
            timeout_seconds=timeout_seconds,
        )
        return await _persist_bundle(
            session,
            bundle=bundle,
            organization_id=organization_id,
            workspace_id=workspace_id,
            project_id=project_id,
            run_id=run_id,
            issued_by=issued_by,
            source="agent",
        )


async def issue_and_persist_demo(
    session: AsyncSession,
    *,
    organization_id: str,
    workspace_id: str,
    issued_by: str,
    project_id: str | None = None,
    require_lean: bool,
    allow_unverified: bool,
    timeout_seconds: int = 600,
    settings: Settings | None = None,
) -> dict[str, Any]:
    cfg = settings or get_settings()
    ed_priv = (
        bytes.fromhex(cfg.certificate_ed25519_private_key_hex)
        if cfg.certificate_ed25519_private_key_hex
        else None
    )
    with tempfile.TemporaryDirectory(prefix="formal-api-cert-") as tmp:
        bundle = issue_demo_certificate(
            Path(tmp) / "certificate-demo",
            signing_secret=cfg.certificate_signing_secret,
            require_lean=require_lean,
            allow_unverified=allow_unverified,
            timeout_seconds=timeout_seconds,
            ed25519_private_key=ed_priv,
            signing_key_id=cfg.certificate_signing_key_id,
        )
        return await _persist_bundle(
            session,
            bundle=bundle,
            organization_id=organization_id,
            workspace_id=workspace_id,
            project_id=project_id,
            run_id=None,
            issued_by=issued_by,
            source="demo",
        )
