"""Problem modelling graph — deterministic NL domain modelling (no LLM)."""

from __future__ import annotations

from formal_agent_core.graph import TypedGraph
from formal_agent_core.nl_model import (
    assumptions_from_model,
    build_domain_model,
    claims_from_goals,
    goals_from_model,
)
from formal_agent_core.state import AgentGraphState, GraphName, NodeResult


async def extract_entities(state: AgentGraphState) -> NodeResult:
    model = build_domain_model(state.problem_text)
    return NodeResult(
        node="extract_entities",
        output={
            "entities": model.entities,
            "relations": model.relations,
            "product_kinds": model.product_kinds,
            "obligation_sentences": model.obligation_sentences,
            "domain_model": {
                "entity_count": len(model.entities),
                "relation_count": len(model.relations),
                "product_kinds": model.product_kinds,
                "obligations": model.obligation_sentences,
            },
        },
    )


async def draft_assumptions(state: AgentGraphState) -> NodeResult:
    # Rebuild from text so assumptions stay aligned even if entities were edited.
    model = build_domain_model(state.problem_text)
    if state.entities:
        # Prefer entities already extracted in this run
        model.entities = state.entities
        extract = state.data.get("extract_entities") or {}
        if extract.get("relations"):
            model.relations = list(extract["relations"])
        if extract.get("product_kinds"):
            model.product_kinds = list(extract["product_kinds"])
    assumptions = assumptions_from_model(model)
    return NodeResult(
        node="draft_assumptions",
        output={"assumptions": assumptions, "relations": model.relations},
    )


async def propose_goals(state: AgentGraphState) -> NodeResult:
    model = build_domain_model(state.problem_text)
    extract = state.data.get("extract_entities") or {}
    if extract.get("obligation_sentences"):
        model.obligation_sentences = list(extract["obligation_sentences"])
    if state.entities:
        model.entities = state.entities
    assumptions = state.assumptions or (state.data.get("draft_assumptions") or {}).get(
        "assumptions", []
    )
    goals = goals_from_model(model, state.problem_text)
    claims = claims_from_goals(goals, assumptions)
    return NodeResult(
        node="propose_goals",
        output={"goals": goals, "claims": claims},
    )


def build_problem_modelling_graph(
    *,
    interrupt_before: frozenset[str] | None = None,
) -> TypedGraph:
    """``extract_entities -> draft_assumptions -> propose_goals``."""
    return TypedGraph(
        name=GraphName.PROBLEM_MODELLING,
        entry="extract_entities",
        nodes={
            "extract_entities": extract_entities,
            "draft_assumptions": draft_assumptions,
            "propose_goals": propose_goals,
        },
        edges={
            "extract_entities": "draft_assumptions",
            "draft_assumptions": "propose_goals",
            "propose_goals": None,
        },
        interrupt_before=interrupt_before or frozenset(),
        metadata={"deterministic": True, "requires_llm": False},
    )
