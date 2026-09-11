"""Lean backend unit tests (forbidden construct scanning does not need lake)."""

from __future__ import annotations

from pathlib import Path

import pytest

from formal_proof_service.backend import ProofCheckRequest
from formal_proof_service.lean_backend import LeanLakeBackend


@pytest.mark.asyncio
async def test_forbidden_sorry_detected(tmp_path: Path) -> None:
    (tmp_path / "lakefile.toml").write_text('name = "Bad"\n', encoding="utf-8")
    (tmp_path / "Bad.lean").write_text(
        "theorem t : True := by\n  sorry\n",
        encoding="utf-8",
    )
    backend = LeanLakeBackend()
    result = await backend.check(ProofCheckRequest(project_path=str(tmp_path)))
    assert result.success is False
    assert result.contains_forbidden is True
    assert any("sorry" in m for m in result.forbidden_matches)
    assert result.environment.get("isolated_workdir") is False


def test_scan_forbidden_ignores_sorry_in_comments(tmp_path: Path) -> None:
    (tmp_path / "Ok.lean").write_text(
        "/-!\nNo `sorry` / `admit`.\n-/\n"
        "-- also mention sorry and admit here\n"
        "theorem t : True := by\n  trivial\n",
        encoding="utf-8",
    )
    backend = LeanLakeBackend()
    matches = backend._scan_forbidden(tmp_path, ["sorry", "admit", "native_decide"])
    assert matches == []


@pytest.mark.asyncio
async def test_inspect_lists_lean_files() -> None:
    root = Path(__file__).resolve().parents[1]
    project = root / "lean" / "examples" / "agent-policy"
    backend = LeanLakeBackend()
    info = await backend.inspect(str(project))
    assert "AgentPolicy.lean" in info["lean_files"]
    assert info["toolchain"]


@pytest.mark.lean
@pytest.mark.asyncio
async def test_lake_build_agent_policy() -> None:
    root = Path(__file__).resolve().parents[1]
    project = root / "lean" / "examples" / "agent-policy"
    backend = LeanLakeBackend()
    result = await backend.check(ProofCheckRequest(project_path=str(project)))
    if result.stderr and "not found" in result.stderr.lower():
        pytest.skip("lake not available")
    assert result.success is True
    assert result.contains_forbidden is False
    assert result.environment.get("isolated_workdir") is True
