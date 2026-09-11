"""Problem modelling graph — deterministic stubs (no LLM required)."""

from __future__ import annotations

import re
from typing import Any

from formal_agent_core.graph import TypedGraph
from formal_agent_core.state import AgentGraphState, GraphName, NodeResult

_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "in",
        "for",
        "on",
        "with",
        "by",
        "is",
        "are",
        "be",
        "that",
        "this",
        "as",
        "at",
        "from",
        "it",
        "its",
        "must",
        "should",
        "shall",
        "will",
        "can",
        "may",
        "if",
        "then",
        "when",
        "where",
        "which",
        "who",
        "whom",
        "into",
        "over",
        "under",
        "not",
        "no",
        "nor",
        "but",
        "we",
        "our",
        "their",
        "they",
        "them",
        "his",
        "her",
        "has",
        "have",
        "had",
        "do",
        "does",
        "did",
        "been",
        "being",
        "was",
        "were",
        "such",
        "any",
        "all",
        "each",
        "every",
        "both",
        "few",
        "more",
        "most",
        "other",
        "some",
        "than",
        "too",
        "very",
        "just",
        "also",
        "only",
        "own",
        "same",
        "so",
        "via",
        "per",
        "using",
        "use",
        "used",
        "ensure",
        "ensures",
        "system",
        "systems",
        "agent",
        "agents",
        "policy",
        "policies",
    }
)


def _tokens(text: str) -> list[str]:
    return [t.lower() for t in re.findall(r"[A-Za-z][A-Za-z0-9_\-]*", text)]


def _noun_phrases(text: str) -> list[str]:
    """Very small heuristic: capitalized phrases + frequent content tokens."""
    phrases: list[str] = []
    for m in re.finditer(r"\b([A-Z][a-z0-9]+(?:\s+[A-Z][a-z0-9]+)*)\b", text):
        phrases.append(m.group(1))
    counts: dict[str, int] = {}
    for tok in _tokens(text):
        if tok in _STOPWORDS or len(tok) < 3:
            continue
        counts[tok] = counts.get(tok, 0) + 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    for tok, _ in ranked[:8]:
        if tok not in {p.lower() for p in phrases}:
            phrases.append(tok)
    return phrases[:12]


async def extract_entities(state: AgentGraphState) -> NodeResult:
    phrases = _noun_phrases(state.problem_text)
    entities: list[dict[str, Any]] = [
        {"id": f"ent-{i + 1}", "name": name, "kind": "entity"} for i, name in enumerate(phrases)
    ]
    if not entities:
        entities = [{"id": "ent-1", "name": "system", "kind": "entity"}]
    return NodeResult(node="extract_entities", output={"entities": entities})


async def draft_assumptions(state: AgentGraphState) -> NodeResult:
    entities = state.entities or (state.data.get("extract_entities") or {}).get("entities", [])
    assumptions: list[dict[str, Any]] = []
    for i, ent in enumerate(entities[:5]):
        name = ent.get("name", f"entity_{i}")
        assumptions.append(
            {
                "id": f"asm-{i + 1}",
                "statement": f"{name} behaves according to declared policy constraints",
                "trust": "asserted",
                "entity_id": ent.get("id"),
            }
        )
    if not assumptions:
        assumptions.append(
            {
                "id": "asm-1",
                "statement": "The modelled environment is closed under stated actions",
                "trust": "asserted",
            }
        )
    return NodeResult(node="draft_assumptions", output={"assumptions": assumptions})


async def propose_goals(state: AgentGraphState) -> NodeResult:
    assumptions = state.assumptions or (state.data.get("draft_assumptions") or {}).get(
        "assumptions", []
    )
    text = state.problem_text.lower()
    goals: list[dict[str, Any]] = []
    if any(k in text for k in ("safe", "safety", "never", "forbid", "must not")):
        goals.append(
            {
                "id": "goal-1",
                "statement": "Safety invariant holds under all allowed transitions",
                "kind": "safety",
            }
        )
    if any(k in text for k in ("reach", "eventually", "complete", "liveness")):
        goals.append(
            {
                "id": "goal-2",
                "statement": "Desired states are eventually reachable",
                "kind": "liveness",
            }
        )
    if not goals:
        goals.append(
            {
                "id": "goal-1",
                "statement": "Specified policy constraints are preserved",
                "kind": "invariant",
            }
        )
    claims = [
        {
            "id": f"claim-{g['id']}",
            "goal_id": g["id"],
            "assumption_ids": [a["id"] for a in assumptions],
            "statement": f"Under assumptions, {g['statement'].lower()}",
        }
        for g in goals
    ]
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
