"""Retrieval service — hybrid search with mandatory tenant pre-filter."""

from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from formal_retrieval.store import InMemoryRetrievalIndex, RetrievalDocument

app = FastAPI(
    title="Formal Platform Retrieval Service",
    version="0.1.0",
    description="Tenant-scoped hybrid retrieval (Phase 9).",
)

index = InMemoryRetrievalIndex()


class IndexBody(BaseModel):
    organization_id: str
    workspace_id: str
    document_id: str
    content_hash: str
    text: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    trust_level: str = "research"


class SearchBody(BaseModel):
    organization_id: str
    workspace_id: str
    query: str
    limit: int = Field(default=10, ge=1, le=100)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "retrieval-service"}


@app.post("/index")
async def index_document(body: IndexBody) -> dict[str, Any]:
    doc = RetrievalDocument(
        organization_id=body.organization_id,
        workspace_id=body.workspace_id,
        document_id=body.document_id,
        content_hash=body.content_hash,
        text=body.text,
        metadata=body.metadata,
        trust_level=body.trust_level,
    )
    index.upsert(doc)
    return {"ok": True, "document_id": doc.document_id}


@app.post("/search")
async def search(body: SearchBody) -> dict[str, Any]:
    """Authorization filter is applied BEFORE ranking (threat model T09)."""
    if not body.organization_id or not body.workspace_id:
        raise HTTPException(status_code=400, detail="organization_id and workspace_id required")
    hits = index.search(
        organization_id=body.organization_id,
        workspace_id=body.workspace_id,
        query=body.query,
        limit=body.limit,
    )
    return {"items": [h.as_dict() for h in hits]}


def main() -> None:
    import uvicorn

    uvicorn.run(
        "formal_retrieval.app:app",
        host=os.environ.get("RETRIEVAL_HOST", "0.0.0.0"),
        port=int(os.environ.get("RETRIEVAL_PORT", "8003")),
        reload=False,
    )


if __name__ == "__main__":
    main()
