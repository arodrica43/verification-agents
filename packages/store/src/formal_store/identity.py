"""Identity and tenancy persistence (Phase 3)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from formal_domain.organization import Membership, Organization, Role, Workspace
from formal_domain.project import Project, ProjectStatus
from formal_shared.errors import ErrorCode, FormalPlatformError
from formal_shared.ids import new_id
from formal_store.models import MembershipRow, OrganizationRow, ProjectRow, WorkspaceRow


@dataclass(frozen=True)
class OrganizationCreate:
    name: str
    slug: str
    organization_id: str | None = None


@dataclass(frozen=True)
class WorkspaceCreate:
    organization_id: str
    name: str
    slug: str
    workspace_id: str | None = None


@dataclass(frozen=True)
class MembershipCreate:
    organization_id: str
    principal_id: str
    role: Role
    workspace_id: str | None = None
    principal_type: str = "user"
    membership_id: str | None = None


@dataclass(frozen=True)
class ProjectCreate:
    organization_id: str
    workspace_id: str
    name: str
    description: str = ""
    project_id: str | None = None


class IdentityStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_organization(self, spec: OrganizationCreate) -> Organization:
        row = OrganizationRow(
            id=spec.organization_id or new_id(),
            name=spec.name,
            slug=spec.slug,
            created_at=datetime.now(UTC),
        )
        self._session.add(row)
        try:
            async with self._session.begin_nested():
                await self._session.flush()
        except IntegrityError as exc:
            raise FormalPlatformError(
                ErrorCode.CONFLICT,
                f"Organization slug already exists: {spec.slug}",
            ) from exc
        return Organization(
            id=row.id, name=row.name, slug=row.slug, created_at=row.created_at
        )

    async def create_workspace(self, spec: WorkspaceCreate) -> Workspace:
        row = WorkspaceRow(
            id=spec.workspace_id or new_id(),
            organization_id=spec.organization_id,
            name=spec.name,
            slug=spec.slug,
            created_at=datetime.now(UTC),
        )
        self._session.add(row)
        await self._session.flush()
        return Workspace(
            id=row.id,
            organization_id=row.organization_id,
            name=row.name,
            slug=row.slug,
            created_at=row.created_at,
        )

    async def add_membership(self, spec: MembershipCreate) -> Membership:
        row = MembershipRow(
            id=spec.membership_id or new_id(),
            organization_id=spec.organization_id,
            workspace_id=spec.workspace_id,
            principal_id=spec.principal_id,
            principal_type=spec.principal_type,
            role=str(spec.role),
            created_at=datetime.now(UTC),
        )
        self._session.add(row)
        await self._session.flush()
        return Membership(
            id=row.id,
            organization_id=row.organization_id,
            workspace_id=row.workspace_id,
            principal_id=row.principal_id,
            principal_type=row.principal_type,
            role=Role(row.role),
            created_at=row.created_at,
        )

    async def create_project(self, spec: ProjectCreate) -> Project:
        row = ProjectRow(
            id=spec.project_id or new_id(),
            organization_id=spec.organization_id,
            workspace_id=spec.workspace_id,
            name=spec.name,
            description=spec.description,
            status=str(ProjectStatus.ACTIVE),
            created_at=datetime.now(UTC),
        )
        self._session.add(row)
        await self._session.flush()
        return Project(
            id=row.id,
            organization_id=row.organization_id,
            workspace_id=row.workspace_id,
            name=row.name,
            description=row.description,
            status=ProjectStatus(row.status),
            created_at=row.created_at,
        )

    async def get_organization(self, organization_id: str) -> Organization | None:
        row = await self._session.get(OrganizationRow, organization_id)
        if row is None:
            return None
        return Organization(
            id=row.id, name=row.name, slug=row.slug, created_at=row.created_at
        )

    async def list_organizations_for_principal(
        self, principal_id: str
    ) -> list[Organization]:
        stmt = (
            select(OrganizationRow)
            .join(
                MembershipRow,
                MembershipRow.organization_id == OrganizationRow.id,
            )
            .where(MembershipRow.principal_id == principal_id)
            .distinct()
            .order_by(OrganizationRow.name)
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            Organization(
                id=r.id, name=r.name, slug=r.slug, created_at=r.created_at
            )
            for r in rows
        ]

    async def list_workspaces(self, organization_id: str) -> list[Workspace]:
        stmt = select(WorkspaceRow).where(WorkspaceRow.organization_id == organization_id)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            Workspace(
                id=r.id,
                organization_id=r.organization_id,
                name=r.name,
                slug=r.slug,
                created_at=r.created_at,
            )
            for r in rows
        ]

    async def get_project(self, project_id: str) -> Project | None:
        row = await self._session.get(ProjectRow, project_id)
        if row is None:
            return None
        return Project(
            id=row.id,
            organization_id=row.organization_id,
            workspace_id=row.workspace_id,
            name=row.name,
            description=row.description,
            status=ProjectStatus(row.status),
            created_at=row.created_at,
        )

    async def list_projects(
        self, *, organization_id: str, workspace_id: str
    ) -> list[Project]:
        stmt = select(ProjectRow).where(
            ProjectRow.organization_id == organization_id,
            ProjectRow.workspace_id == workspace_id,
        )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [
            Project(
                id=r.id,
                organization_id=r.organization_id,
                workspace_id=r.workspace_id,
                name=r.name,
                description=r.description,
                status=ProjectStatus(r.status),
                created_at=r.created_at,
            )
            for r in rows
        ]

    async def principal_roles(
        self, *, organization_id: str, principal_id: str, workspace_id: str | None = None
    ) -> list[Role]:
        stmt = select(MembershipRow).where(
            MembershipRow.organization_id == organization_id,
            MembershipRow.principal_id == principal_id,
        )
        if workspace_id is not None:
            stmt = stmt.where(
                (MembershipRow.workspace_id.is_(None))
                | (MembershipRow.workspace_id == workspace_id)
            )
        rows = (await self._session.execute(stmt)).scalars().all()
        return [Role(r.role) for r in rows]

    async def authorize(
        self,
        *,
        organization_id: str,
        principal_id: str,
        workspace_id: str | None = None,
        allowed: set[Role] | None = None,
    ) -> list[Role]:
        roles = await self.principal_roles(
            organization_id=organization_id,
            principal_id=principal_id,
            workspace_id=workspace_id,
        )
        if not roles:
            raise FormalPlatformError(
                ErrorCode.UNAUTHORIZED,
                "Principal has no membership in organization/workspace",
                details={
                    "organization_id": organization_id,
                    "workspace_id": workspace_id,
                    "principal_id": principal_id,
                },
            )
        if allowed is not None and not (set(roles) & allowed):
            raise FormalPlatformError(
                ErrorCode.UNAUTHORIZED,
                "Principal lacks required role",
                details={"roles": [str(r) for r in roles]},
            )
        return roles
