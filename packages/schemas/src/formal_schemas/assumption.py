"""Assumption schema with provenance categories."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AssumptionCategory(StrEnum):
    FORMALLY_DERIVED = "formally_derived"
    EXTERNALLY_SPECIFIED = "externally_specified"
    EMPIRICALLY_MEASURED = "empirically_measured"
    STATISTICALLY_INFERRED = "statistically_inferred"
    USER_ASSERTED = "user_asserted"
    TRUSTED_SOFTWARE = "trusted_software"
    TRUSTED_HARDWARE = "trusted_hardware"
    IMPORTED_CERTIFICATE = "imported_certificate"
    UNRESOLVED = "unresolved"


class AssumptionStatus(StrEnum):
    DRAFT = "draft"
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    INVALIDATED = "invalidated"


class Assumption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    statement: str
    formal_representation: str | None = None
    category: AssumptionCategory
    evidence_links: list[str] = Field(default_factory=list)
    validation_method: str | None = None
    uncertainty: str | None = None
    validity_interval_start: datetime | None = None
    validity_interval_end: datetime | None = None
    reviewer: str | None = None
    status: AssumptionStatus = AssumptionStatus.DRAFT
    metadata: dict[str, Any] = Field(default_factory=dict)

    def is_production_eligible(self) -> bool:
        """Production certificates may not contain unresolved assumptions."""
        return (
            self.category != AssumptionCategory.UNRESOLVED
            and self.status == AssumptionStatus.ACCEPTED
        )
