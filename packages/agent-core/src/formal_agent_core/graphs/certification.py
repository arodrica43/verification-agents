"""Certification graph — requires prior independent Lean verification."""

from __future__ import annotations

from formal_agent_core.graph import TypedGraph
from formal_agent_core.state import AgentGraphState, GraphName, NodeResult


async def gate_lean_verified(state: AgentGraphState) -> NodeResult:
    """Refuse to proceed unless ``lean_verified`` was set by an independent check."""
    if not state.lean_verified:
        return NodeResult(
            node="gate_lean_verified",
            output={"certificate_ready": False},
            error=(
                "certification requires lean_verified=True from an independent "
                "Lean kernel check; agent graphs cannot self-attest proof success"
            ),
        )
    return NodeResult(
        node="gate_lean_verified",
        output={"gate": "passed", "lean_verified": True},
    )


async def prepare_certificate_bundle(state: AgentGraphState) -> NodeResult:
    """Mark a certificate as ready for the certificate-service (issuance is separate)."""
    return NodeResult(
        node="prepare_certificate_bundle",
        output={
            "certificate_ready": True,
            "bundle_hint": {
                "organization_id": state.organization_id,
                "workspace_id": state.workspace_id,
                "project_id": state.project_id,
                "artifact_ids": list(state.artifact_ids),
                "needs_independent_verification": False,
            },
        },
    )


def build_certification_graph() -> TypedGraph:
    return TypedGraph(
        name=GraphName.CERTIFICATION,
        entry="gate_lean_verified",
        nodes={
            "gate_lean_verified": gate_lean_verified,
            "prepare_certificate_bundle": prepare_certificate_bundle,
        },
        edges={
            "gate_lean_verified": "prepare_certificate_bundle",
            "prepare_certificate_bundle": None,
        },
        metadata={"requires_lean_verified": True},
    )
