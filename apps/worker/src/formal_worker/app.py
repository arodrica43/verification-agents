"""Worker application: enqueue and run Formal Platform agent graphs."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from formal_agent_core import (
    AgentGraphState,
    GraphName,
    GraphRunner,
    InMemoryCheckpointStore,
    RunStatus,
    build_certification_graph,
    build_formalization_graph,
    build_problem_modelling_graph,
    build_proof_graph,
)
from formal_shared.ids import new_id
from formal_worker.queue import FilesystemJobQueue, JobQueue, open_queue
from formal_worker.settings import JobKind, JobRequest, JobResult, WorkerSettings

logger = logging.getLogger(__name__)


def _graph_for(kind: JobKind, interrupt_before: list[str]):
    gates = frozenset(interrupt_before)
    if kind == JobKind.MODELLING:
        return build_problem_modelling_graph(interrupt_before=gates)
    if kind == JobKind.FORMALIZATION:
        return build_formalization_graph()
    if kind == JobKind.PROOF:
        return build_proof_graph()
    if kind == JobKind.CERTIFICATION:
        return build_certification_graph()
    raise ValueError(f"unsupported job kind: {kind}")


def _graph_name(kind: JobKind) -> GraphName:
    return {
        JobKind.MODELLING: GraphName.PROBLEM_MODELLING,
        JobKind.FORMALIZATION: GraphName.FORMALIZATION,
        JobKind.PROOF: GraphName.PROOF,
        JobKind.CERTIFICATION: GraphName.CERTIFICATION,
    }[kind]


async def run_job(job: JobRequest) -> JobResult:
    """Execute a single job against the appropriate typed graph."""
    graph = _graph_for(job.kind, job.interrupt_before)
    run_id = new_id()
    payload = dict(job.payload)
    state = AgentGraphState(
        run_id=run_id,
        organization_id=job.organization_id,
        workspace_id=job.workspace_id,
        project_id=job.project_id,
        graph=_graph_name(job.kind),
        problem_text=job.problem_text or str(payload.get("problem_text", "")),
        claims=list(payload.get("claims", [])),
        assumptions=list(payload.get("assumptions", [])),
        goals=list(payload.get("goals", [])),
        lean_skeleton=payload.get("lean_skeleton"),
        lean_verified=bool(payload.get("lean_verified", False)),
        artifact_ids=list(payload.get("artifact_ids", [])),
    )
    runner = GraphRunner(graph, checkpoints=InMemoryCheckpointStore())
    final = await runner.run(state)
    return JobResult(
        job_id=job.job_id,
        status=str(final.status),
        run_id=final.run_id,
        graph=str(final.graph),
        error=final.error,
        state=final.model_dump(mode="json"),
    )


async def enqueue_modelling(
    queue: JobQueue,
    *,
    problem_text: str,
    job_id: str | None = None,
    organization_id: str = "org-local",
    workspace_id: str = "ws-local",
    project_id: str = "proj-local",
    interrupt_before: list[str] | None = None,
) -> JobRequest:
    job = JobRequest(
        job_id=job_id or new_id(),
        kind=JobKind.MODELLING,
        organization_id=organization_id,
        workspace_id=workspace_id,
        project_id=project_id,
        problem_text=problem_text,
        interrupt_before=list(interrupt_before or []),
    )
    await queue.enqueue(job)
    return job


async def process_one(queue: JobQueue) -> JobResult | None:
    job = await queue.dequeue()
    if job is None:
        return None
    try:
        result = await run_job(job)
        if isinstance(queue, FilesystemJobQueue):
            if result.status == str(RunStatus.FAILED):
                await queue.mark_failed(job.job_id, result.error or "failed")
            else:
                await queue.mark_done(job.job_id, result.model_dump(mode="json"))
        return result
    except Exception as exc:
        logger.exception("job %s failed", job.job_id)
        if isinstance(queue, FilesystemJobQueue):
            await queue.mark_failed(job.job_id, str(exc))
        return JobResult(
            job_id=job.job_id,
            status=str(RunStatus.FAILED),
            run_id="",
            graph=str(_graph_name(job.kind)),
            error=str(exc),
        )


async def run_worker(settings: WorkerSettings | None = None) -> None:
    settings = settings or WorkerSettings()
    queue = await open_queue(settings)
    logger.info(
        "formal-worker started (backend=%s, once=%s)",
        settings.queue_backend,
        settings.once,
    )
    try:
        while True:
            result = await process_one(queue)
            if result is not None:
                logger.info(
                    "job %s -> %s (run_id=%s)",
                    result.job_id,
                    result.status,
                    result.run_id,
                )
                if settings.once:
                    return
            else:
                if settings.once:
                    logger.info("no jobs; exiting (--once)")
                    return
                await asyncio.sleep(settings.poll_interval_s)
    finally:
        await queue.close()


def enqueue_modelling_sync(
    problem_text: str,
    *,
    jobs_dir: str | None = None,
    **kwargs: Any,
) -> JobRequest:
    """Synchronous helper for CLI / scripts (filesystem queue)."""
    from pathlib import Path

    from formal_worker.settings import QueueBackend

    async def _go() -> JobRequest:
        settings = WorkerSettings(
            queue_backend=QueueBackend.FILESYSTEM,
            jobs_dir=Path(jobs_dir) if jobs_dir else Path(".data/jobs"),
        )
        queue = await open_queue(settings)
        try:
            return await enqueue_modelling(queue, problem_text=problem_text, **kwargs)
        finally:
            await queue.close()

    return asyncio.run(_go())
