# Worker

Async agent / job worker for Formal Platform typed graphs (Phase 5+).

## Role

- Poll a job queue and run agent graphs from `formal-agent-core`
- Default graph: **problem modelling** (`extract_entities → draft_assumptions → propose_goals`)
- Queue: **Redis** when reachable, otherwise a **filesystem** queue under `.data/jobs`

Lean kernel verification remains outside this worker. Proof graphs only emit
`candidate_proof` artifacts with `needs_independent_verification=True`.

## Install

From the monorepo root (uv workspace):

```bash
uv sync --package formal-worker
# optional Redis client:
uv sync --package formal-worker --extra redis
```

## Enqueue a modelling job

```bash
# filesystem queue (default for enqueue)
uv run formal-worker enqueue-modelling --problem "Agent must never leak secrets."

# or module form
uv run python -m formal_worker enqueue-modelling --problem "..." --jobs-dir .data/jobs
```

## Run the worker

```bash
# auto: Redis if ping succeeds, else .data/jobs
uv run formal-worker run

# filesystem only, single job (CI / local)
uv run formal-worker run --backend filesystem --jobs-dir .data/jobs --once
```

Environment (prefix `FORMAL_WORKER_`):

| Variable | Default | Meaning |
|----------|---------|---------|
| `QUEUE_BACKEND` | `auto` | `auto` \| `redis` \| `filesystem` |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `REDIS_QUEUE_KEY` | `formal:jobs` | List key |
| `JOBS_DIR` | `.data/jobs` | Filesystem queue root |
| `POLL_INTERVAL_S` | `0.5` | Idle poll interval |

## Programmatic use

```python
from formal_worker import enqueue_modelling_sync, run_job, JobRequest, JobKind
import asyncio

job = enqueue_modelling_sync("Safety monitor must block forbidden actions.")
result = asyncio.run(run_job(job))
print(result.status, result.state["goals"])
```
