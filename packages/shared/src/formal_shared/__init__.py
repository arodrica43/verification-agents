"""Shared primitives: IDs, hashing, errors, modelling, evidence."""

from formal_shared.errors import ErrorCode, FormalPlatformError
from formal_shared.evidence import (
    AssumptionCheck,
    EvidenceItem,
    EvidenceValidationResult,
    EvidenceVerdict,
    validate_evidence_against_assumptions,
)
from formal_shared.hashing import sha256_bytes, sha256_hex
from formal_shared.ids import new_id
from formal_shared.modelling import claim_to_lean_skeleton, extract_problem_model

__all__ = [
    "AssumptionCheck",
    "ErrorCode",
    "EvidenceItem",
    "EvidenceValidationResult",
    "EvidenceVerdict",
    "FormalPlatformError",
    "claim_to_lean_skeleton",
    "extract_problem_model",
    "new_id",
    "sha256_bytes",
    "sha256_hex",
    "validate_evidence_against_assumptions",
]
