# Roadmap

Statuses: `planned` · `active` · `implemented` · `validated` · `production_ready`

Do not mark `production_ready` unless operational and security requirements are satisfied.

## Phase 0 — Architecture and Contracts

| Field | Value |
|-------|-------|
| Goal | Monorepo, ADRs, schemas, Docker skeleton, CI foundation |
| Status | **implemented** |
| Tests | Schema / provenance / certificate unit tests passing |
| Security | Threat model draft |
| Limitations | No running multi-tenant API persistence yet |

## Phase 1 — Deterministic Formal Core

| Field | Value |
|-------|-------|
| Goal | Proof service, Lean demo, certificate export/verify without LLM |
| Status | **active** (vertical slice working) |
| Dependencies | Phase 0 schemas/provenance |
| Test status | Bundle verify + forbidden-construct checks; Lean CI job present |
| Limitations | Demo certificate may be issued with `lean_verified=false` if host lacks `lake`; production issuance must require independent lake success |

## Phase 2 — Artifact and Provenance Platform

| Field | Value |
|-------|-------|
| Goal | PostgreSQL artifacts, hashing, DAG, object storage, audit log |
| Status | planned |

## Phase 3 — Identity and Multi-Tenancy

| Field | Value |
|-------|-------|
| Goal | Orgs, workspaces, RLS, access tests |
| Status | planned |

## Phase 4 — Minimal SaaS Studio

| Field | Value |
|-------|-------|
| Goal | Projects, problem, assumptions, proof, certificate UI |
| Status | planned |

## Phase 5 — LangGraph Orchestration

| Field | Value |
|-------|-------|
| Goal | Typed graphs, persistence, HITL interrupts |
| Status | planned |

## Phase 6–8 — NL modelling, AI formalization, proof search

| Field | Value |
|-------|-------|
| Status | planned |
| Note | Final verification remains independent Lean check |

## Phase 9–11 — Knowledge, evidence, certificate security

| Field | Value |
|-------|-------|
| Status | planned |

## Phase 12 — Flagship demonstrations

| Field | Value |
|-------|-------|
| Goal | Agent safety certificate + infrastructure-bound certificate |
| Status | planned (Lean seed theorem started in Phase 1) |

## Phase 13–19

Collaboration, integrations, continuous certification, multi-agent research, enterprise hardening, ecosystem, advanced trust — all **planned**. See product vision in repository root instructions / architecture docs.

## Deliberately postponed

Blockchain/crypto tokens, Neo4j as second canonical DB, complex billing, autonomous agent swarms, custom foundation training.
