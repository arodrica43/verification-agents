"""Minimal API skeleton — health and schema metadata."""

from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Formal Platform API",
    version="0.1.0",
    description="AI-assisted formal reasoning platform API (Phase 0/1).",
)

origins = [
    o.strip()
    for o in os.environ.get("API_CORS_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "api"}


@app.get("/api/v1/meta")
async def meta() -> dict:
    return {
        "api_version": "v1",
        "certificate_schema_version": "1.0",
        "problem_spec_schema_version": "1.0",
        "phase": "0-1",
    }


def main() -> None:
    import uvicorn

    uvicorn.run(
        "formal_api.main:app",
        host=os.environ.get("API_HOST", "0.0.0.0"),
        port=int(os.environ.get("API_PORT", "8000")),
        reload=False,
    )


if __name__ == "__main__":
    main()
