"""Proof graph — materialize Lean project and run an independent lake check."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from formal_agent_core.graph import TypedGraph
from formal_agent_core.lean_project import (
    AGENT_FORBIDDEN,
    DEFAULT_MODULE,
    find_repo_root,
    materialize_lean_project,
)
from formal_agent_core.state import AgentGraphState, GraphName, NodeResult


def _workdir_root() -> Path:
    env = os.environ.get("FORMAL_LEAN_WORKDIR") or os.environ.get("BLOB_ROOT")
    if env:
        return Path(env) / "lean-runs"
    return Path(".data") / "lean-runs"


async def _run_lean_check(project_path: Path) -> dict[str, Any]:
    """Invoke LeanLakeBackend when available; never self-attest success."""
    try:
        from formal_proof_service.backend import ProofCheckRequest
        from formal_proof_service.lean_backend import LeanLakeBackend
    except ImportError:
        return {
            "success": False,
            "backend": "unavailable",
            "stderr": "formal_proof_service is not installed in this environment",
            "contains_forbidden": False,
            "forbidden_matches": [],
            "exit_code": None,
            "duration_ms": 0,
            "environment": {},
        }

    # Test / CI escape hatch: force a recorded failure without calling lake.
    if os.environ.get("FORMAL_SKIP_LEAN", "").lower() in {"1", "true", "yes"}:
        return {
            "success": False,
            "backend": "skipped",
            "stderr": "FORMAL_SKIP_LEAN set; lake not executed",
            "contains_forbidden": False,
            "forbidden_matches": [],
            "exit_code": None,
            "duration_ms": 0,
            "environment": {"skipped": True},
        }

    backend = LeanLakeBackend()
    result = await backend.check(
        ProofCheckRequest(
            project_path=str(project_path),
            timeout_seconds=int(os.environ.get("FORMAL_LEAN_TIMEOUT", "300")),
            forbidden_constructs=list(AGENT_FORBIDDEN),
        )
    )
    return {
        "success": bool(result.success and not result.contains_forbidden),
        "backend": result.backend,
        "stderr": result.stderr,
        "stdout": result.stdout,
        "contains_forbidden": result.contains_forbidden,
        "forbidden_matches": result.forbidden_matches,
        "exit_code": result.exit_code,
        "duration_ms": result.duration_ms,
        "environment": result.environment,
        "checked_at": result.checked_at.isoformat() if result.checked_at else None,
        "request_id": result.request_id,
    }


async def propose_candidate_proof(state: AgentGraphState) -> NodeResult:
    """Materialize the Lean project and run an independent kernel/lake check.

    Sets ``lean_verified=True`` only when that check succeeds without forbidden
    constructs. Agent graphs never self-attest proof success.
    """
    skeleton = state.lean_skeleton or ""
    claims = state.claims or []
    if not skeleton.strip():
        return NodeResult(
            node="propose_candidate_proof",
            output={
                "candidate_proof": {
                    "kind": "candidate_proof",
                    "status": "missing_skeleton",
                    "backend": "lean4",
                    "notes": "No lean_skeleton on state; run formalization first.",
                },
                "needs_independent_verification": True,
                "lean_verified": False,
                "certificate_ready": False,
            },
            error="proof requires lean_skeleton from formalization",
        )

    dest = _workdir_root() / state.run_id
    project = materialize_lean_project(
        skeleton,
        dest,
        module_name=DEFAULT_MODULE,
        repo_root=find_repo_root(),
    )
    report = await _run_lean_check(project)
    lean_verified = bool(report.get("success"))

    primary_theorem = None
    formal = state.data.get("draft_lean_skeleton") or {}
    theorems = formal.get("theorems") or []
    if theorems:
        primary_theorem = f"FormalPlatform.Model.{theorems[0].get('name')}"
    elif claims:
        primary_theorem = f"FormalPlatform.Model.{claims[0].get('id', 'claim')}"

    candidate: dict[str, Any] = {
        "kind": "candidate_proof",
        "status": "verified" if lean_verified else "unverified",
        "backend": "lean4",
        "tactics": ["lake_build"],
        "source_skeleton": skeleton,
        "lean_project_path": str(project.resolve()),
        "theorem": primary_theorem,
        "claim_ids": [c.get("id") for c in claims if isinstance(c, dict)],
        "verification": report,
        "notes": (
            "Independent lake build succeeded; lean_verified=True."
            if lean_verified
            else (
                "Independent lake build did not succeed. Install Lean 4 + lake, "
                "ensure FORMAL_LEAN_WORKDIR is writable, then re-run proof. "
                f"stderr_tail={(str(report.get('stderr') or ''))[-500:]}"
            )
        ),
    }
    output: dict[str, Any] = {
        "candidate_proof": candidate,
        "lean_project_path": str(project.resolve()),
        "verification_report": report,
        "needs_independent_verification": not lean_verified,
        "lean_verified": lean_verified,
        "certificate_ready": False,
    }
    return NodeResult(node="propose_candidate_proof", output=output)


def build_proof_graph() -> TypedGraph:
    return TypedGraph(
        name=GraphName.PROOF,
        entry="propose_candidate_proof",
        nodes={"propose_candidate_proof": propose_candidate_proof},
        edges={"propose_candidate_proof": None},
        metadata={
            "deterministic": True,
            "verifies": True,
            "requires_independent_lean_check": True,
            "forbidden_constructs": list(AGENT_FORBIDDEN),
        },
    )
