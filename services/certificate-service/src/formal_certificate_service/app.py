"""FastAPI app for certificate issuance and verification."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from formal_certificate_sdk.bundle import verify_bundle
from formal_certificate_service.issuer import issue_demo_certificate
from formal_shared.errors import FormalPlatformError

app = FastAPI(
    title="Formal Platform Certificate Service",
    version="0.1.0",
    description="Issue and verify independently reproducible formal certificates.",
)


class IssueDemoBody(BaseModel):
    require_lean: bool = True
    allow_unverified: bool = False
    timeout_seconds: int = Field(default=600, ge=1, le=3600)


class VerifyBody(BaseModel):
    bundle_path: str
    run_lean: bool = False
    signing_secret: str | None = None


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "certificate-service"}


@app.post("/certificates/demo/issue")
async def issue_demo(body: IssueDemoBody) -> dict:
    """Issue the agent-policy demo certificate (requires Lean unless allow_unverified)."""
    secret = os.environ.get(
        "CERTIFICATE_SIGNING_SECRET", "dev_signing_secret_change_me_before_prod"
    )
    try:
        with tempfile.TemporaryDirectory(prefix="formal-cert-issue-") as tmp:
            out = Path(tmp) / "certificate-demo"
            bundle = issue_demo_certificate(
                out,
                signing_secret=secret,
                require_lean=body.require_lean,
                allow_unverified=body.allow_unverified,
                timeout_seconds=body.timeout_seconds,
            )
            certificate = json.loads((bundle / "certificate.json").read_text(encoding="utf-8"))
            verification = json.loads(
                (bundle / "verification" / "verification.json").read_text(encoding="utf-8")
            )
            return {
                "certificate_id": certificate.get("certificate_id"),
                "root_hash": certificate.get("root_hash"),
                "lean_verified": bool(verification.get("success")),
                "certificate": certificate,
                "verification": verification,
            }
    except FormalPlatformError as exc:
        raise HTTPException(status_code=400, detail=exc.to_dict()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@app.post("/certificates/verify")
async def verify(body: VerifyBody) -> dict:
    secret = body.signing_secret or os.environ.get("CERTIFICATE_SIGNING_SECRET")
    try:
        return verify_bundle(
            Path(body.bundle_path),
            signing_secret=secret,
            run_lean=body.run_lean,
        )
    except FormalPlatformError as exc:
        raise HTTPException(status_code=400, detail=exc.to_dict()) from exc


def create_app() -> FastAPI:
    return app


def main() -> None:
    import uvicorn

    uvicorn.run(
        "formal_certificate_service.app:app",
        host=os.environ.get("CERTIFICATE_SERVICE_HOST", "0.0.0.0"),
        port=int(os.environ.get("CERTIFICATE_SERVICE_PORT", "8002")),
        reload=False,
    )


if __name__ == "__main__":
    main()
