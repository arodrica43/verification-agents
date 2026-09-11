"""Graph runner with optional checkpoint persistence and HITL resume."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from formal_agent_core.graph import TypedGraph
from formal_agent_core.state import AgentGraphState, NodeResult, RunStatus


@runtime_checkable
class CheckpointStore(Protocol):
    """Persist operational run checkpoints separately from scientific artifacts."""

    async def save(self, state: AgentGraphState) -> None: ...

    async def load(self, run_id: str) -> AgentGraphState | None: ...


class InMemoryCheckpointStore:
    """Process-local checkpoint store for tests and single-worker demos."""

    def __init__(self) -> None:
        self._data: dict[str, AgentGraphState] = {}

    async def save(self, state: AgentGraphState) -> None:
        self._data[state.run_id] = state.model_copy(deep=True)

    async def load(self, run_id: str) -> AgentGraphState | None:
        stored = self._data.get(run_id)
        return None if stored is None else stored.model_copy(deep=True)


class GraphRunner:
    """Execute a TypedGraph sequentially with branching and HITL interrupts.

    LangGraph is never required. If ``langgraph`` is installed, callers may still
    use this native runner; adapters can be layered later without changing graphs.
    """

    def __init__(
        self,
        graph: TypedGraph,
        *,
        checkpoints: CheckpointStore | None = None,
    ) -> None:
        graph.validate()
        self.graph = graph
        self.checkpoints = checkpoints

    async def run(self, state: AgentGraphState) -> AgentGraphState:
        """Start (or continue) a run from ``state.current_node`` or the graph entry."""
        if state.graph != self.graph.name:
            raise ValueError(
                f"state.graph={state.graph!r} does not match runner graph {self.graph.name!r}"
            )
        state = state.model_copy(deep=True)
        if state.current_node is None:
            state.current_node = self.graph.entry
        state.status = RunStatus.RUNNING
        state.pending_human_review = False
        state.interrupt_node = None
        state.error = None
        await self._persist(state)
        return await self._loop(state, resume_approved=False)

    async def resume(
        self,
        run_id: str,
        *,
        updates: dict[str, Any] | None = None,
        state: AgentGraphState | None = None,
    ) -> AgentGraphState:
        """Resume after human review. Requires a prior INTERRUPTED checkpoint."""
        if state is None:
            if self.checkpoints is None:
                raise RuntimeError("resume requires a CheckpointStore or an explicit state")
            loaded = await self.checkpoints.load(run_id)
            if loaded is None:
                raise KeyError(f"no checkpoint for run_id={run_id!r}")
            state = loaded
        else:
            if state.run_id != run_id:
                raise ValueError("state.run_id does not match resume run_id")

        if state.status != RunStatus.INTERRUPTED:
            raise RuntimeError(
                f"cannot resume run in status={state.status!r}; expected interrupted"
            )
        if state.interrupt_node is None or state.current_node is None:
            raise RuntimeError("interrupted state missing interrupt_node/current_node")

        state = state.model_copy(deep=True)
        if updates:
            state = self._apply_updates(state, updates)
        # Human approved execution of the gated node.
        state.status = RunStatus.RUNNING
        state.pending_human_review = False
        approved = state.interrupt_node
        state.interrupt_node = None
        await self._persist(state)
        return await self._loop(state, resume_approved=True, approved_node=approved)

    async def _loop(
        self,
        state: AgentGraphState,
        *,
        resume_approved: bool,
        approved_node: str | None = None,
    ) -> AgentGraphState:
        while state.current_node is not None:
            node = state.current_node
            if node not in self.graph.nodes:
                state.status = RunStatus.FAILED
                state.error = f"unknown node {node!r}"
                await self._persist(state)
                return state

            # HITL: pause before gated nodes unless this resume just approved it.
            if node in self.graph.interrupt_before and not (
                resume_approved and approved_node == node
            ):
                state.status = RunStatus.INTERRUPTED
                state.pending_human_review = True
                state.interrupt_node = node
                await self._persist(state)
                return state

            # Consume one-shot resume approval.
            resume_approved = False
            approved_node = None

            fn = self.graph.nodes[node]
            try:
                result = await fn(state)
            except Exception as exc:  # noqa: BLE001 — surface as failed run
                state.status = RunStatus.FAILED
                state.error = f"{type(exc).__name__}: {exc}"
                await self._persist(state)
                return state

            state = self._merge_result(state, result)
            if result.error:
                state.status = RunStatus.FAILED
                state.error = result.error
                await self._persist(state)
                return state

            state.history = [*state.history, node]
            if result.next_node is not None:
                state.current_node = result.next_node
            else:
                state.current_node = self.graph.edges.get(node)

            await self._persist(state)

        state.status = RunStatus.COMPLETED
        state.pending_human_review = False
        state.interrupt_node = None
        await self._persist(state)
        return state

    def _merge_result(self, state: AgentGraphState, result: NodeResult) -> AgentGraphState:
        data = dict(state.data)
        data[result.node] = result.output
        patch: dict[str, Any] = {"data": data}

        # Promote well-known keys onto top-level state when present.
        for key in (
            "entities",
            "assumptions",
            "goals",
            "claims",
            "lean_skeleton",
            "candidate_proof",
            "lean_project_path",
            "verification_report",
            "needs_independent_verification",
            "lean_verified",
            "certificate_ready",
            "certificate_id",
            "issued_certificate",
            "artifact_ids",
            "problem_text",
        ):
            if key in result.output:
                patch[key] = result.output[key]

        return state.model_copy(update=patch)

    @staticmethod
    def _apply_updates(state: AgentGraphState, updates: dict[str, Any]) -> AgentGraphState:
        allowed = set(AgentGraphState.model_fields)
        filtered = {k: v for k, v in updates.items() if k in allowed and k != "run_id"}
        return state.model_copy(update=filtered)

    async def _persist(self, state: AgentGraphState) -> None:
        if self.checkpoints is not None:
            await self.checkpoints.save(state)
