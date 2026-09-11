"""FastAPI app for the proof service."""

from __future__ import annotations

import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from formal_proof_service.backend import ProofCheckRequest, ProofCheckResult
from formal_proof_service.lean_backend import LeanLakeBackend
from formal_shared.errors import FormalPlatformError
from formal_shared.ids import new_id

app = FastAPI(
    title="Formal Platform Proof Service",
    version="0.1.0",
    description="Isolated Lean verification — independent of agent generation paths.",
)

backend = LeanLakeBackend()


class CheckBody(BaseModel):
    project_path: str
    toolchain: str | None = None
    timeout_seconds: int = Field(default=300, ge=1, le=3600)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "proof-service"}


@app.post("/proofs/check", response_model=ProofCheckResult)
async def proofs_check(body: CheckBody) -> ProofCheckResult:
    request = ProofCheckRequest(
        request_id=new_id(),
        project_path=body.project_path,
        toolchain=body.toolchain,
        timeout_seconds=body.timeout_seconds,
    )
    try:
        return await backend.check(request)
    except FormalPlatformError as exc:
        raise HTTPException(status_code=400, detail=exc.to_dict()) from exc


@app.post("/proofs/replay", response_model=ProofCheckResult)
async def proofs_replay(body: CheckBody) -> ProofCheckResult:
    """Independent replay — same check API; keep generation off this process in production."""
    return await proofs_check(body)


@app.get("/proofs/inspect")
async def proofs_inspect(project_path: str) -> dict:
    return await backend.inspect(project_path)


@app.post("/proofs/search")
async def proofs_search() -> dict:
    return await backend.search_proof()


def create_app() -> FastAPI:
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "formal_proof_service.app:app",
        host=os.environ.get("PROOF_SERVICE_HOST", "0.0.0.0"),
        port=int(os.environ.get("PROOF_SERVICE_PORT", "8001")),
        reload=False,
    )
