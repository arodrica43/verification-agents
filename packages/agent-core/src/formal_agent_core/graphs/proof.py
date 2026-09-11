"""Proof graph stub — emits candidate proofs only; never claims Lean success."""

from __future__ import annotations

from typing import Any

from formal_agent_core.graph import TypedGraph
from formal_agent_core.state import AgentGraphState, GraphName, NodeResult


async def propose_candidate_proof(state: AgentGraphState) -> NodeResult:
    """Produce a candidate_proof artifact. Does NOT verify.

    Lean kernel verification is the sole authority for proof success. This node
    always sets ``needs_independent_verification=True`` and never sets
    ``lean_verified=True``.
    """
    skeleton = state.lean_skeleton or ""
    claims = state.claims or []
    candidate: dict[str, Any] = {
        "kind": "candidate_proof",
        "status": "unverified",
        "backend": "lean4",
        "tactics": ["sorry"],
        "source_skeleton": skeleton,
        "claim_ids": [c.get("id") for c in claims if isinstance(c, dict)],
        "notes": (
            "Agent-generated candidate only. Must be checked by an independent "
            "Lean kernel session before any certificate issuance."
        ),
    }
    return NodeResult(
        node="propose_candidate_proof",
        output={
            "candidate_proof": candidate,
            "needs_independent_verification": True,
            # Explicitly false — agent graphs must never claim verification.
            "lean_verified": False,
        },
    )


def build_proof_graph() -> TypedGraph:
    return TypedGraph(
        name=GraphName.PROOF,
        entry="propose_candidate_proof",
        nodes={"propose_candidate_proof": propose_candidate_proof},
        edges={"propose_candidate_proof": None},
        metadata={
            "deterministic": True,
            "verifies": False,
            "requires_independent_lean_check": True,
        },
    )
