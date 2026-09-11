"""Formalization graph — Lean model + proof obligations from the domain model."""

from __future__ import annotations

import re
from typing import Any

from formal_agent_core.graph import TypedGraph
from formal_agent_core.nl_model import build_domain_model
from formal_agent_core.state import AgentGraphState, GraphName, NodeResult


def _lean_ident(raw: str) -> str:
    cleaned = "".join(ch if ch.isalnum() else "_" for ch in raw.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned or cleaned[0].isdigit():
        cleaned = f"T_{cleaned}"
    return cleaned[:64] or "TheoremStub"


def _lean_ctor(raw: str) -> str:
    """solid-a → solidA."""
    parts = re.split(r"[-_\s]+", raw.strip().lower())
    if not parts:
        return "anon"
    head, *rest = parts
    return head + "".join(p.capitalize() for p in rest if p)


def _pascal(raw: str) -> str:
    parts = re.split(r"[-_\s]+", raw.strip())
    return "".join(p[:1].upper() + p[1:] for p in parts if p) or "Entity"


def _collect_product_kinds(state: AgentGraphState) -> list[str]:
    extract = state.data.get("extract_entities") or {}
    kinds = list(extract.get("product_kinds") or [])
    if kinds:
        return kinds
    # Recover from entity notes
    for ent in state.entities:
        notes = str(ent.get("notes") or "")
        if notes.startswith("kinds="):
            return [k for k in notes[6:].split(",") if k]
    if state.problem_text:
        return build_domain_model(state.problem_text).product_kinds
    return []


def _machine_attrs(state: AgentGraphState) -> list[str]:
    for ent in state.entities:
        if str(ent.get("kind")) == "component" and ent.get("attributes"):
            return [str(a) for a in ent["attributes"]]
    for ent in state.entities:
        if "machine" in str(ent.get("name", "")).lower() and ent.get("attributes"):
            return [str(a) for a in ent["attributes"]]
    return ["thermostat", "speed", "product_kind", "buffer_size"]


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
    if not claims:
        claims = [{"id": "claim-1", "statement": "Stated constraints are preserved."}]

    product_kinds = _collect_product_kinds(state)
    machine_attrs = _machine_attrs(state)
    has_temp = any(
        "temp" in a or a == "thermostat" for a in machine_attrs
    ) or any("temperature" in str(g.get("statement", "")).lower() for g in state.goals)

    parts: list[str] = [
        "/-!",
        "  Auto-generated domain model and proof obligations.",
        "  Definitions are candidates — independent Lean kernel check required.",
        "  Claims are stated as axioms (not proofs). Do not treat as verified.",
        "-/",
        "",
        "namespace FormalPlatform.Model",
        "",
    ]

    # Product kind inductive
    if product_kinds:
        parts.append("inductive ProductKind where")
        for k in product_kinds:
            parts.append(f"  | {_lean_ctor(k)}")
        parts.append("  deriving DecidableEq, Repr")
        parts.append("")
    else:
        parts.extend(
            [
                "inductive ProductKind where",
                "  | generic",
                "  deriving DecidableEq, Repr",
                "",
            ]
        )

    if has_temp:
        parts.extend(
            [
                "structure Temperature where",
                "  value : Int",
                "  deriving Repr",
                "",
                "structure Product where",
                "  kind : ProductKind",
                "  temperature : Temperature",
                "  deriving Repr",
                "",
                "structure Machine where",
                "  thermostat : Temperature",
                "  speed : Nat",
                "  productKind : ProductKind",
                "  bufferSize : Nat",
                "  deriving Repr",
                "",
                "/-- Machine thermostat setting matches the product being processed. -/",
                "def thermostatMatchesProduct (m : Machine) (p : Product) : Prop :=",
                "  m.thermostat.value = p.temperature.value ∧ m.productKind = p.kind",
                "",
            ]
        )
    else:
        # Generic component model from entities
        parts.extend(
            [
                "structure Component where",
                "  name : String",
                "  deriving Repr",
                "",
            ]
        )

    # Assumption comments (documentation) + named axiom placeholders
    for asm in state.assumptions:
        aid = _lean_ident(str(asm.get("id", "asm")))
        stmt = str(asm.get("statement", "")).replace("\n", " ")
        parts.append(f"/-- Assumption {asm.get('id')}: {stmt} -/")
        parts.append(f"axiom {aid} : True")
        parts.append("")

    theorems: list[dict[str, Any]] = []
    for i, claim in enumerate(claims):
        name = _lean_ident(str(claim.get("id", f"claim_{i}")))
        stmt = str(claim.get("statement", "True")).replace("\n", " ")
        goal_kind = "invariant"
        for g in state.goals:
            if str(claim.get("goal_id")) == str(g.get("id")):
                goal_kind = str(g.get("kind") or "invariant")
                break

        parts.append(f"/-- Claim: {stmt} -/")
        if has_temp and ("temperature" in stmt.lower() or "thermostat" in stmt.lower()):
            parts.append(f"def {_pascal(name)}Goal (m : Machine) (p : Product) : Prop :=")
            parts.append("  thermostatMatchesProduct m p")
            parts.append("")
            parts.append(
                f"/-- Proof obligation (unproven). Replace axiom with a theorem + proof. -/"
            )
            parts.append(f"axiom {name} :")
            parts.append("  ∀ (m : Machine) (p : Product),")
            parts.append(f"    {_pascal(name)}Goal m p")
        else:
            parts.append(
                f"/-- Proof obligation (unproven). Replace axiom with a theorem + proof. -/"
            )
            parts.append(f"axiom {name} : True  -- TODO: encode: {stmt}")
        parts.append("")
        theorems.append(
            {
                "name": name,
                "claim_id": claim.get("id"),
                "statement": stmt,
                "kind": goal_kind,
                "has_sorry": False,
                "is_axiom": True,
            }
        )

    parts.append("end FormalPlatform.Model")
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
