"""Tests for blobs, identity, evidence, modelling, signing, retrieval."""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from formal_certificate_sdk.signing import (
    ed25519_generate_keypair,
    ed25519_sign,
    ed25519_verify,
    hmac_sign,
    hmac_verify,
)
from formal_domain.organization import Role
from formal_retrieval.store import InMemoryRetrievalIndex, RetrievalDocument
from formal_shared.evidence import (
    AssumptionCheck,
    EvidenceItem,
    EvidenceVerdict,
    validate_evidence_against_assumptions,
)
from formal_shared.modelling import claim_to_lean_skeleton, extract_problem_model
from formal_store.blobs import LocalFilesystemBlobStore
from formal_store.db import init_db
from formal_store.identity import (
    IdentityStore,
    MembershipCreate,
    OrganizationCreate,
    ProjectCreate,
    WorkspaceCreate,
)


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
async def test_local_blob_store_roundtrip(tmp_path: Path) -> None:
    store = LocalFilesystemBlobStore(tmp_path / "blobs")
    stored = await store.put(b"hello-formal", content_type="text/plain")
    assert stored.content_hash
    assert await store.exists(stored.content_hash)
    assert await store.get(stored.content_hash) == b"hello-formal"
    again = await store.put(b"hello-formal")
    assert again.content_hash == stored.content_hash


@pytest.mark.asyncio
async def test_identity_authorize(session: AsyncSession) -> None:
    store = IdentityStore(session)
    org = await store.create_organization(OrganizationCreate(name="Acme", slug="acme"))
    await store.add_membership(
        MembershipCreate(
            organization_id=org.id,
            principal_id="alice",
            role=Role.ORG_OWNER,
        )
    )
    ws = await store.create_workspace(
        WorkspaceCreate(organization_id=org.id, name="Main", slug="main")
    )
    project = await store.create_project(
        ProjectCreate(
            organization_id=org.id,
            workspace_id=ws.id,
            name="Demo",
            description="phase3",
        )
    )
    roles = await store.authorize(organization_id=org.id, principal_id="alice")
    assert Role.ORG_OWNER in roles
    assert project.name == "Demo"


def test_evidence_validation_supports() -> None:
    results = validate_evidence_against_assumptions(
        assumptions=[
            AssumptionCheck(
                assumption_id="a1",
                statement="Authorization policy covers privileged actions",
            )
        ],
        evidence=[
            EvidenceItem(
                evidence_id="e1",
                description="Review of authorization policy document",
                content_hash="abc",
                source="human",
                confidence=0.9,
            )
        ],
    )
    assert results[0].verdict == EvidenceVerdict.SUPPORTS


def test_modelling_extract() -> None:
    model = extract_problem_model(
        "The AgentRuntime must ensure privileged actions require Authorization."
    )
    assert model["goals"]
    assert model["needs_human_review"] is True
    lean = claim_to_lean_skeleton("privileged implies authorized", "auth_thm")
    assert "theorem auth_thm" in lean
    assert "sorry" not in lean


def test_ed25519_sign_verify() -> None:
    pytest.importorskip("cryptography")
    priv, pub = ed25519_generate_keypair()
    payload = b"certificate-root"
    sig = ed25519_sign(key_id="k1", private_key=priv, payload=payload)
    assert sig.algorithm == "Ed25519"
    assert ed25519_verify(public_key=pub, payload=payload, signature=sig.signature)
    assert not ed25519_verify(public_key=pub, payload=b"tampered", signature=sig.signature)


def test_hmac_still_works() -> None:
    payload = b"demo"
    block = hmac_sign(key_id="dev", secret="secret", payload=payload)
    assert hmac_verify(secret="secret", payload=payload, signature=block.signature)


def test_retrieval_tenant_prefilter() -> None:
    index = InMemoryRetrievalIndex()
    index.upsert(
        RetrievalDocument(
            organization_id="org-a",
            workspace_id="ws-1",
            document_id="d1",
            content_hash="h1",
            text="capacity demand bound infrastructure",
        )
    )
    index.upsert(
        RetrievalDocument(
            organization_id="org-b",
            workspace_id="ws-1",
            document_id="d2",
            content_hash="h2",
            text="capacity demand bound infrastructure",
        )
    )
    hits = index.search(
        organization_id="org-a",
        workspace_id="ws-1",
        query="capacity bound",
    )
    assert len(hits) == 1
    assert hits[0].document_id == "d1"
