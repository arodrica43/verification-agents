"""Organization / workspace / membership entities."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Role(StrEnum):
    ORG_OWNER = "org_owner"
    ORG_ADMIN = "org_admin"
    WORKSPACE_ADMIN = "workspace_admin"
    PROJECT_OWNER = "project_owner"
    RESEARCHER = "researcher"
    FORMAL_ENGINEER = "formal_engineer"
    REVIEWER = "reviewer"
    CERTIFICATE_ISSUER = "certificate_issuer"
    VIEWER = "viewer"
    SERVICE = "service"


class Organization(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    slug: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Workspace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    organization_id: str
    name: str
    slug: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Membership(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    organization_id: str
    workspace_id: str | None = None
    principal_id: str
    principal_type: str  # user | service
    role: Role
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
