"""Persisted certificate issuance and listing."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from formal_api.main import app
from formal_api.settings import get_settings
from formal_store.db import create_engine, create_session_factory, init_db


@pytest.fixture
async def client(tmp_path, monkeypatch: pytest.MonkeyPatch):
    db = tmp_path / "certs.db"
    monkeypatch.setenv("PLATFORM_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db.as_posix()}")
    monkeypatch.setenv("AUTO_CREATE_TABLES", "true")
    monkeypatch.setenv("ALLOW_UNVERIFIED_ISSUANCE", "true")
    monkeypatch.setenv("REQUIRE_LEAN_FOR_ISSUANCE", "false")
    monkeypatch.setenv("BLOB_ROOT", str(tmp_path / "blobs"))
    monkeypatch.setenv("DEFAULT_PRINCIPAL_ID", "cert-tester")
    get_settings.cache_clear()

    engine = create_engine(f"sqlite+aiosqlite:///{db.as_posix()}")
    await init_db(engine)
    app.state.engine = engine
    app.state.session_factory = create_session_factory(engine)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await engine.dispose()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_demo_certificate_persists_and_lists(client: AsyncClient) -> None:
    headers = {"X-Principal-Id": "cert-tester"}
    org = (
        await client.post(
            "/api/v1/organizations",
            headers=headers,
            json={"name": "Cert Org", "slug": "cert-org"},
        )
    ).json()
    ws = org["default_workspace"]

    issued = (
        await client.post(
            "/api/v1/certificates/demo/issue",
            headers=headers,
            json={
                "organization_id": org["id"],
                "workspace_id": ws["id"],
                "require_lean": False,
                "allow_unverified": True,
            },
            timeout=120.0,
        )
    ).json()
    assert issued.get("certificate_id"), issued
    assert issued.get("root_hash")
    assert issued.get("bundle_content_hash")

    listed = (
        await client.get(
            f"/api/v1/organizations/{org['id']}/certificates",
            headers=headers,
        )
    ).json()
    assert len(listed["items"]) >= 1
    assert listed["items"][0]["certificate_id"] == issued["certificate_id"]

    detail = (
        await client.get(
            f"/api/v1/certificates/{issued['certificate_id']}",
            headers=headers,
        )
    ).json()
    assert detail["certificate_id"] == issued["certificate_id"]

    bundle = await client.get(
        f"/api/v1/certificates/{issued['certificate_id']}/bundle",
        headers=headers,
    )
    assert bundle.status_code == 200
    assert "zip" in bundle.headers.get("content-type", "")
    assert len(bundle.content) > 100
