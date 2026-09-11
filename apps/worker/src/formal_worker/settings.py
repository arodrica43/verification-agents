"""Formal Platform async agent worker settings and job models."""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class QueueBackend(StrEnum):
    REDIS = "redis"
    FILESYSTEM = "filesystem"
    AUTO = "auto"


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="FORMAL_WORKER_", extra="ignore")

    queue_backend: QueueBackend = QueueBackend.AUTO
    redis_url: str = "redis://localhost:6379/0"
    redis_queue_key: str = "formal:jobs"
    jobs_dir: Path = Path(".data/jobs")
    poll_interval_s: float = 0.5
    once: bool = False
    """Process at most one job then exit (useful for tests / CI)."""


class JobKind(StrEnum):
    MODELLING = "modelling"
    FORMALIZATION = "formalization"
    PROOF = "proof"
    CERTIFICATION = "certification"


class JobRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    kind: JobKind = JobKind.MODELLING
    organization_id: str = "org-local"
    workspace_id: str = "ws-local"
    project_id: str = "proj-local"
    problem_text: str = ""
    payload: dict[str, Any] = Field(default_factory=dict)
    interrupt_before: list[str] = Field(default_factory=list)


class JobResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    job_id: str
    status: str
    run_id: str
    graph: str
    error: str | None = None
    state: dict[str, Any] = Field(default_factory=dict)
