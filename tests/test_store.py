"""Phase 2 store tests (SQLite async)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from formal_schemas.enums import CreatorType, ProvenanceRelation
from formal_shared.errors import FormalPlatformError
from formal_store.artifacts import ArtifactCreate
from formal_store.audit import AuditStore
from formal_store.db import init_db
from formal_store.models import Base
from formal_store.service import ArtifactPlatform


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
        await session.commit()
    await engine.dispose()


@pytest.mark.asyncio
async def test_artifact_content_hash_upsert(session: AsyncSession) -> None:
    platform = ArtifactPlatform(session)
    spec = ArtifactCreate(
        organization_id="org-1",
        workspace_id="ws-1",
        artifact_type="problem_spec",
        content={"title": "demo", "description": "phase2"},
        creator_type=CreatorType.USER,
        creator_id="user-1",
    )
    first = await platform.put_artifact(spec)
    second = await platform.put_artifact(spec)
    assert first.created is True
    assert second.created is False
    assert first.artifact.id == second.artifact.id
    assert first.artifact.content_hash == second.artifact.content_hash
    assert len(first.artifact.content_hash) == 64


@pytest.mark.asyncio
async def test_provenance_cycle_rejected(session: AsyncSession) -> None:
    platform = ArtifactPlatform(session)
    a = await platform.put_artifact(
        ArtifactCreate(
            organization_id="org-1",
            workspace_id="ws-1",
            artifact_type="model",
            content={"n": "a"},
            creator_type=CreatorType.SERVICE,
            creator_id="svc",
        )
    )
    b = await platform.put_artifact(
        ArtifactCreate(
            organization_id="org-1",
            workspace_id="ws-1",
            artifact_type="model",
            content={"n": "b"},
            creator_type=CreatorType.SERVICE,
            creator_id="svc",
        )
    )
    await platform.link(
        organization_id="org-1",
        workspace_id="ws-1",
        source_hash=a.artifact.content_hash,
        target_hash=b.artifact.content_hash,
        relation=ProvenanceRelation.DERIVED_FROM,
    )
    with pytest.raises(FormalPlatformError) as exc:
        await platform.link(
            organization_id="org-1",
            workspace_id="ws-1",
            source_hash=b.artifact.content_hash,
            target_hash=a.artifact.content_hash,
            relation=ProvenanceRelation.DERIVED_FROM,
        )
    assert exc.value.code.value == "conflict"


@pytest.mark.asyncio
async def test_audit_append_only(session: AsyncSession) -> None:
    platform = ArtifactPlatform(session)
    await platform.put_artifact(
        ArtifactCreate(
            organization_id="org-1",
            workspace_id="ws-1",
            artifact_type="evidence",
            content={"bytes": "abc"},
            creator_type=CreatorType.AGENT,
            creator_id="agent-1",
        )
    )
    events = await platform.list_audit(organization_id="org-1", workspace_id="ws-1")
    assert len(events) >= 1
    assert events[0].action == "artifact.created"
    audit = AuditStore(session)
    with pytest.raises(FormalPlatformError):
        await audit.update_forbidden(events[0].event_id)


@pytest.mark.asyncio
async def test_metadata_create_all_registers_tables() -> None:
    assert {"artifacts", "provenance_edges", "audit_events"} <= set(Base.metadata.tables)
