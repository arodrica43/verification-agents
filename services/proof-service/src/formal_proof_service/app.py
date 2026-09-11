"""Proof service with path allowlisting for production."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from formal_proof_service.backend import ProofCheckRequest, ProofCheckResult
from formal_proof_service.lean_backend import LeanLakeBackend
from formal_shared.errors import FormalPlatformError
from formal_shared.ids import new_id

app = FastAPI(
    title="Formal Platform Proof Service",
    version="1.0.0",
    description="Isolated Lean verification — independent of agent generation paths.",
)

backend = LeanLakeBackend()


class CheckBody(BaseModel):
    project_path: str
    toolchain: str | None = None
    timeout_seconds: int = Field(default=300, ge=1, le=3600)


def _allowed_roots() -> list[Path]:
    raw = os.environ.get("PROOF_ALLOWED_ROOTS", "")
    return [Path(p.strip()).resolve() for p in raw.split(",") if p.strip()]


def _assert_path_allowed(project_path: str) -> Path:
    resolved = Path(project_path).resolve()
    roots = _allowed_roots()
    platform_env = os.environ.get("PLATFORM_ENV", "development").lower()
    if not roots:
        if platform_env == "production":
            raise HTTPException(
                status_code=403,
                detail={"code": "security_policy_denied", "message": "PROOF_ALLOWED_ROOTS required"},
            )
        return resolved
    for root in roots:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise HTTPException(
        status_code=403,
        detail={
            "code": "security_policy_denied",
            "message": "project_path outside allowed roots",
            "project_path": str(resolved),
        },
    )


def _require_internal_token(authorization: str | None) -> None:
    token = os.environ.get("PROOF_SERVICE_TOKEN", "").strip()
    if not token:
        return
    if not authorization or authorization != f"Bearer {token}":
        raise HTTPException(status_code=401, detail={"code": "unauthorized"})


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "proof-service"}


@app.post("/proofs/check", response_model=ProofCheckResult)
async def proofs_check(
    body: CheckBody,
    authorization: str | None = Header(default=None),
) -> ProofCheckResult:
    _require_internal_token(authorization)
    project_path = str(_assert_path_allowed(body.project_path))
    request = ProofCheckRequest(
        request_id=new_id(),
        project_path=project_path,
        toolchain=body.toolchain,
        timeout_seconds=body.timeout_seconds,
    )
    try:
        return await backend.check(request)
    except FormalPlatformError as exc:
        raise HTTPException(status_code=400, detail=exc.to_dict()) from exc


@app.post("/proofs/replay", response_model=ProofCheckResult)
async def proofs_replay(
    body: CheckBody,
    authorization: str | None = Header(default=None),
) -> ProofCheckResult:
    return await proofs_check(body, authorization=authorization)


@app.get("/proofs/inspect")
async def proofs_inspect(
    project_path: str,
    authorization: str | None = Header(default=None),
) -> dict:
    _require_internal_token(authorization)
    path = str(_assert_path_allowed(project_path))
    return await backend.inspect(path)


@app.post("/proofs/search")
async def proofs_search(authorization: str | None = Header(default=None)) -> dict:
    _require_internal_token(authorization)
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
