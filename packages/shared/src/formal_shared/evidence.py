"""Evidence validation helpers (Phase 10 foundation)."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class EvidenceVerdict(StrEnum):
    SUPPORTS = "supports"
    INSUFFICIENT = "insufficient"
    CONTRADICTS = "contradicts"
    NEEDS_REVIEW = "needs_review"


@dataclass
class EvidenceItem:
    evidence_id: str
    description: str
    content_hash: str
    source: str
    confidence: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AssumptionCheck:
    assumption_id: str
    statement: str
    required: bool = True


@dataclass
class EvidenceValidationResult:
    assumption_id: str
    verdict: EvidenceVerdict
    supporting_evidence_ids: list[str]
    notes: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "assumption_id": self.assumption_id,
            "verdict": str(self.verdict),
            "supporting_evidence_ids": self.supporting_evidence_ids,
            "notes": self.notes,
        }


def validate_evidence_against_assumptions(
    *,
    assumptions: list[AssumptionCheck],
    evidence: list[EvidenceItem],
    min_confidence: float = 0.4,
) -> list[EvidenceValidationResult]:
    """Deterministic heuristic validator (no LLM).

    Marks assumptions as supported when any evidence description shares a
    significant token with the assumption statement and confidence clears the floor.
    """
    results: list[EvidenceValidationResult] = []
    for assumption in assumptions:
        tokens = {t.lower() for t in assumption.statement.replace(",", " ").split() if len(t) > 3}
        supporting: list[str] = []
        for item in evidence:
            ev_tokens = {
                t.lower() for t in item.description.replace(",", " ").split() if len(t) > 3
            }
            if tokens & ev_tokens and item.confidence >= min_confidence:
                supporting.append(item.evidence_id)
        if supporting:
            verdict = EvidenceVerdict.SUPPORTS
            notes = "Keyword overlap with evidence descriptions"
        elif assumption.required:
            verdict = EvidenceVerdict.NEEDS_REVIEW
            notes = "No supporting evidence above confidence floor"
        else:
            verdict = EvidenceVerdict.INSUFFICIENT
            notes = "Optional assumption without supporting evidence"
        results.append(
            EvidenceValidationResult(
                assumption_id=assumption.assumption_id,
                verdict=verdict,
                supporting_evidence_ids=supporting,
                notes=notes,
            )
        )
    return results
