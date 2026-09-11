# Architecture Overview

**Status:** Phase 2 persistence foundation  
**Last updated:** 2026-09-11

## Purpose

The Formal Platform turns applied claims about real-world systems into **auditable epistemic objects**: structured problems, evidence-backed assumptions, formal models, Lean theorems, independently verified proofs, and signed certificates.

## Trust boundary (north star)

```text
Evidence E  ⊨  Assumptions A
Lean        ⊢  A → G
Certificate binds (E, A, G) with provenance, hashes, and signatures
```

Never conflate:

| Layer | Meaning |
|-------|---------|
| Kernel-verified | Lean proved `A → G` |
| Externally validated | Evidence/tooling supports premises in `A` |
| Asserted | Human/system accepted a premise without formal/empirical closure |

## System context

```text
┌─────────────┐     ┌─────────────┐     ┌──────────────────┐
│  Web Studio │────▶│  API / Auth │────▶│  PostgreSQL+RLS  │
│  (Next.js)  │     │  (FastAPI)  │     │  + pgvector      │
└─────────────┘     └──────┬──────┘     └──────────────────┘
                           │
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
    ┌────────────┐  ┌────────────┐  ┌────────────────┐
    │ Agent      │  │ Proof      │  │ Object store   │
    │ workers    │  │ workers    │  │ (S3 / MinIO)   │
    │ (LangGraph)│  │ (isolated) │  │ content-addr.  │
    └────────────┘  └────────────┘  └────────────────┘
```

## Core packages

| Package | Responsibility |
|---------|----------------|
| `formal-schemas` | Versioned Pydantic schemas (ProblemSpec, Certificate, …) |
| `formal-domain` | Domain entities, lifecycle, trust levels |
| `formal-provenance` | Canonicalization, hashing, DAG relations, roots |
| `formal-certificate-sdk` | Bundle export/verify CLI |
| `formal-store` | PostgreSQL artifacts, provenance edges, append-only audit |
| `formal-shared` | IDs, hashing, errors, observability helpers |
| `formal-agent-core` | Typed graph runner + HITL (LangGraph optional; Phase 5+) |
| `formal-client-sdk` | Python client (later) |

## Services

| Service | Role |
|---------|------|
| `apps/api` | External REST API, authz, orchestration triggers |
| `apps/worker` | Async jobs / LangGraph runners |
| `services/proof-service` | Isolated Lean check/search/replay |
| `services/certificate-service` | Issue, sign, export, invalidate |
| `services/retrieval-service` | Hybrid knowledge retrieval (Phase 9) |

## Artifact model

Every meaningful development is a typed artifact with:

- tenant scope (`organization_id`, `workspace_id`)
- content hash over **canonical** serialization
- lifecycle state
- confidentiality classification
- typed provenance edges

Operational LangGraph checkpoints are **not** scientific knowledge and are stored separately.

## Formal backend abstraction

Lean 4 is the first `FormalBackend`. Domain layers avoid Lean-specific fields where avoidable so Isabelle/Coq/SMT can be added later.

Final verification always runs in a **clean** environment, independent of the process that generated a proof.

## Multi-tenancy

- First-class `organization_id` / `workspace_id` columns
- PostgreSQL Row-Level Security
- Retrieval (including vectors) must apply authorization **before** returning results

## Decentralization readiness (no blockchain initially)

Phase 1–3 provide:

- SHA-256 content addressing
- signed certificate roots
- Merkle-style provenance roots
- append-only audit events

Interfaces allow later transparency logs / external anchoring without changing the certificate semantic model.

## Related documents

- [Provenance](provenance.md)
- [Certificate semantics](../formal-model/certificate-semantics.md)
- [Threat model](../threat-model/threat-model.md)
- [Roadmap](../roadmap.md)
- ADRs in `docs/adr/`
