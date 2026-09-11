"""Append-only audit event store."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from formal_shared.errors import ErrorCode, FormalPlatformError
from formal_shared.ids import new_id
from formal_store.models import AuditEventRow


@dataclass(frozen=True)
class AuditEventCreate:
    organization_id: str
    actor_type: str
    actor_id: str
    action: str
    resource_type: str
    workspace_id: str | None = None
    resource_id: str | None = None
    content_hash: str | None = None
    payload: dict[str, Any] | None = None
    event_id: str | None = None


@dataclass(frozen=True)
class AuditEvent:
    seq: int
    event_id: str
    organization_id: str
    workspace_id: str | None
    actor_type: str
    actor_id: str
    action: str
    resource_type: str
    resource_id: str | None
    content_hash: str | None
    payload: dict[str, Any]
    created_at: datetime


def _row_to_event(row: AuditEventRow) -> AuditEvent:
    return AuditEvent(
        seq=row.seq,
        event_id=row.event_id,
        organization_id=row.organization_id,
        workspace_id=row.workspace_id,
        actor_type=row.actor_type,
        actor_id=row.actor_id,
        action=row.action,
        resource_type=row.resource_type,
        resource_id=row.resource_id,
        content_hash=row.content_hash,
        payload=dict(row.payload or {}),
        created_at=row.created_at,
    )


class AuditStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(self, spec: AuditEventCreate) -> AuditEvent:
        row = AuditEventRow(
            event_id=spec.event_id or new_id(),
            organization_id=spec.organization_id,
            workspace_id=spec.workspace_id,
            actor_type=spec.actor_type,
            actor_id=spec.actor_id,
            action=spec.action,
            resource_type=spec.resource_type,
            resource_id=spec.resource_id,
            content_hash=spec.content_hash,
            payload=spec.payload or {},
            created_at=datetime.now(UTC),
        )
        self._session.add(row)
        await self._session.flush()
        return _row_to_event(row)

    async def list_events(
        self,
        *,
        organization_id: str,
        workspace_id: str | None = None,
        after_seq: int = 0,
        limit: int = 100,
    ) -> list[AuditEvent]:
        stmt = (
            select(AuditEventRow)
            .where(
                AuditEventRow.organization_id == organization_id,
                AuditEventRow.seq > after_seq,
            )
            .order_by(AuditEventRow.seq.asc())
            .limit(limit)
        )
        if workspace_id is not None:
            stmt = stmt.where(AuditEventRow.workspace_id == workspace_id)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_row_to_event(r) for r in rows]

    async def update_forbidden(self, event_id: str) -> None:
        """Guardrail: audit rows are immutable."""
        raise FormalPlatformError(
            ErrorCode.SECURITY_POLICY_DENIED,
            "Audit events are append-only and cannot be updated",
            details={"event_id": event_id},
        )
