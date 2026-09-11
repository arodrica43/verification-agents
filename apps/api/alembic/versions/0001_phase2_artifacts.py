"""Phase 2: artifacts, provenance edges, append-only audit events.

Revision ID: 0001_phase2_artifacts
Revises:
Create Date: 2026-09-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_phase2_artifacts"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JsonType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "artifacts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("artifact_type", sa.String(length=128), nullable=False),
        sa.Column("schema_version", sa.String(length=32), nullable=False),
        sa.Column("lifecycle_state", sa.String(length=64), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("canonical_content", JsonType, nullable=False),
        sa.Column("storage_uri", sa.Text(), nullable=True),
        sa.Column("creator_type", sa.String(length=32), nullable=False),
        sa.Column("creator_id", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("supersedes", sa.String(length=36), nullable=True),
        sa.Column("metadata", JsonType, nullable=False),
        sa.Column("confidentiality", sa.String(length=32), nullable=False),
        sa.UniqueConstraint(
            "organization_id",
            "workspace_id",
            "content_hash",
            name="uq_artifacts_tenant_content_hash",
        ),
    )
    op.create_index("ix_artifacts_org_workspace", "artifacts", ["organization_id", "workspace_id"])
    op.create_index("ix_artifacts_content_hash", "artifacts", ["content_hash"])
    op.create_index("ix_artifacts_type", "artifacts", ["artifact_type"])

    op.create_table(
        "provenance_edges",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("source_hash", sa.String(length=64), nullable=False),
        sa.Column("target_hash", sa.String(length=64), nullable=False),
        sa.Column("relation", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("metadata", JsonType, nullable=False),
        sa.UniqueConstraint(
            "organization_id",
            "workspace_id",
            "source_hash",
            "target_hash",
            "relation",
            name="uq_provenance_edge",
        ),
    )
    op.create_index(
        "ix_provenance_source",
        "provenance_edges",
        ["organization_id", "workspace_id", "source_hash"],
    )
    op.create_index(
        "ix_provenance_target",
        "provenance_edges",
        ["organization_id", "workspace_id", "target_hash"],
    )

    op.create_table(
        "audit_events",
        sa.Column("seq", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("event_id", sa.String(length=36), nullable=False),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=True),
        sa.Column("actor_type", sa.String(length=32), nullable=False),
        sa.Column("actor_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=128), nullable=False),
        sa.Column("resource_type", sa.String(length=128), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("payload", JsonType, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("event_id", name="uq_audit_event_id"),
    )
    op.create_index("ix_audit_org_created", "audit_events", ["organization_id", "created_at"])
    op.create_index("ix_audit_resource", "audit_events", ["resource_type", "resource_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_resource", table_name="audit_events")
    op.drop_index("ix_audit_org_created", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_index("ix_provenance_target", table_name="provenance_edges")
    op.drop_index("ix_provenance_source", table_name="provenance_edges")
    op.drop_table("provenance_edges")
    op.drop_index("ix_artifacts_type", table_name="artifacts")
    op.drop_index("ix_artifacts_content_hash", table_name="artifacts")
    op.drop_index("ix_artifacts_org_workspace", table_name="artifacts")
    op.drop_table("artifacts")
