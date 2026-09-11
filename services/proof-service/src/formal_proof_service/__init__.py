"""Proof service: FormalBackend abstraction and Lean adapter."""

from formal_proof_service.backend import FormalBackend, ProofCheckRequest, ProofCheckResult
from formal_proof_service.lean_backend import LeanLakeBackend

__all__ = [
    "FormalBackend",
    "LeanLakeBackend",
    "ProofCheckRequest",
    "ProofCheckResult",
]
