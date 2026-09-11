"""Certificate list / get / download APIs."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from formal_api.auth import PrincipalDep, set_rls_organization
from formal_api.deps import get_db_session
from formal_api.routes.blobs import get_blob_store
from formal_shared.errors import FormalPlatformError
from formal_store.certificates import CertificateStore
from formal_store.identity import IdentityStore

router = APIRouter(prefix="/api/v1", tags=["certificates"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


async def _authorize_org(
    session: AsyncSession, *, organization_id: str, principal_id: str
) -> None:
    store = IdentityStore(session)
    await set_rls_organization(session, organization_id)
    try:
        await store.authorize(organization_id=organization_id, principal_id=principal_id)
    except FormalPlatformError as exc:
        raise HTTPException(status_code=401, detail=exc.to_dict()) from exc


@router.get("/organizations/{organization_id}/certificates")
async def list_org_certificates(
    organization_id: str,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    await _authorize_org(
        session, organization_id=organization_id, principal_id=principal.principal_id
    )
    items = await CertificateStore(session).list_for_organization(
        organization_id=organization_id
    )
    return {"items": items}


@router.get("/projects/{project_id}/certificates")
async def list_project_certificates(
    project_id: str,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    identity = IdentityStore(session)
    project = await identity.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    await _authorize_org(
        session,
        organization_id=project.organization_id,
        principal_id=principal.principal_id,
    )
    items = await CertificateStore(session).list_for_project(
        organization_id=project.organization_id, project_id=project.id
    )
    return {"items": items, "project_id": project.id}


@router.get("/certificates/{certificate_id}")
async def get_certificate(
    certificate_id: str,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    # Load without RLS first to discover org, then re-authorize.
    store = CertificateStore(session)
    # Temporarily clear RLS by reading via identity-less path: fetch then auth.
    from sqlalchemy import select

    from formal_store.models import CertificateRow

    row = (
        await session.execute(
            select(CertificateRow).where(CertificateRow.id == certificate_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    await _authorize_org(
        session,
        organization_id=row.organization_id,
        principal_id=principal.principal_id,
    )
    record = await store.get(certificate_id)
    if record is None:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    return record


@router.get("/certificates/{certificate_id}/bundle")
async def download_certificate_bundle(
    certificate_id: str,
    session: SessionDep,
    principal: PrincipalDep,
) -> Response:
    from sqlalchemy import select

    from formal_store.models import CertificateRow

    row = (
        await session.execute(
            select(CertificateRow).where(CertificateRow.id == certificate_id)
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    await _authorize_org(
        session,
        organization_id=row.organization_id,
        principal_id=principal.principal_id,
    )
    try:
        data = await get_blob_store().get(row.bundle_content_hash, prefix="certificates")
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "bundle_missing", "message": "Certificate bundle blob not found"},
        ) from exc
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="certificate-{certificate_id}.zip"'
        },
    )
