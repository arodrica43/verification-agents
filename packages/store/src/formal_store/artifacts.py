"""Content-addressed artifact persistence with tenant-scoped upsert."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from formal_domain.artifact import Artifact
from formal_provenance.canonical import content_hash
from formal_schemas.enums import ArtifactLifecycle, Confidentiality, CreatorType
from formal_shared.ids import new_id
from formal_store.models import ArtifactRow


@dataclass(frozen=True)
class ArtifactCreate:
    organization_id: str
    workspace_id: str
    artifact_type: str
    content: dict[str, Any]
    creator_type: CreatorType
    creator_id: str
    project_id: str | None = None
    schema_version: str = "1.0"
    lifecycle_state: ArtifactLifecycle = ArtifactLifecycle.DRAFT
    storage_uri: str | None = None
    supersedes: str | None = None
    metadata: dict[str, Any] | None = None
    confidentiality: Confidentiality = Confidentiality.WORKSPACE
    artifact_id: str | None = None


@dataclass(frozen=True)
class UpsertResult:
    artifact: Artifact
    created: bool


def _row_to_artifact(row: ArtifactRow) -> Artifact:
    return Artifact(
        id=row.id,
        organization_id=row.organization_id,
        workspace_id=row.workspace_id,
        project_id=row.project_id,
        artifact_type=row.artifact_type,
        schema_version=row.schema_version,
        lifecycle_state=ArtifactLifecycle(row.lifecycle_state),
        content_hash=row.content_hash,
        canonical_content_reference=row.content_hash,
        storage_uri=row.storage_uri,
        creator_type=CreatorType(row.creator_type),
        creator_id=row.creator_id,
        created_at=row.created_at,
        supersedes=row.supersedes,
        metadata=dict(row.metadata_json or {}),
        confidentiality=Confidentiality(row.confidentiality),
    )


class ArtifactStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(self, spec: ArtifactCreate) -> UpsertResult:
        """Insert artifact or return existing row with the same tenant+content_hash."""
        digest = content_hash(spec.content)
        existing = await self.get_by_hash(
            organization_id=spec.organization_id,
            workspace_id=spec.workspace_id,
            content_hash_value=digest,
        )
        if existing is not None:
            return UpsertResult(artifact=existing, created=False)

        row = ArtifactRow(
            id=spec.artifact_id or new_id(),
            organization_id=spec.organization_id,
            workspace_id=spec.workspace_id,
            project_id=spec.project_id,
            artifact_type=spec.artifact_type,
            schema_version=spec.schema_version,
            lifecycle_state=str(spec.lifecycle_state),
            content_hash=digest,
            canonical_content=spec.content,
            storage_uri=spec.storage_uri,
            creator_type=str(spec.creator_type),
            creator_id=spec.creator_id,
            created_at=datetime.now(UTC),
            supersedes=spec.supersedes,
            metadata_json=spec.metadata or {},
            confidentiality=str(spec.confidentiality),
        )
        try:
            async with self._session.begin_nested():
                self._session.add(row)
                await self._session.flush()
        except IntegrityError:
            existing = await self.get_by_hash(
                organization_id=spec.organization_id,
                workspace_id=spec.workspace_id,
                content_hash_value=digest,
            )
            if existing is None:
                raise
            return UpsertResult(artifact=existing, created=False)
        return UpsertResult(artifact=_row_to_artifact(row), created=True)

    async def get(self, artifact_id: str) -> Artifact | None:
        row = await self._session.get(ArtifactRow, artifact_id)
        return _row_to_artifact(row) if row else None

    async def get_by_hash(
        self,
        *,
        organization_id: str,
        workspace_id: str,
        content_hash_value: str,
    ) -> Artifact | None:
        stmt = select(ArtifactRow).where(
            ArtifactRow.organization_id == organization_id,
            ArtifactRow.workspace_id == workspace_id,
            ArtifactRow.content_hash == content_hash_value,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return _row_to_artifact(row) if row else None

    async def get_content(
        self,
        *,
        organization_id: str,
        workspace_id: str,
        content_hash_value: str,
    ) -> dict[str, Any] | None:
        stmt = select(ArtifactRow).where(
            ArtifactRow.organization_id == organization_id,
            ArtifactRow.workspace_id == workspace_id,
            ArtifactRow.content_hash == content_hash_value,
        )
        row = (await self._session.execute(stmt)).scalar_one_or_none()
        return dict(row.canonical_content) if row else None

    async def list_workspace(
        self,
        *,
        organization_id: str,
        workspace_id: str,
        artifact_type: str | None = None,
        limit: int = 100,
    ) -> list[Artifact]:
        stmt = (
            select(ArtifactRow)
            .where(
                ArtifactRow.organization_id == organization_id,
                ArtifactRow.workspace_id == workspace_id,
            )
            .order_by(ArtifactRow.created_at.desc())
            .limit(limit)
        )
        if artifact_type:
            stmt = stmt.where(ArtifactRow.artifact_type == artifact_type)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_row_to_artifact(r) for r in rows]
