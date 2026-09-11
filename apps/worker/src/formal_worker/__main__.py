"""CLI entry: ``python -m formal_worker`` or ``formal-worker``."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from formal_worker.app import enqueue_modelling, run_worker
from formal_worker.queue import open_queue
from formal_worker.settings import QueueBackend, WorkerSettings


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Formal Platform agent worker")
    sub = p.add_subparsers(dest="command", required=True)

    run_p = sub.add_parser("run", help="Poll and execute jobs")
    run_p.add_argument("--once", action="store_true", help="Process at most one job then exit")
    run_p.add_argument(
        "--backend",
        choices=[b.value for b in QueueBackend],
        default=None,
        help="Queue backend (default: auto)",
    )
    run_p.add_argument("--jobs-dir", default=None, help="Filesystem queue root")

    enq = sub.add_parser("enqueue-modelling", help="Enqueue a problem modelling job")
    enq.add_argument("--problem", required=True, help="Problem text")
    enq.add_argument("--job-id", default=None)
    enq.add_argument("--backend", choices=[b.value for b in QueueBackend], default="filesystem")
    enq.add_argument("--jobs-dir", default=None)

    return p


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    args = _build_parser().parse_args(argv)
    kwargs: dict[str, object] = {}
    if getattr(args, "backend", None):
        kwargs["queue_backend"] = args.backend
    if getattr(args, "jobs_dir", None):
        kwargs["jobs_dir"] = args.jobs_dir
    if getattr(args, "once", False):
        kwargs["once"] = True
    settings = WorkerSettings(**kwargs)  # type: ignore[arg-type]

    if args.command == "run":
        asyncio.run(run_worker(settings))
        return

    if args.command == "enqueue-modelling":

        async def _enq() -> None:
            queue = await open_queue(settings)
            try:
                job = await enqueue_modelling(
                    queue,
                    problem_text=args.problem,
                    job_id=args.job_id,
                )
                print(job.job_id)
            finally:
                await queue.close()

        asyncio.run(_enq())
        return

    # Unreachable when required=True, but keep explicit.
    print(f"unknown command: {args.command}", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
