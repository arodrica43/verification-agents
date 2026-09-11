"""Persisted provenance DAG edges."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from formal_provenance.graph import ProvenanceEdge, ProvenanceGraph
from formal_schemas.enums import ProvenanceRelation
from formal_shared.errors import ErrorCode, FormalPlatformError
from formal_shared.ids import new_id
from formal_store.models import ProvenanceEdgeRow


@dataclass(frozen=True)
class ProvenanceEdgeCreate:
    organization_id: str
    workspace_id: str
    source_hash: str
    target_hash: str
    relation: ProvenanceRelation
    metadata: dict[str, Any] | None = None


class ProvenanceStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_edge(self, spec: ProvenanceEdgeCreate) -> tuple[ProvenanceEdge, bool]:
        """Insert an edge; return (edge, created). Rejects cycles within the workspace DAG."""
        existing = await self._find(spec)
        if existing is not None:
            return (
                ProvenanceEdge(
                    source_hash=existing.source_hash,
                    target_hash=existing.target_hash,
                    relation=ProvenanceRelation(existing.relation),
                ),
                False,
            )

        graph = await self.load_graph(
            organization_id=spec.organization_id,
            workspace_id=spec.workspace_id,
        )
        try:
            graph.add_edge(
                ProvenanceEdge(
                    source_hash=spec.source_hash,
                    target_hash=spec.target_hash,
                    relation=spec.relation,
                )
            )
        except FormalPlatformError:
            raise
        except Exception as exc:  # pragma: no cover - defensive
            raise FormalPlatformError(
                ErrorCode.CONFLICT,
                "Failed to add provenance edge",
                details={"error": str(exc)},
            ) from exc

        row = ProvenanceEdgeRow(
            id=new_id(),
            organization_id=spec.organization_id,
            workspace_id=spec.workspace_id,
            source_hash=spec.source_hash,
            target_hash=spec.target_hash,
            relation=str(spec.relation),
            created_at=datetime.now(UTC),
            metadata_json=spec.metadata or {},
        )
        self._session.add(row)
        await self._session.flush()
        return (
            ProvenanceEdge(
                source_hash=row.source_hash,
                target_hash=row.target_hash,
                relation=ProvenanceRelation(row.relation),
            ),
            True,
        )

    async def load_graph(
        self,
        *,
        organization_id: str,
        workspace_id: str,
    ) -> ProvenanceGraph:
        stmt = select(ProvenanceEdgeRow).where(
            ProvenanceEdgeRow.organization_id == organization_id,
            ProvenanceEdgeRow.workspace_id == workspace_id,
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        graph = ProvenanceGraph()
        for row in rows:
            graph.add_node(row.source_hash)
            graph.add_node(row.target_hash)
            graph.edges.append(
                ProvenanceEdge(
                    source_hash=row.source_hash,
                    target_hash=row.target_hash,
                    relation=ProvenanceRelation(row.relation),
                )
            )
        return graph

    async def list_edges(
        self,
        *,
        organization_id: str,
        workspace_id: str,
        content_hash_value: str | None = None,
    ) -> list[ProvenanceEdge]:
        stmt = select(ProvenanceEdgeRow).where(
            ProvenanceEdgeRow.organization_id == organization_id,
            ProvenanceEdgeRow.workspace_id == workspace_id,
        )
        if content_hash_value:
            stmt = stmt.where(
                (ProvenanceEdgeRow.source_hash == content_hash_value)
                | (ProvenanceEdgeRow.target_hash == content_hash_value)
            )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            ProvenanceEdge(
                source_hash=r.source_hash,
                target_hash=r.target_hash,
                relation=ProvenanceRelation(r.relation),
            )
            for r in rows
        ]

    async def _find(self, spec: ProvenanceEdgeCreate) -> ProvenanceEdgeRow | None:
        stmt = select(ProvenanceEdgeRow).where(
            ProvenanceEdgeRow.organization_id == spec.organization_id,
            ProvenanceEdgeRow.workspace_id == spec.workspace_id,
            ProvenanceEdgeRow.source_hash == spec.source_hash,
            ProvenanceEdgeRow.target_hash == spec.target_hash,
            ProvenanceEdgeRow.relation == str(spec.relation),
        )
        return (await self._session.execute(stmt)).scalar_one_or_none()
