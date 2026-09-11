"""High-level artifact platform operations composing stores."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from formal_domain.artifact import Artifact
from formal_provenance.graph import ProvenanceEdge
from formal_schemas.enums import CreatorType, ProvenanceRelation
from formal_store.artifacts import ArtifactCreate, ArtifactStore, UpsertResult
from formal_store.audit import AuditEvent, AuditEventCreate, AuditStore
from formal_store.provenance import ProvenanceEdgeCreate, ProvenanceStore


class ArtifactPlatform:
    """Transactional facade for artifact upsert, provenance edges, and audit."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.artifacts = ArtifactStore(session)
        self.provenance = ProvenanceStore(session)
        self.audit = AuditStore(session)

    async def put_artifact(
        self,
        spec: ArtifactCreate,
        *,
        actor_type: str | None = None,
        actor_id: str | None = None,
    ) -> UpsertResult:
        result = await self.artifacts.upsert(spec)
        if result.created:
            await self.audit.append(
                AuditEventCreate(
                    organization_id=spec.organization_id,
                    workspace_id=spec.workspace_id,
                    actor_type=actor_type or str(spec.creator_type),
                    actor_id=actor_id or spec.creator_id,
                    action="artifact.created",
                    resource_type="artifact",
                    resource_id=result.artifact.id,
                    content_hash=result.artifact.content_hash,
                    payload={
                        "artifact_type": spec.artifact_type,
                        "lifecycle_state": str(spec.lifecycle_state),
                    },
                )
            )
        else:
            await self.audit.append(
                AuditEventCreate(
                    organization_id=spec.organization_id,
                    workspace_id=spec.workspace_id,
                    actor_type=actor_type or str(spec.creator_type),
                    actor_id=actor_id or spec.creator_id,
                    action="artifact.upsert_hit",
                    resource_type="artifact",
                    resource_id=result.artifact.id,
                    content_hash=result.artifact.content_hash,
                    payload={"artifact_type": spec.artifact_type},
                )
            )
        return result

    async def link(
        self,
        *,
        organization_id: str,
        workspace_id: str,
        source_hash: str,
        target_hash: str,
        relation: ProvenanceRelation,
        actor_type: str = "service",
        actor_id: str = "artifact-platform",
        metadata: dict[str, Any] | None = None,
    ) -> tuple[ProvenanceEdge, bool]:
        edge, created = await self.provenance.add_edge(
            ProvenanceEdgeCreate(
                organization_id=organization_id,
                workspace_id=workspace_id,
                source_hash=source_hash,
                target_hash=target_hash,
                relation=relation,
                metadata=metadata,
            )
        )
        await self.audit.append(
            AuditEventCreate(
                organization_id=organization_id,
                workspace_id=workspace_id,
                actor_type=actor_type,
                actor_id=actor_id,
                action="provenance.edge_added" if created else "provenance.edge_exists",
                resource_type="provenance_edge",
                content_hash=source_hash,
                payload=edge.as_dict(),
            )
        )
        return edge, created

    async def get_artifact(self, artifact_id: str) -> Artifact | None:
        return await self.artifacts.get(artifact_id)

    async def list_audit(
        self,
        *,
        organization_id: str,
        workspace_id: str | None = None,
        after_seq: int = 0,
        limit: int = 100,
    ) -> list[AuditEvent]:
        return await self.audit.list_events(
            organization_id=organization_id,
            workspace_id=workspace_id,
            after_seq=after_seq,
            limit=limit,
        )


def demo_creator() -> tuple[CreatorType, str]:
    return CreatorType.SERVICE, "phase2-bootstrap"
