"""Phase 3: identity tables + Postgres RLS policies.

Revision ID: 0002_phase3_identity
Revises: 0001_phase2_artifacts
Create Date: 2026-09-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_phase3_identity"
down_revision: str | None = "0001_phase2_artifacts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JsonType = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )
    op.create_table(
        "workspaces",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("organization_id", "slug", name="uq_workspaces_org_slug"),
    )
    op.create_index("ix_workspaces_org", "workspaces", ["organization_id"])

    op.create_table(
        "memberships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("workspace_id", sa.String(36), nullable=True),
        sa.Column("principal_id", sa.String(128), nullable=False),
        sa.Column("principal_type", sa.String(32), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_memberships_principal", "memberships", ["organization_id", "principal_id"]
    )
    op.create_index("ix_memberships_workspace", "memberships", ["workspace_id"])

    op.create_table(
        "projects",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_projects_workspace", "projects", ["organization_id", "workspace_id"]
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("organization_id", sa.String(36), nullable=False),
        sa.Column("workspace_id", sa.String(36), nullable=False),
        sa.Column("project_id", sa.String(36), nullable=False),
        sa.Column("graph", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("state_json", JsonType, nullable=False),
        sa.Column("pending_human_review", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_agent_runs_project", "agent_runs", ["organization_id", "project_id"]
    )

    # RLS — only applies on PostgreSQL; no-op semantics on other dialects via IF.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in ("artifacts", "provenance_edges", "audit_events", "projects", "workspaces"):
            op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
            op.execute(
                sa.text(
                    f"""
                    CREATE POLICY tenant_isolation_{table} ON {table}
                    USING (
                      organization_id = current_setting('app.organization_id', true)
                    )
                    WITH CHECK (
                      organization_id = current_setting('app.organization_id', true)
                    )
                    """
                )
            )
        op.execute(sa.text("ALTER TABLE memberships ENABLE ROW LEVEL SECURITY"))
        op.execute(
            sa.text(
                """
                CREATE POLICY tenant_isolation_memberships ON memberships
                USING (organization_id = current_setting('app.organization_id', true))
                WITH CHECK (organization_id = current_setting('app.organization_id', true))
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for table in (
            "artifacts",
            "provenance_edges",
            "audit_events",
            "projects",
            "workspaces",
            "memberships",
        ):
            op.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}"))
            op.execute(sa.text(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY"))

    op.drop_index("ix_agent_runs_project", table_name="agent_runs")
    op.drop_table("agent_runs")
    op.drop_index("ix_projects_workspace", table_name="projects")
    op.drop_table("projects")
    op.drop_index("ix_memberships_workspace", table_name="memberships")
    op.drop_index("ix_memberships_principal", table_name="memberships")
    op.drop_table("memberships")
    op.drop_index("ix_workspaces_org", table_name="workspaces")
    op.drop_table("workspaces")
    op.drop_table("organizations")
