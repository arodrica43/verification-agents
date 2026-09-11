"""Job queue backends: Redis when available, otherwise filesystem under .data/jobs."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from formal_worker.settings import JobRequest, QueueBackend, WorkerSettings

logger = logging.getLogger(__name__)


class JobQueue(ABC):
    @abstractmethod
    async def enqueue(self, job: JobRequest) -> None: ...

    @abstractmethod
    async def dequeue(self) -> JobRequest | None: ...

    @abstractmethod
    async def close(self) -> None: ...


class FilesystemJobQueue(JobQueue):
    """Simple directory queue: pending/ -> processing/ -> done|failed/."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.pending = root / "pending"
        self.processing = root / "processing"
        self.done = root / "done"
        self.failed = root / "failed"
        for d in (self.pending, self.processing, self.done, self.failed):
            d.mkdir(parents=True, exist_ok=True)

    def _path(self, folder: Path, job_id: str) -> Path:
        return folder / f"{job_id}.json"

    async def enqueue(self, job: JobRequest) -> None:
        path = self._path(self.pending, job.job_id)
        path.write_text(job.model_dump_json(indent=2), encoding="utf-8")

    async def dequeue(self) -> JobRequest | None:
        files = sorted(self.pending.glob("*.json"))
        if not files:
            return None
        src = files[0]
        dest = self.processing / src.name
        src.replace(dest)
        data = json.loads(dest.read_text(encoding="utf-8"))
        return JobRequest.model_validate(data)

    async def mark_done(self, job_id: str, result: dict[str, Any]) -> None:
        src = self._path(self.processing, job_id)
        dest = self._path(self.done, job_id)
        payload = {"job_id": job_id, "result": result}
        dest.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if src.exists():
            src.unlink()

    async def mark_failed(self, job_id: str, error: str) -> None:
        src = self._path(self.processing, job_id)
        dest = self._path(self.failed, job_id)
        dest.write_text(json.dumps({"job_id": job_id, "error": error}, indent=2), encoding="utf-8")
        if src.exists():
            src.unlink()

    async def close(self) -> None:
        return None


class RedisJobQueue(JobQueue):
    def __init__(self, url: str, key: str) -> None:
        try:
            import redis.asyncio as redis
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "redis package not installed; use filesystem queue or pip install redis"
            ) from exc
        self._redis = redis.from_url(url, decode_responses=True)
        self._key = key

    async def enqueue(self, job: JobRequest) -> None:
        await self._redis.rpush(self._key, job.model_dump_json())

    async def dequeue(self) -> JobRequest | None:
        item = await self._redis.lpop(self._key)
        if item is None:
            return None
        return JobRequest.model_validate_json(item)

    async def close(self) -> None:
        await self._redis.aclose()


async def open_queue(settings: WorkerSettings) -> JobQueue:
    backend = settings.queue_backend
    if backend == QueueBackend.FILESYSTEM:
        logger.info("Using filesystem job queue at %s", settings.jobs_dir)
        return FilesystemJobQueue(settings.jobs_dir)

    if backend == QueueBackend.REDIS:
        q = RedisJobQueue(settings.redis_url, settings.redis_queue_key)
        logger.info("Using Redis job queue %s", settings.redis_queue_key)
        return q

    # AUTO: try Redis ping, else filesystem
    try:
        import redis.asyncio as redis

        client = redis.from_url(settings.redis_url, decode_responses=True)
        try:
            await client.ping()
        finally:
            await client.aclose()
        logger.info("Redis available — using Redis job queue")
        return RedisJobQueue(settings.redis_url, settings.redis_queue_key)
    except Exception as exc:  # noqa: BLE001
        logger.info("Redis unavailable (%s) — using filesystem queue at %s", exc, settings.jobs_dir)
        return FilesystemJobQueue(settings.jobs_dir)
