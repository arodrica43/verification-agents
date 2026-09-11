"""Artifact / provenance / audit HTTP routes (authz + RLS)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from formal_api.auth import PrincipalDep, require_org_access
from formal_api.deps import get_db_session
from formal_schemas.enums import (
    ArtifactLifecycle,
    Confidentiality,
    CreatorType,
    ProvenanceRelation,
)
from formal_shared.errors import FormalPlatformError
from formal_store.artifacts import ArtifactCreate
from formal_store.service import ArtifactPlatform

router = APIRouter(prefix="/api/v1", tags=["artifacts"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


class PutArtifactBody(BaseModel):
    organization_id: str
    workspace_id: str
    artifact_type: str
    content: dict[str, Any]
    creator_type: CreatorType = CreatorType.USER
    creator_id: str | None = None
    project_id: str | None = None
    schema_version: str = "1.0"
    lifecycle_state: ArtifactLifecycle = ArtifactLifecycle.DRAFT
    storage_uri: str | None = None
    supersedes: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    confidentiality: Confidentiality = Confidentiality.WORKSPACE


class LinkProvenanceBody(BaseModel):
    organization_id: str
    workspace_id: str
    source_hash: str
    target_hash: str
    relation: ProvenanceRelation
    metadata: dict[str, Any] = Field(default_factory=dict)


@router.post("/artifacts")
async def put_artifact(
    body: PutArtifactBody,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    await require_org_access(
        session,
        organization_id=body.organization_id,
        principal=principal,
        workspace_id=body.workspace_id,
    )
    platform = ArtifactPlatform(session)
    result = await platform.put_artifact(
        ArtifactCreate(
            organization_id=body.organization_id,
            workspace_id=body.workspace_id,
            artifact_type=body.artifact_type,
            content=body.content,
            creator_type=body.creator_type,
            creator_id=body.creator_id or principal.principal_id,
            project_id=body.project_id,
            schema_version=body.schema_version,
            lifecycle_state=body.lifecycle_state,
            storage_uri=body.storage_uri,
            supersedes=body.supersedes,
            metadata=body.metadata,
            confidentiality=body.confidentiality,
        ),
        actor_id=principal.principal_id,
    )
    return {
        "created": result.created,
        "artifact": result.artifact.model_dump(mode="json"),
    }


@router.get("/artifacts/{artifact_id}")
async def get_artifact(
    artifact_id: str,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    platform = ArtifactPlatform(session)
    artifact = await platform.get_artifact(artifact_id)
    if artifact is None:
        raise HTTPException(
            status_code=404, detail={"code": "not_found", "message": "Artifact not found"}
        )
    await require_org_access(
        session,
        organization_id=artifact.organization_id,
        principal=principal,
        workspace_id=artifact.workspace_id,
    )
    return artifact.model_dump(mode="json")


@router.get("/workspaces/{organization_id}/{workspace_id}/artifacts")
async def list_artifacts(
    organization_id: str,
    workspace_id: str,
    session: SessionDep,
    principal: PrincipalDep,
    artifact_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    await require_org_access(
        session,
        organization_id=organization_id,
        principal=principal,
        workspace_id=workspace_id,
    )
    platform = ArtifactPlatform(session)
    items = await platform.artifacts.list_workspace(
        organization_id=organization_id,
        workspace_id=workspace_id,
        artifact_type=artifact_type,
        limit=limit,
    )
    return {"items": [a.model_dump(mode="json") for a in items]}


@router.post("/provenance/edges")
async def link_provenance(
    body: LinkProvenanceBody,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    await require_org_access(
        session,
        organization_id=body.organization_id,
        principal=principal,
        workspace_id=body.workspace_id,
    )
    platform = ArtifactPlatform(session)
    try:
        edge, created = await platform.link(
            organization_id=body.organization_id,
            workspace_id=body.workspace_id,
            source_hash=body.source_hash,
            target_hash=body.target_hash,
            relation=body.relation,
            actor_type=principal.principal_type,
            actor_id=principal.principal_id,
            metadata=body.metadata,
        )
    except FormalPlatformError as exc:
        raise HTTPException(status_code=409, detail=exc.to_dict()) from exc
    return {"created": created, "edge": edge.as_dict()}


@router.get("/workspaces/{organization_id}/{workspace_id}/provenance")
async def get_provenance(
    organization_id: str,
    workspace_id: str,
    session: SessionDep,
    principal: PrincipalDep,
    content_hash: str | None = None,
) -> dict[str, Any]:
    await require_org_access(
        session,
        organization_id=organization_id,
        principal=principal,
        workspace_id=workspace_id,
    )
    platform = ArtifactPlatform(session)
    edges = await platform.provenance.list_edges(
        organization_id=organization_id,
        workspace_id=workspace_id,
        content_hash_value=content_hash,
    )
    graph = await platform.provenance.load_graph(
        organization_id=organization_id,
        workspace_id=workspace_id,
    )
    return {
        "edges": [e.as_dict() for e in edges],
        "sorted_edges": graph.sorted_edge_dicts(),
    }


@router.get("/workspaces/{organization_id}/{workspace_id}/audit")
async def list_audit(
    organization_id: str,
    workspace_id: str,
    session: SessionDep,
    principal: PrincipalDep,
    after_seq: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict[str, Any]:
    await require_org_access(
        session,
        organization_id=organization_id,
        principal=principal,
        workspace_id=workspace_id,
    )
    platform = ArtifactPlatform(session)
    events = await platform.list_audit(
        organization_id=organization_id,
        workspace_id=workspace_id,
        after_seq=after_seq,
        limit=limit,
    )
    return {
        "items": [
            {
                "seq": e.seq,
                "event_id": e.event_id,
                "organization_id": e.organization_id,
                "workspace_id": e.workspace_id,
                "actor_type": e.actor_type,
                "actor_id": e.actor_id,
                "action": e.action,
                "resource_type": e.resource_type,
                "resource_id": e.resource_id,
                "content_hash": e.content_hash,
                "payload": e.payload,
                "created_at": e.created_at.isoformat().replace("+00:00", "Z"),
            }
            for e in events
        ]
    }
