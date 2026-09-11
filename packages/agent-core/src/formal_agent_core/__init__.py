"""Agent core scaffold — LangGraph graphs land in Phase 5."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class GraphName(StrEnum):
    PROBLEM_MODELLING = "problem_modelling"
    FORMALIZATION = "formalization"
    PROOF = "proof"
    EVIDENCE_VALIDATION = "evidence_validation"
    CERTIFICATION = "certification"
    RESEARCH = "research"


class AgentGraphState(BaseModel):
    """Typed graph state placeholder."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    organization_id: str
    workspace_id: str
    project_id: str
    graph: GraphName
    artifact_ids: list[str] = Field(default_factory=list)
    pending_human_review: bool = False
