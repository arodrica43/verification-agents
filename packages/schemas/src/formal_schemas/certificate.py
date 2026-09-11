"""Versioned certificate schema (certificate_version 1.0)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from formal_schemas.assumption import Assumption, AssumptionCategory


class CertificateState(StrEnum):
    VALID = "valid"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"


class AssuranceLayer(StrEnum):
    """Explicit assurance layers — never present as equivalent."""

    FORMALLY_VERIFIED = "formally_verified"
    EXTERNALLY_VALIDATED = "externally_validated"
    ASSERTED = "asserted"


class FormalTheoremRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    lean_statement: str
    human_readable: str
    backend: str = "lean4"
    source_path: str | None = None


class VerificationEnvironment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lean_version: str
    lake_version: str | None = None
    mathlib_rev: str | None = None
    toolchain: str
    worker_image_digest: str | None = None
    dependency_manifest_hash: str | None = None
    verified_at: datetime | None = None


class CertificateValidity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: CertificateState = CertificateState.VALID
    not_before: datetime | None = None
    not_after: datetime | None = None
    conditions: list[str] = Field(default_factory=list)
    invalidation_reason: str | None = None


class SignatureBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key_id: str
    algorithm: str
    signature: str
    signed_at: datetime
    signed_payload_hash: str


class ScopeBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = ""
    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)


class ClaimBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    statement: str
    assurance_summary: str = (
        "Formal verification applies only to the Lean theorem under listed assumptions; "
        "empirical fit of assumptions to reality is separately recorded."
    )


class ProofRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theorem_name: str
    lean_source_hash: str
    verification_report_hash: str
    contains_sorry: bool = False
    contains_admit: bool = False


class EvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    description: str
    content_hash: str
    assurance_layer: AssuranceLayer


class FormalModelRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    description: str
    content_hash: str
    lean_module: str | None = None


class ProvenanceBlock(BaseModel):
    model_config = ConfigDict(extra="forbid")

    root_hash: str
    edges: list[dict[str, str]] = Field(default_factory=list)
    artifact_hashes: list[str] = Field(default_factory=list)


class Certificate(BaseModel):
    """Stable certificate schema v1.0."""

    model_config = ConfigDict(extra="forbid")

    certificate_version: str = "1.0"
    certificate_id: str
    claim: ClaimBlock
    scope: ScopeBlock = Field(default_factory=ScopeBlock)
    formal_theorem: FormalTheoremRef
    assumptions: list[Assumption] = Field(default_factory=list)
    evidence: list[EvidenceSummary] = Field(default_factory=list)
    formal_model: FormalModelRef | None = None
    proof: ProofRef
    verification_environment: VerificationEnvironment
    provenance: ProvenanceBlock
    validity: CertificateValidity = Field(default_factory=CertificateValidity)
    signatures: list[SignatureBlock] = Field(default_factory=list)
    root_hash: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def reject_unresolved_assumptions(self) -> Certificate:
        unresolved = [
            a.id
            for a in self.assumptions
            if a.category == AssumptionCategory.UNRESOLVED
        ]
        if unresolved:
            raise ValueError(
                f"Production certificates must not contain unresolved assumptions: {unresolved}"
            )
        if self.proof.contains_sorry or self.proof.contains_admit:
            raise ValueError(
                "Production certificates must not contain sorry/admit unless explicitly declared "
                "as trusted assumptions under policy (forbidden in v1.0 issuance)."
            )
        return self
