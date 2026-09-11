"""Phase 3b: FORCE RLS + cover agent_runs.

Revision ID: 0003_force_rls
Revises: 0002_phase3_identity
Create Date: 2026-09-11
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_force_rls"
down_revision: str | None = "0002_phase3_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    tables = (
        "artifacts",
        "provenance_edges",
        "audit_events",
        "projects",
        "workspaces",
        "memberships",
        "agent_runs",
    )
    for table in tables:
        op.execute(sa.text(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY"))
        op.execute(sa.text(f"DROP POLICY IF EXISTS tenant_isolation_{table} ON {table}"))
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


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table in (
        "artifacts",
        "provenance_edges",
        "audit_events",
        "projects",
        "workspaces",
        "memberships",
        "agent_runs",
    ):
        op.execute(sa.text(f"ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY"))
