"""Persist issued certificates (metadata + blob pointer)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from formal_store.models import CertificateRow


@dataclass(frozen=True)
class CertificateCreate:
    id: str
    organization_id: str
    workspace_id: str
    root_hash: str
    lean_verified: bool
    claim_statement: str
    theorem_name: str
    bundle_content_hash: str
    bundle_uri: str
    certificate_json: dict[str, Any]
    verification_json: dict[str, Any]
    issued_by: str
    project_id: str | None = None
    run_id: str | None = None
    source: str = "agent"
    status: str = "issued"


class CertificateStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, data: CertificateCreate) -> dict[str, Any]:
        now = datetime.now(UTC)
        row = CertificateRow(
            id=data.id,
            organization_id=data.organization_id,
            workspace_id=data.workspace_id,
            project_id=data.project_id,
            run_id=data.run_id,
            root_hash=data.root_hash,
            lean_verified=data.lean_verified,
            status=data.status,
            claim_statement=data.claim_statement,
            theorem_name=data.theorem_name,
            bundle_content_hash=data.bundle_content_hash,
            bundle_uri=data.bundle_uri,
            certificate_json=data.certificate_json,
            verification_json=data.verification_json,
            issued_by=data.issued_by,
            source=data.source,
            created_at=now,
        )
        self._session.add(row)
        await self._session.flush()
        return self._to_dict(row)

    async def get(self, certificate_id: str) -> dict[str, Any] | None:
        row = await self._session.get(CertificateRow, certificate_id)
        return None if row is None else self._to_dict(row)

    async def list_for_organization(
        self, *, organization_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        stmt = (
            select(CertificateRow)
            .where(CertificateRow.organization_id == organization_id)
            .order_by(CertificateRow.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_dict(r) for r in rows]

    async def list_for_project(
        self, *, organization_id: str, project_id: str, limit: int = 100
    ) -> list[dict[str, Any]]:
        stmt = (
            select(CertificateRow)
            .where(
                CertificateRow.organization_id == organization_id,
                CertificateRow.project_id == project_id,
            )
            .order_by(CertificateRow.created_at.desc())
            .limit(limit)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [self._to_dict(r) for r in rows]

    @staticmethod
    def _to_dict(row: CertificateRow) -> dict[str, Any]:
        return {
            "certificate_id": row.id,
            "organization_id": row.organization_id,
            "workspace_id": row.workspace_id,
            "project_id": row.project_id,
            "run_id": row.run_id,
            "root_hash": row.root_hash,
            "lean_verified": row.lean_verified,
            "status": row.status,
            "claim_statement": row.claim_statement,
            "theorem_name": row.theorem_name,
            "bundle_content_hash": row.bundle_content_hash,
            "bundle_uri": row.bundle_uri,
            "certificate": row.certificate_json,
            "verification": row.verification_json,
            "issued_by": row.issued_by,
            "source": row.source,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
