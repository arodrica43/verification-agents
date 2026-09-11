"""Platform error codes and exceptions."""

from __future__ import annotations

from enum import StrEnum
from typing import Any


class ErrorCode(StrEnum):
    INVALID_PROBLEM_SPEC = "invalid_problem_spec"
    INCOMPLETE_EVIDENCE = "incomplete_evidence"
    UNSUPPORTED_ASSUMPTION = "unsupported_assumption"
    INCONSISTENT_ASSUMPTIONS = "inconsistent_assumptions"
    FORMALIZATION_ERROR = "formalization_error"
    THEOREM_FALSE_OR_UNPROVABLE = "theorem_false_or_unprovable_under_assumptions"
    PROOF_SEARCH_EXHAUSTED = "proof_search_exhausted"
    DEPENDENCY_MISSING = "dependency_missing"
    LEAN_COMPILATION_ERROR = "lean_compilation_error"
    TIMEOUT = "timeout"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    VERIFICATION_ENVIRONMENT_ERROR = "verification_environment_error"
    SECURITY_POLICY_DENIED = "security_policy_denied"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    INTEGRITY_FAILURE = "integrity_failure"
    UNAUTHORIZED = "unauthorized"
    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    INTERNAL = "internal"


class FormalPlatformError(Exception):
    """Base exception with machine-readable code."""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": str(self.code),
            "message": self.message,
            "details": self.details,
        }
