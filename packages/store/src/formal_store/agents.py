"""Persist agent graph run checkpoints in the platform store."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from formal_shared.ids import new_id
from formal_store.models import AgentRunRow


class AgentRunStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert_state(
        self,
        *,
        run_id: str,
        organization_id: str,
        workspace_id: str,
        project_id: str,
        graph: str,
        status: str,
        state: dict[str, Any],
        pending_human_review: bool,
    ) -> None:
        row = await self._session.get(AgentRunRow, run_id)
        now = datetime.now(UTC)
        if row is None:
            self._session.add(
                AgentRunRow(
                    id=run_id,
                    organization_id=organization_id,
                    workspace_id=workspace_id,
                    project_id=project_id,
                    graph=graph,
                    status=status,
                    state_json=state,
                    pending_human_review=pending_human_review,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            row.graph = graph
            row.status = status
            row.state_json = state
            row.pending_human_review = pending_human_review
            row.updated_at = now
        await self._session.flush()

    async def get_state(self, run_id: str) -> dict[str, Any] | None:
        row = await self._session.get(AgentRunRow, run_id)
        if row is None:
            return None
        return dict(row.state_json)

    async def list_for_project(
        self, *, organization_id: str, project_id: str
    ) -> list[dict[str, Any]]:
        stmt = (
            select(AgentRunRow)
            .where(
                AgentRunRow.organization_id == organization_id,
                AgentRunRow.project_id == project_id,
            )
            .order_by(AgentRunRow.updated_at.desc())
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            {
                "run_id": r.id,
                "graph": r.graph,
                "status": r.status,
                "pending_human_review": r.pending_human_review,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]


def new_run_id() -> str:
    return new_id()
