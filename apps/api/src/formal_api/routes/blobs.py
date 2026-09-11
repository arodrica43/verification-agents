"""Blob upload routes (content-addressed object storage)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from formal_api.auth import PrincipalDep, require_org_access
from formal_api.deps import get_db_session
from formal_schemas.enums import CreatorType
from formal_store.artifacts import ArtifactCreate
from formal_store.blobs import BlobStore, create_blob_store_from_env
from formal_store.service import ArtifactPlatform

router = APIRouter(prefix="/api/v1", tags=["blobs"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]
UploadDep = Annotated[UploadFile, File()]

_blob_store: BlobStore | None = None


def get_blob_store() -> BlobStore:
    global _blob_store
    if _blob_store is None:
        _blob_store = create_blob_store_from_env()
    return _blob_store


@router.post("/blobs")
async def upload_blob(
    session: SessionDep,
    principal: PrincipalDep,
    file: UploadDep,
    organization_id: str = Query(...),
    workspace_id: str = Query(...),
) -> dict[str, Any]:
    await require_org_access(
        session,
        organization_id=organization_id,
        principal=principal,
        workspace_id=workspace_id,
    )
    data = await file.read()
    if len(data) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail={"message": "blob too large (25MB max)"})
    content_type = file.content_type or "application/octet-stream"
    store = get_blob_store()
    stored = await store.put(data, content_type=content_type)
    platform = ArtifactPlatform(session)
    result = await platform.put_artifact(
        ArtifactCreate(
            organization_id=organization_id,
            workspace_id=workspace_id,
            artifact_type="blob",
            content={
                "content_hash": stored.content_hash,
                "size_bytes": stored.size_bytes,
                "content_type": stored.content_type,
                "filename": file.filename,
            },
            creator_type=CreatorType.USER,
            creator_id=principal.principal_id,
            storage_uri=stored.uri,
            metadata={"kind": "raw_blob"},
        ),
        actor_id=principal.principal_id,
    )
    return {
        "created": result.created,
        "blob": {
            "content_hash": stored.content_hash,
            "uri": stored.uri,
            "size_bytes": stored.size_bytes,
            "content_type": stored.content_type,
        },
        "artifact": result.artifact.model_dump(mode="json"),
    }


@router.get("/blobs/{content_hash}")
async def download_blob_meta(content_hash: str) -> dict[str, Any]:
    store = get_blob_store()
    exists = await store.exists(content_hash)
    if not exists:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    return {"content_hash": content_hash, "exists": True}
