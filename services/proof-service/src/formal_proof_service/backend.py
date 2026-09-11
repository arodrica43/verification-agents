"""Formal backend protocol — Lean first, other provers later."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from formal_shared.ids import new_id


class ProofCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(default_factory=new_id)
    project_path: str
    toolchain: str | None = None
    timeout_seconds: int = 300
    forbidden_constructs: list[str] = Field(
        default_factory=lambda: ["sorry", "admit", "native_decide"]
    )


class ProofCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    success: bool
    backend: str = "lean4"
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""
    duration_ms: int = 0
    contains_forbidden: bool = False
    forbidden_matches: list[str] = Field(default_factory=list)
    environment: dict[str, Any] = Field(default_factory=dict)
    checked_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


@runtime_checkable
class FormalBackend(Protocol):
    async def check(self, request: ProofCheckRequest) -> ProofCheckResult: ...

    async def inspect(self, project_path: str) -> dict[str, Any]: ...

    async def search_proof(self, *args: Any, **kwargs: Any) -> dict[str, Any]: ...

    async def extract_dependencies(self, project_path: str) -> dict[str, Any]: ...
