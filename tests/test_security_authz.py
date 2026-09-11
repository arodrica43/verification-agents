"""Security-oriented unit checks (Phase 3 / threat model)."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from formal_domain.organization import Role
from formal_shared.errors import FormalPlatformError
from formal_store.db import init_db
from formal_store.identity import IdentityStore, MembershipCreate, OrganizationCreate


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    await init_db(engine)
    factory = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    async with factory() as session:
        yield session
        await session.commit()
    await engine.dispose()


@pytest.mark.security
@pytest.mark.asyncio
async def test_cross_tenant_authorization_denied(session: AsyncSession) -> None:
    store = IdentityStore(session)
    org_a = await store.create_organization(OrganizationCreate(name="A", slug="org-a"))
    org_b = await store.create_organization(OrganizationCreate(name="B", slug="org-b"))
    await store.add_membership(
        MembershipCreate(
            organization_id=org_a.id,
            principal_id="alice",
            role=Role.RESEARCHER,
        )
    )
    with pytest.raises(FormalPlatformError) as exc:
        await store.authorize(organization_id=org_b.id, principal_id="alice")
    assert exc.value.code.value == "unauthorized"
