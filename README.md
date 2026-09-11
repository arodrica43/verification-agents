# Formal Platform

Production-oriented SaaS platform for **AI-assisted formal reasoning over real-world systems**.

Users describe applied problems, attach evidence, collaborate with AI agents, and obtain **independently reproducible formal certificates**. Lean kernel verification is authoritative; LLMs may propose artifacts but never substitute for verification.

## Epistemic model

```text
E ⊨ A          evidence supports assumptions (platform-recorded justification)
Lean ⊢ A → G   formal implication checked by the Lean kernel
```

A certificate always exposes this trust boundary. Proving a theorem about a formal model is **not** the same as proving that reality satisfies that model.

## Repository layout

```text
apps/          web (Next.js), API (FastAPI), worker
services/      proof-service, retrieval-service, certificate-service
packages/      domain, schemas, provenance, store, certificate-sdk, …
lean/          Lean 4 libraries, examples, templates
infra/         docker, terraform, kubernetes, observability
docs/          architecture, ADRs, threat model, roadmap
examples/      flagship demos
tests/         integration, e2e, security, reproducibility
```

## Current phase

Phases **0–3** and formal-core demos are implemented.  
Studio (Phase 4), agents (5), modelling/evidence/retrieval (6–11), and Demo B Lean seed (12) are in-tree.  
Later enterprise phases remain incremental — see [`docs/roadmap.md`](docs/roadmap.md).

## Quick start

### Prerequisites

- Docker + Docker Compose
- Python 3.12+
- [uv](https://docs.astral.sh/uv/) (recommended)
- Lean 4 (for local proof verification outside containers)

### Local stack

```bash
cp .env.example .env
docker compose up -d
```

### Production stack

```bash
# Fill strong secrets first — see docs/operations/production.md
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
curl -fsS http://localhost:8000/ready
```

This starts PostgreSQL (pgvector), MinIO, Redis, API, proof-service, and certificate-service.

### Python packages

```bash
uv sync --all-extras
uv run pytest
uv run formal-cert --help
```

### Verify the demo certificate bundle

```bash
uv run formal-cert verify examples/agent-policy-certificate/certificate-demo
```

### Lean demo theorem

```bash
cd lean/examples/agent-policy
lake build
```

## Trust principles (non-negotiable)

1. Only the Lean kernel decides that a theorem is proved.
2. Certificates are exportable and independently verifiable without an LLM.
3. Everything important is a typed, versioned artifact with structured provenance.
4. Multi-tenancy is enforced at storage boundaries (RLS), not only in app code.
5. No blockchain/cryptocurrency in the initial architecture — content addressing, signatures, and transparency logs first.

## Documentation

| Document | Path |
|----------|------|
| Architecture | [`docs/architecture/overview.md`](docs/architecture/overview.md) |
| Roadmap | [`docs/roadmap.md`](docs/roadmap.md) |
| **Production ops** | [`docs/operations/production.md`](docs/operations/production.md) |
| Certificate semantics | [`docs/formal-model/certificate-semantics.md`](docs/formal-model/certificate-semantics.md) |
| Provenance | [`docs/architecture/provenance.md`](docs/architecture/provenance.md) |
| Threat model | [`docs/threat-model/threat-model.md`](docs/threat-model/threat-model.md) |
| ADRs | [`docs/adr/`](docs/adr/) |
| Local development | [`docs/development/local-setup.md`](docs/development/local-setup.md) |

## License

Apache-2.0 (see `LICENSE`).
