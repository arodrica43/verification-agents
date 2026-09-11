"""Typed agent graph state and run metadata."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class GraphName(StrEnum):
    PROBLEM_MODELLING = "problem_modelling"
    FORMALIZATION = "formalization"
    PROOF = "proof"
    EVIDENCE_VALIDATION = "evidence_validation"
    CERTIFICATION = "certification"
    RESEARCH = "research"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    INTERRUPTED = "interrupted"
    COMPLETED = "completed"
    FAILED = "failed"


class NodeResult(BaseModel):
    """Structured result returned by a graph node."""

    model_config = ConfigDict(extra="forbid")

    node: str
    output: dict[str, Any] = Field(default_factory=dict)
    """Merged into ``AgentGraphState.data`` under the node name (and selected top-level fields)."""

    next_node: str | None = None
    """Override the static edge target when set (branching). ``None`` means follow static edges."""

    error: str | None = None


class AgentGraphState(BaseModel):
    """Operational state for a single graph run (not a scientific knowledge artifact)."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    organization_id: str
    workspace_id: str
    project_id: str
    graph: GraphName
    status: RunStatus = RunStatus.PENDING
    current_node: str | None = None
    """Node about to execute, or the interrupt gate currently waiting for human review."""

    artifact_ids: list[str] = Field(default_factory=list)
    pending_human_review: bool = False
    interrupt_node: str | None = None
    """When status is INTERRUPTED, the node that must not run until resume."""

    # Modelling / formalization inputs & stubs
    problem_text: str = ""
    entities: list[dict[str, Any]] = Field(default_factory=list)
    assumptions: list[dict[str, Any]] = Field(default_factory=list)
    goals: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[dict[str, Any]] = Field(default_factory=list)

    # Formal / proof-related fields (agent-produced; Lean remains sole verifier)
    lean_skeleton: str | None = None
    candidate_proof: dict[str, Any] | None = None
    needs_independent_verification: bool = False
    lean_verified: bool = False
    """Set only by an independent Lean kernel check — never by agent graphs."""

    certificate_ready: bool = False
    error: str | None = None

    # Free-form node outputs keyed by node name
    data: dict[str, Any] = Field(default_factory=dict)
    history: list[str] = Field(default_factory=list)
    """Ordered list of completed node names."""
