"""NL problem modelling helpers (Phase 6 foundation — deterministic, no LLM)."""

from __future__ import annotations

import re
from typing import Any

_ENTITY = re.compile(r"\b([A-Z][a-zA-Z0-9]+(?:\s+[A-Z][a-zA-Z0-9]+)*)\b")


def extract_problem_model(text: str) -> dict[str, Any]:
    """Extract a coarse problem model from free text without an LLM."""
    entities = []
    seen: set[str] = set()
    for match in _ENTITY.finditer(text):
        name = match.group(1).strip()
        if name.lower() in {"the", "and", "for", "with"} or name in seen:
            continue
        seen.add(name)
        entities.append({"id": f"ent-{len(entities)+1}", "name": name})
    goals = []
    for i, line in enumerate(text.splitlines()):
        lower = line.lower()
        if any(k in lower for k in ("must", "should", "prove", "ensure", "require")):
            goals.append({"id": f"goal-{len(goals)+1}", "statement": line.strip()})
    if not goals and text.strip():
        goals.append({"id": "goal-1", "statement": text.strip().split(".")[0][:240]})
    assumptions = [
        {
            "id": "asm-model-fit",
            "statement": "The extracted entities adequately model the system under study",
            "category": "user_asserted",
        }
    ]
    return {
        "entities": entities[:20],
        "goals": goals[:10],
        "assumptions": assumptions,
        "modelling_method": "deterministic_heuristic_v1",
        "needs_human_review": True,
    }


def claim_to_lean_skeleton(claim: str, theorem_name: str = "claim_theorem") -> str:
    """Produce a Lean-shaped skeleton that still requires real proof work."""
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", theorem_name)
    return (
        f"-- Auto-formalization skeleton (NOT verified)\n"
        f"-- Claim: {claim}\n"
        f"theorem {safe} : True := by\n"
        f"  trivial\n"
        f"-- Replace True with the real proposition; do not use unfinished proofs.\n"
    )
