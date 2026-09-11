"""Phase 5+ agent-core: modelling, formalization, Lean proof, certification."""

from __future__ import annotations

from pathlib import Path

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
from formal_agent_core.lean_project import AGENT_FORBIDDEN, materialize_lean_project
from formal_proof_service.backend import ProofCheckRequest
from formal_proof_service.lean_backend import LeanLakeBackend
from formal_shared.ids import new_id

FACTORY_PROBLEM = (
    "We are working in a pre-cooked food factory. We have 3 machines. "
    "One machine produces solid and liquid products, and distributes them into "
    "the two other packing machines, so one handles the liquids and the other "
    "the solids. Every machine has a thermostat, a production speed "
    "(production or packing speed), and the type of product they are handling. "
    "Types of products can be solid-a, solid-b and solid-c for solids, and "
    "liquid-a and liquid-b. As each machine has a small buffer while processing "
    "products, we have also buffer size for each machine. Each product has its "
    "own temperature too. There's a group of workers that can work with the "
    "machines, by turning-on, off and changing the machine parameters at any "
    "moment. We must ensure that temperature of machines behaves accordingly "
    "to the product temperature initially."
)


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
async def test_proof_graph_rejects_sorry_without_claiming_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("FORMAL_LEAN_WORKDIR", str(tmp_path))
    monkeypatch.delenv("FORMAL_SKIP_LEAN", raising=False)
    graph = build_proof_graph()
    runner = GraphRunner(graph)
    state = await runner.run(
        _base_state(
            graph=GraphName.PROOF,
            lean_skeleton="theorem T : True := by\n  sorry\n",
            claims=[{"id": "claim-1", "statement": "True"}],
        )
    )
    assert state.status == RunStatus.COMPLETED
    assert state.candidate_proof is not None
    assert state.candidate_proof["kind"] == "candidate_proof"
    assert state.lean_verified is False
    assert state.needs_independent_verification is True
    report = state.verification_report or {}
    assert report.get("contains_forbidden") is True or report.get("success") is False


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
async def test_formalization_emits_real_theorems_not_axioms() -> None:
    graph = build_formalization_graph()
    runner = GraphRunner(graph)
    state = await runner.run(
        _base_state(
            graph=GraphName.FORMALIZATION,
            claims=[
                {
                    "id": "claim-safe",
                    "statement": "Must never export secrets.",
                    "assumption_ids": ["asm-1"],
                }
            ],
            goals=[{"id": "goal-1", "statement": "Must never export secrets.", "kind": "safety"}],
            assumptions=[{"id": "asm-1", "statement": "closed world"}],
        )
    )
    assert state.status == RunStatus.COMPLETED
    assert state.lean_skeleton is not None
    assert "sorry" not in state.lean_skeleton
    assert "axiom" not in state.lean_skeleton
    assert "theorem" in state.lean_skeleton
    assert state.needs_independent_verification is True
    assert state.lean_verified is False


@pytest.mark.asyncio
async def test_factory_modelling_extracts_meaningful_domain() -> None:
    graph = build_problem_modelling_graph()
    runner = GraphRunner(graph, checkpoints=InMemoryCheckpointStore())
    state = await runner.run(_base_state(problem_text=FACTORY_PROBLEM))

    assert state.status == RunStatus.COMPLETED
    names = {str(e.get("name", "")).lower() for e in state.entities}
    kinds = {str(e.get("kind")) for e in state.entities}
    assert "we" not in names
    assert "every" not in names
    assert "one" not in names
    assert "types" not in names
    assert "component" in kinds
    assert any("machine" in n for n in names)
    assert any("worker" in n for n in names)
    assert any("product" in n for n in names)

    statements = [str(a.get("statement", "")).lower() for a in state.assumptions]
    assert statements
    assert not any("behaves according to declared policy" in s for s in statements)
    assert any("thermostat" in s or "attribute" in s for s in statements)
    assert any("solid-a" in s or "product kind" in s for s in statements)

    goal_text = " ".join(str(g.get("statement", "")).lower() for g in state.goals)
    assert "temperature" in goal_text


