"""Phase 4: certificates registry + RLS.

Revision ID: 0004_certificates
Revises: 0003_force_rls
Create Date: 2026-09-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0004_certificates"
down_revision: str | None = "0003_force_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    json_type = sa.JSON().with_variant(postgresql.JSONB(), "postgresql")
    op.create_table(
        "certificates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("run_id", sa.String(length=36), nullable=True),
        sa.Column("root_hash", sa.String(length=64), nullable=False),
        sa.Column("lean_verified", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="issued"),
        sa.Column("claim_statement", sa.Text(), nullable=False, server_default=""),
        sa.Column("theorem_name", sa.String(length=256), nullable=False, server_default=""),
        sa.Column("bundle_content_hash", sa.String(length=64), nullable=False),
        sa.Column("bundle_uri", sa.Text(), nullable=False),
        sa.Column("certificate_json", json_type, nullable=False),
        sa.Column("verification_json", json_type, nullable=False),
        sa.Column("issued_by", sa.String(length=128), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False, server_default="agent"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(
        "ix_certificates_org_project",
        "certificates",
        ["organization_id", "project_id"],
    )
    op.create_index(
        "ix_certificates_org_workspace",
        "certificates",
        ["organization_id", "workspace_id"],
    )
    op.create_index("ix_certificates_root_hash", "certificates", ["root_hash"])

    if bind.dialect.name == "postgresql":
        op.execute(sa.text("ALTER TABLE certificates ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text("ALTER TABLE certificates FORCE ROW LEVEL SECURITY"))
        op.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation_certificates ON certificates"))
        op.execute(
            sa.text(
                """
                CREATE POLICY tenant_isolation_certificates ON certificates
                USING (
                  organization_id = current_setting('app.organization_id', true)
                )
                WITH CHECK (
                  organization_id = current_setting('app.organization_id', true)
                )
                """
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text("DROP POLICY IF EXISTS tenant_isolation_certificates ON certificates"))
        op.execute(sa.text("ALTER TABLE certificates NO FORCE ROW LEVEL SECURITY"))
    op.drop_index("ix_certificates_root_hash", table_name="certificates")
    op.drop_index("ix_certificates_org_workspace", table_name="certificates")
    op.drop_index("ix_certificates_org_project", table_name="certificates")
    op.drop_table("certificates")
