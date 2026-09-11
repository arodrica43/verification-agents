"""Typed graph definition without a hard LangGraph dependency."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from formal_agent_core.state import AgentGraphState, GraphName, NodeResult

# Optional LangGraph import — never required at runtime for the native runner.
try:
    import langgraph  # type: ignore[import-untyped]  # noqa: F401

    HAS_LANGGRAPH = True
except ImportError:
    HAS_LANGGRAPH = False

NodeFn = Callable[[AgentGraphState], Awaitable[NodeResult]]
"""Async node callable: receives state, returns a NodeResult."""


@dataclass(frozen=True, slots=True)
class TypedGraph:
    """Deterministic typed graph: named async nodes + static edges + HITL gates."""

    name: GraphName
    entry: str
    nodes: Mapping[str, NodeFn]
    edges: Mapping[str, str | None]
    """Maps ``from_node -> next_node``. ``None`` means terminal after that node."""

    interrupt_before: frozenset[str] = field(default_factory=frozenset)
    """Pause before executing these nodes until ``GraphRunner.resume``."""

    metadata: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.entry not in self.nodes:
            raise ValueError(f"entry node {self.entry!r} not in nodes")
        for src, dst in self.edges.items():
            if src not in self.nodes:
                raise ValueError(f"edge source {src!r} not in nodes")
            if dst is not None and dst not in self.nodes:
                raise ValueError(f"edge target {dst!r} not in nodes")
        for name in self.interrupt_before:
            if name not in self.nodes:
                raise ValueError(f"interrupt_before node {name!r} not in nodes")

    def successors(self, node: str) -> Sequence[str]:
        nxt = self.edges.get(node)
        return () if nxt is None else (nxt,)
