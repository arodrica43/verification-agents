"""Agent run API smoke tests (in-process GraphRunner)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from formal_api.main import app
from formal_api.settings import get_settings
from formal_store.db import create_engine, create_session_factory, init_db


@pytest.fixture
async def client(tmp_path, monkeypatch: pytest.MonkeyPatch):
    db = tmp_path / "agents.db"
    monkeypatch.setenv("PLATFORM_ENV", "development")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{db.as_posix()}")
    monkeypatch.setenv("AUTO_CREATE_TABLES", "true")
    monkeypatch.setenv("ALLOW_UNVERIFIED_ISSUANCE", "true")
    monkeypatch.setenv("REQUIRE_LEAN_FOR_ISSUANCE", "false")
    monkeypatch.setenv("DEFAULT_PRINCIPAL_ID", "test-user")
    get_settings.cache_clear()

    engine = create_engine(f"sqlite+aiosqlite:///{db.as_posix()}")
    await init_db(engine)
    factory = create_session_factory(engine)

    app.state.engine = engine
    app.state.session_factory = factory

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    await engine.dispose()
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_modelling_agent_run(client: AsyncClient) -> None:
    headers = {"X-Principal-Id": "test-user"}
    org = (
        await client.post(
            "/api/v1/organizations",
            json={"name": "Agent Org", "slug": "agent-org"},
            headers=headers,
        )
    ).json()
    ws = org["default_workspace"]
    project = (
        await client.post(
            "/api/v1/projects",
            json={
                "organization_id": org["id"],
                "workspace_id": ws["id"],
                "name": "Policy Project",
                "description": "demo",
            },
            headers=headers,
        )
    ).json()

    run = (
        await client.post(
            "/api/v1/agents/runs",
            json={
                "organization_id": org["id"],
                "workspace_id": ws["id"],
                "project_id": project["id"],
                "graph": "problem_modelling",
                "problem_text": (
                    "AgentRuntime must never execute PrivilegedAction unless "
                    "Authorization holds under Policy. Ensure safety."
                ),
            },
            headers=headers,
        )
    ).json()

    assert run["status"] == "completed"
    assert run["entities"]
    assert run["goals"]
    assert run["assumptions"]

    listed = (
        await client.get(
            f"/api/v1/projects/{project['id']}/agent-runs", headers=headers
        )
    ).json()
    assert listed["items"]
    assert listed["items"][0]["run_id"] == run["run_id"]

    formal = (
        await client.post(
            "/api/v1/agents/runs",
            json={
                "organization_id": org["id"],
                "workspace_id": ws["id"],
                "project_id": project["id"],
                "graph": "formalization",
                "seed_from_run_id": run["run_id"],
            },
            headers=headers,
        )
    ).json()
    assert formal["status"] == "completed"
    assert formal["lean_skeleton"]
