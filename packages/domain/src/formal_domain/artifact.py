"""Artifact domain entity."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from formal_schemas.enums import ArtifactLifecycle, Confidentiality, CreatorType


class Artifact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    organization_id: str
    workspace_id: str
    project_id: str | None = None
    artifact_type: str
    schema_version: str = "1.0"
    lifecycle_state: ArtifactLifecycle = ArtifactLifecycle.DRAFT
    content_hash: str
    canonical_content_reference: str | None = None
    storage_uri: str | None = None
    creator_type: CreatorType
    creator_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    supersedes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    confidentiality: Confidentiality = Confidentiality.WORKSPACE

    def is_trusted_formal_dependency(self) -> bool:
        return self.lifecycle_state in {
            ArtifactLifecycle.VERIFIED,
            ArtifactLifecycle.CERTIFIED,
        }
