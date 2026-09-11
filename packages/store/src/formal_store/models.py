"""SQLAlchemy ORM models for Phase 2–3 persistence."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON

JsonType = JSON().with_variant(JSONB(), "postgresql")
AuditSeq = BigInteger().with_variant(Integer(), "sqlite")


class Base(DeclarativeBase):
    pass


class ArtifactRow(Base):
    __tablename__ = "artifacts"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "workspace_id",
            "content_hash",
            name="uq_artifacts_tenant_content_hash",
        ),
        Index("ix_artifacts_org_workspace", "organization_id", "workspace_id"),
        Index("ix_artifacts_content_hash", "content_hash"),
        Index("ix_artifacts_type", "artifact_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    artifact_type: Mapped[str] = mapped_column(String(128), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0")
    lifecycle_state: Mapped[str] = mapped_column(String(64), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    canonical_content: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False)
    storage_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    creator_type: Mapped[str] = mapped_column(String(32), nullable=False)
    creator_id: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    supersedes: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JsonType, nullable=False, default=dict
    )
    confidentiality: Mapped[str] = mapped_column(String(32), nullable=False)


class ProvenanceEdgeRow(Base):
    __tablename__ = "provenance_edges"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "workspace_id",
            "source_hash",
            "target_hash",
            "relation",
            name="uq_provenance_edge",
        ),
        Index("ix_provenance_source", "organization_id", "workspace_id", "source_hash"),
        Index("ix_provenance_target", "organization_id", "workspace_id", "target_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    target_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    relation: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JsonType, nullable=False, default=dict
    )


class AuditEventRow(Base):
    """Append-only audit log. Application code must never update or delete rows."""

    __tablename__ = "audit_events"
    __table_args__ = (
        Index("ix_audit_org_created", "organization_id", "created_at"),
        Index("ix_audit_resource", "resource_type", "resource_id"),
    )

    seq: Mapped[int] = mapped_column(AuditSeq, primary_key=True, autoincrement=True)
    event_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(128), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class OrganizationRow(Base):
    __tablename__ = "organizations"
    __table_args__ = (UniqueConstraint("slug", name="uq_organizations_slug"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class WorkspaceRow(Base):
    __tablename__ = "workspaces"
    __table_args__ = (
        UniqueConstraint("organization_id", "slug", name="uq_workspaces_org_slug"),
        Index("ix_workspaces_org", "organization_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MembershipRow(Base):
    __tablename__ = "memberships"
    __table_args__ = (
        Index("ix_memberships_principal", "organization_id", "principal_id"),
        Index("ix_memberships_workspace", "workspace_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    workspace_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    principal_id: Mapped[str] = mapped_column(String(128), nullable=False)
    principal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    role: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class ProjectRow(Base):
    __tablename__ = "projects"
    __table_args__ = (Index("ix_projects_workspace", "organization_id", "workspace_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class AgentRunRow(Base):
    """Operational agent run checkpoints (not scientific knowledge artifacts)."""

    __tablename__ = "agent_runs"
    __table_args__ = (Index("ix_agent_runs_project", "organization_id", "project_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    project_id: Mapped[str] = mapped_column(String(36), nullable=False)
    graph: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    state_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    pending_human_review: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CertificateRow(Base):
    """Issued certificate registry (bundle stored in blob store)."""

    __tablename__ = "certificates"
    __table_args__ = (
        Index("ix_certificates_org_project", "organization_id", "project_id"),
        Index("ix_certificates_org_workspace", "organization_id", "workspace_id"),
        Index("ix_certificates_root_hash", "root_hash"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=False)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    root_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    lean_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="issued")
    claim_statement: Mapped[str] = mapped_column(Text, nullable=False, default="")
    theorem_name: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    bundle_content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    bundle_uri: Mapped[str] = mapped_column(Text, nullable=False)
    certificate_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    verification_json: Mapped[dict[str, Any]] = mapped_column(JsonType, nullable=False, default=dict)
    issued_by: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="agent")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
