"""Allow `python -m formal_proof_service`."""

from formal_proof_service.app import app

__all__ = ["app"]

if __name__ == "__main__":
    import os

    import uvicorn

    uvicorn.run(
        "formal_proof_service.app:app",
        host=os.environ.get("PROOF_SERVICE_HOST", "0.0.0.0"),
        port=int(os.environ.get("PROOF_SERVICE_PORT", "8001")),
    )
