"""Phase 5 agent-core: modelling graph + HITL interrupt/resume."""

from __future__ import annotations

import pytest

from formal_agent_core import (
    AgentGraphState,
    GraphName,
    GraphRunner,
    InMemoryCheckpointStore,
    RunStatus,
    build_certification_graph,
    build_formalization_graph,
    build_problem_modelling_graph,
    build_proof_graph,
)
from formal_shared.ids import new_id


def _base_state(**kwargs: object) -> AgentGraphState:
    defaults: dict[str, object] = {
        "run_id": new_id(),
        "organization_id": "org-1",
        "workspace_id": "ws-1",
        "project_id": "proj-1",
        "graph": GraphName.PROBLEM_MODELLING,
        "problem_text": (
            "An Agent Policy must never export secrets. "
            "The Safety Monitor ensures forbidden actions are blocked."
        ),
    }
    defaults.update(kwargs)
    return AgentGraphState.model_validate(defaults)


@pytest.mark.asyncio
async def test_problem_modelling_graph_deterministic() -> None:
    graph = build_problem_modelling_graph()
    runner = GraphRunner(graph, checkpoints=InMemoryCheckpointStore())
    state = await runner.run(_base_state())

    assert state.status == RunStatus.COMPLETED
    assert state.history == ["extract_entities", "draft_assumptions", "propose_goals"]
    assert len(state.entities) >= 1
    assert len(state.assumptions) >= 1
    assert len(state.goals) >= 1
    assert any(g.get("kind") == "safety" for g in state.goals)
    assert len(state.claims) == len(state.goals)
    assert state.lean_verified is False
    assert state.data["extract_entities"]["entities"] == state.entities


@pytest.mark.asyncio
async def test_hitl_interrupt_and_resume() -> None:
    store = InMemoryCheckpointStore()
    graph = build_problem_modelling_graph(interrupt_before=frozenset({"propose_goals"}))
    runner = GraphRunner(graph, checkpoints=store)
    run_id = new_id()

    interrupted = await runner.run(_base_state(run_id=run_id))
    assert interrupted.status == RunStatus.INTERRUPTED
    assert interrupted.pending_human_review is True
    assert interrupted.interrupt_node == "propose_goals"
    assert interrupted.current_node == "propose_goals"
    assert interrupted.history == ["extract_entities", "draft_assumptions"]
    assert interrupted.goals == []

    loaded = await store.load(run_id)
    assert loaded is not None
    assert loaded.status == RunStatus.INTERRUPTED

    completed = await runner.resume(run_id)
    assert completed.status == RunStatus.COMPLETED
    assert completed.pending_human_review is False
    assert completed.interrupt_node is None
    assert completed.history == ["extract_entities", "draft_assumptions", "propose_goals"]
    assert len(completed.goals) >= 1
    assert len(completed.claims) >= 1


@pytest.mark.asyncio
async def test_proof_graph_never_claims_verification() -> None:
    graph = build_proof_graph()
    runner = GraphRunner(graph)
    state = await runner.run(
        _base_state(
            graph=GraphName.PROOF,
            lean_skeleton="theorem T : True := by sorry",
            claims=[{"id": "claim-1", "statement": "True"}],
        )
    )
    assert state.status == RunStatus.COMPLETED
    assert state.candidate_proof is not None
    assert state.candidate_proof["kind"] == "candidate_proof"
    assert state.candidate_proof["status"] == "unverified"
    assert state.needs_independent_verification is True
    assert state.lean_verified is False


@pytest.mark.asyncio
async def test_certification_requires_lean_verified() -> None:
    graph = build_certification_graph()
    runner = GraphRunner(graph)

    denied = await runner.run(
        _base_state(graph=GraphName.CERTIFICATION, lean_verified=False)
    )
    assert denied.status == RunStatus.FAILED
    assert denied.certificate_ready is False
    assert denied.error is not None
    assert "lean_verified" in denied.error

    ok = await runner.run(_base_state(graph=GraphName.CERTIFICATION, lean_verified=True))
    assert ok.status == RunStatus.COMPLETED
    assert ok.certificate_ready is True


@pytest.mark.asyncio
async def test_formalization_skeleton_has_sorry() -> None:
    graph = build_formalization_graph()
    runner = GraphRunner(graph)
    state = await runner.run(
        _base_state(
            graph=GraphName.FORMALIZATION,
            claims=[{"id": "claim-safe", "statement": "safety holds", "assumption_ids": ["asm-1"]}],
            assumptions=[{"id": "asm-1", "statement": "closed world"}],
        )
    )
    assert state.status == RunStatus.COMPLETED
    assert state.lean_skeleton is not None
    assert "sorry" in state.lean_skeleton
    assert "theorem" in state.lean_skeleton
    assert state.needs_independent_verification is True
    assert state.lean_verified is False
