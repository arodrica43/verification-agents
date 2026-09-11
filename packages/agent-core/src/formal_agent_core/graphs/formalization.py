"""Formalization graph stub — Lean-shaped theorem skeletons from claims."""

from __future__ import annotations

from typing import Any

from formal_agent_core.graph import TypedGraph
from formal_agent_core.state import AgentGraphState, GraphName, NodeResult


def _lean_ident(raw: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in raw.strip())
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"T_{cleaned}"
    return cleaned[:64] or "TheoremStub"


async def draft_lean_skeleton(state: AgentGraphState) -> NodeResult:
    claims = state.claims
    if not claims and state.goals:
        claims = [
            {
                "id": f"claim-{g.get('id', i)}",
                "statement": g.get("statement", "goal"),
                "assumption_ids": [a.get("id") for a in state.assumptions],
            }
            for i, g in enumerate(state.goals)
        ]

    theorems: list[dict[str, Any]] = []
    parts: list[str] = [
        "/-!",
        "  Auto-generated formalization stub.",
        "  NOT verified. Independent Lean kernel check required.",
        "-/",
        "",
        "namespace FormalPlatform.Stub",
        "",
    ]
    for i, claim in enumerate(claims or [{"id": "claim-1", "statement": "placeholder"}]):
        name = _lean_ident(str(claim.get("id", f"claim_{i}")))
        stmt = str(claim.get("statement", "True"))
        asm_ids = claim.get("assumption_ids") or [a.get("id") for a in state.assumptions]
        hyp_lines = "\n".join(
            f"  ({_lean_ident(str(a))} : Prop) -- assumption {a}" for a in (asm_ids or ["A"])
        )
        body = (
            f"/-- Claim: {stmt} -/\n"
            f"theorem {_lean_ident(name)} :\n"
            f"{hyp_lines if hyp_lines else '  True'}\n"
            f"  → True := by\n"
            f"  sorry  -- candidate only; needs independent verification\n"
        )
        parts.append(body)
        theorems.append(
            {
                "name": _lean_ident(name),
                "claim_id": claim.get("id"),
                "statement": stmt,
                "has_sorry": True,
            }
        )

    parts.append("end FormalPlatform.Stub")
    skeleton = "\n".join(parts)
    return NodeResult(
        node="draft_lean_skeleton",
        output={
            "lean_skeleton": skeleton,
            "theorems": theorems,
            "needs_independent_verification": True,
            "lean_verified": False,
        },
    )


def build_formalization_graph() -> TypedGraph:
    return TypedGraph(
        name=GraphName.FORMALIZATION,
        entry="draft_lean_skeleton",
        nodes={"draft_lean_skeleton": draft_lean_skeleton},
        edges={"draft_lean_skeleton": None},
        metadata={"deterministic": True, "requires_llm": False},
    )