@pytest.mark.asyncio
async def test_factory_pipeline_lean_model() -> None:
    store = InMemoryCheckpointStore()
    modelled = await GraphRunner(
        build_problem_modelling_graph(), checkpoints=store
    ).run(_base_state(problem_text=FACTORY_PROBLEM))

    formal = await GraphRunner(build_formalization_graph(), checkpoints=store).run(
        _base_state(
            graph=GraphName.FORMALIZATION,
            problem_text=FACTORY_PROBLEM,
            entities=modelled.entities,
            assumptions=modelled.assumptions,
            goals=modelled.goals,
            claims=modelled.claims,
            data=modelled.data,
        )
    )
    skel = formal.lean_skeleton or ""
    assert "inductive ProductKind" in skel
    assert "solidA" in skel
    assert "structure Machine" in skel
    assert "thermostatMatchesProduct" in skel
    assert "theorem" in skel
    assert "sorry" not in skel
    assert "axiom" not in skel
    assert formal.lean_verified is False


@pytest.mark.asyncio
async def test_materialized_factory_model_has_no_forbidden(tmp_path: Path) -> None:
    formal = await GraphRunner(build_formalization_graph()).run(
        _base_state(
            graph=GraphName.FORMALIZATION,
            problem_text=FACTORY_PROBLEM,
            goals=[
                {
                    "id": "goal-1",
                    "statement": "Temperature of machines behaves accordingly to the product temperature initially.",
                    "kind": "invariant",
                }
            ],
            claims=[
                {
                    "id": "claim-goal-1",
                    "statement": "Under the modelled assumptions, temperature of machines behaves accordingly to the product temperature initially.",
                }
            ],
        )
    )
    project = materialize_lean_project(formal.lean_skeleton or "", tmp_path / "proj")
    backend = LeanLakeBackend()
    matches = backend._scan_forbidden(project, list(AGENT_FORBIDDEN))
    assert matches == []


@pytest.mark.lean
@pytest.mark.asyncio
async def test_factory_proof_graph_sets_lean_verified(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FORMAL_LEAN_WORKDIR", str(tmp_path))
    monkeypatch.delenv("FORMAL_SKIP_LEAN", raising=False)
    modelled = await GraphRunner(build_problem_modelling_graph()).run(
        _base_state(problem_text=FACTORY_PROBLEM)
    )
    formal = await GraphRunner(build_formalization_graph()).run(
        _base_state(
            graph=GraphName.FORMALIZATION,
            problem_text=FACTORY_PROBLEM,
            entities=modelled.entities,
            assumptions=modelled.assumptions,
            goals=modelled.goals,
            claims=modelled.claims,
            data=modelled.data,
        )
    )
    proved = await GraphRunner(build_proof_graph()).run(
        _base_state(
            graph=GraphName.PROOF,
            problem_text=FACTORY_PROBLEM,
            entities=formal.entities or modelled.entities,
            assumptions=formal.assumptions or modelled.assumptions,
            goals=formal.goals or modelled.goals,
            claims=formal.claims or modelled.claims,
            lean_skeleton=formal.lean_skeleton,
            data=formal.data,
        )
    )
    if proved.verification_report and "not found" in str(
        proved.verification_report.get("stderr", "")
    ).lower():
        pytest.skip("lake not available")
    assert proved.lean_verified is True
    assert proved.lean_project_path
    assert Path(proved.lean_project_path).exists()
    # Re-check with backend directly
    result = await LeanLakeBackend().check(
        ProofCheckRequest(
            project_path=proved.lean_project_path,
            forbidden_constructs=list(AGENT_FORBIDDEN),
        )
    )
    assert result.success is True
    assert result.contains_forbidden is False
