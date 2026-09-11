"""Organization / workspace / project routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from formal_api.auth import PrincipalDep, set_rls_organization
from formal_api.deps import get_db_session
from formal_domain.organization import Role
from formal_shared.errors import FormalPlatformError
from formal_store.identity import (
    IdentityStore,
    MembershipCreate,
    OrganizationCreate,
    ProjectCreate,
    WorkspaceCreate,
)

router = APIRouter(prefix="/api/v1", tags=["identity"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


class OrgBody(BaseModel):
    name: str
    slug: str


class WorkspaceBody(BaseModel):
    organization_id: str
    name: str
    slug: str


class MembershipBody(BaseModel):
    organization_id: str
    principal_id: str
    role: Role = Role.RESEARCHER
    workspace_id: str | None = None
    principal_type: str = "user"


class ProjectBody(BaseModel):
    organization_id: str
    workspace_id: str
    name: str
    description: str = ""


@router.post("/organizations")
async def create_organization(
    body: OrgBody,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    store = IdentityStore(session)
    try:
        org = await store.create_organization(
            OrganizationCreate(name=body.name, slug=body.slug)
        )
        workspace = await store.create_workspace(
            WorkspaceCreate(
                organization_id=org.id,
                name="Main",
                slug="main",
            )
        )
        await store.add_membership(
            MembershipCreate(
                organization_id=org.id,
                principal_id=principal.principal_id,
                principal_type=principal.principal_type,
                role=Role.ORG_OWNER,
                workspace_id=workspace.id,
            )
        )
    except FormalPlatformError as exc:
        raise HTTPException(status_code=409, detail=exc.to_dict()) from exc
    payload = org.model_dump(mode="json")
    payload["default_workspace"] = workspace.model_dump(mode="json")
    return payload


@router.post("/workspaces")
async def create_workspace(
    body: WorkspaceBody,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    store = IdentityStore(session)
    await set_rls_organization(session, body.organization_id)
    try:
        await store.authorize(
            organization_id=body.organization_id,
            principal_id=principal.principal_id,
            allowed={Role.ORG_OWNER, Role.ORG_ADMIN, Role.WORKSPACE_ADMIN},
        )
        ws = await store.create_workspace(
            WorkspaceCreate(
                organization_id=body.organization_id,
                name=body.name,
                slug=body.slug,
            )
        )
    except FormalPlatformError as exc:
        status = 401 if exc.code.value == "unauthorized" else 400
        raise HTTPException(status_code=status, detail=exc.to_dict()) from exc
    return ws.model_dump(mode="json")


@router.post("/memberships")
async def add_membership(
    body: MembershipBody,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    store = IdentityStore(session)
    await set_rls_organization(session, body.organization_id)
    try:
        await store.authorize(
            organization_id=body.organization_id,
            principal_id=principal.principal_id,
            allowed={Role.ORG_OWNER, Role.ORG_ADMIN, Role.WORKSPACE_ADMIN},
        )
        m = await store.add_membership(
            MembershipCreate(
                organization_id=body.organization_id,
                workspace_id=body.workspace_id,
                principal_id=body.principal_id,
                principal_type=body.principal_type,
                role=body.role,
            )
        )
    except FormalPlatformError as exc:
        status = 401 if exc.code.value == "unauthorized" else 400
        raise HTTPException(status_code=status, detail=exc.to_dict()) from exc
    return m.model_dump(mode="json")


@router.post("/projects")
async def create_project(
    body: ProjectBody,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    store = IdentityStore(session)
    await set_rls_organization(session, body.organization_id)
    try:
        await store.authorize(
            organization_id=body.organization_id,
            principal_id=principal.principal_id,
            workspace_id=body.workspace_id,
        )
        project = await store.create_project(
            ProjectCreate(
                organization_id=body.organization_id,
                workspace_id=body.workspace_id,
                name=body.name,
                description=body.description,
            )
        )
    except FormalPlatformError as exc:
        status = 401 if exc.code.value == "unauthorized" else 400
        raise HTTPException(status_code=status, detail=exc.to_dict()) from exc
    return project.model_dump(mode="json")


@router.get("/workspaces/{organization_id}/{workspace_id}/projects")
async def list_projects(
    organization_id: str,
    workspace_id: str,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    store = IdentityStore(session)
    await set_rls_organization(session, organization_id)
    try:
        await store.authorize(
            organization_id=organization_id,
            principal_id=principal.principal_id,
            workspace_id=workspace_id,
        )
    except FormalPlatformError as exc:
        raise HTTPException(status_code=401, detail=exc.to_dict()) from exc
    items = await store.list_projects(
        organization_id=organization_id, workspace_id=workspace_id
    )
    return {"items": [p.model_dump(mode="json") for p in items]}


@router.get("/organizations/{organization_id}/workspaces")
async def list_workspaces(
    organization_id: str,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    store = IdentityStore(session)
    await set_rls_organization(session, organization_id)
    try:
        await store.authorize(
            organization_id=organization_id,
            principal_id=principal.principal_id,
        )
    except FormalPlatformError as exc:
        raise HTTPException(status_code=401, detail=exc.to_dict()) from exc
    items = await store.list_workspaces(organization_id)
    return {"items": [w.model_dump(mode="json") for w in items]}
