# Roadmap

Statuses: `planned` · `active` · `implemented` · `validated` · `production_ready`

Do not mark `production_ready` unless operational and security requirements are satisfied.

## Phase 0 — Architecture and Contracts

| Field | Value |
|-------|-------|
| Goal | Monorepo, ADRs, schemas, Docker skeleton, CI foundation |
| Status | **implemented** |

## Phase 1 — Deterministic Formal Core

| Field | Value |
|-------|-------|
| Goal | Proof service, Lean demo, certificate export/verify without LLM |
| Status | **implemented** (Lean-gated issuance + CI verify) |
| Limitations | Dev HMAC still default; Ed25519 available; full cgroup isolation later |

## Phase 2 — Artifact and Provenance Platform

| Field | Value |
|-------|-------|
| Goal | PostgreSQL artifacts, hashing, DAG, object storage, audit log |
| Status | **implemented** (upsert, provenance, audit, local/S3 blob adapter) |
| Limitations | S3 adapter needs `boto3` extra; WORM policies not yet enforced |

## Phase 3 — Identity and Multi-Tenancy

| Field | Value |
|-------|-------|
| Goal | Orgs, workspaces, RLS, access tests |
| Status | **implemented** (memberships, authorize(), Postgres RLS policies in Alembic) |
| Limitations | Header/API-key auth (not OIDC); RLS requires `SET app.organization_id` |

## Phase 4 — Minimal SaaS Studio

| Field | Value |
|-------|-------|
| Goal | Projects, problem, assumptions, proof, certificate UI |
| Status | **implemented** (Next.js studio: org/workspace/project + demo certificates) |

## Phase 5 — LangGraph Orchestration

| Field | Value |
|-------|-------|
| Goal | Typed graphs, persistence, HITL interrupts |
| Status | **implemented** (typed `GraphRunner` in agent-core; worker queue) |
| Note | Independent Lean verification remains outside agent graphs |

## Phase 6–8 — NL modelling, AI formalization, proof search

| Field | Value |
|-------|-------|
| Status | **implemented (deterministic scaffolds)** |
| Note | Heuristic modelling + Lean skeletons; proof search still `not_implemented` in proof-service; final verification = lake |

## Phase 9–11 — Knowledge, evidence, certificate security

| Field | Value |
|-------|-------|
| Status | **implemented (foundation)** |
| Note | Retrieval service with tenant pre-filter; evidence validator; Ed25519 signing |

## Phase 12 — Flagship demonstrations

| Field | Value |
|-------|-------|
| Goal | Agent safety certificate + infrastructure-bound certificate |
| Status | **implemented (Lean seeds)** — agent-policy + infrastructure-bound theorems |

## Phase 13–19

| Area | Status |
|------|--------|
| Collaboration / comments | planned |
| Integrations | planned |
| Continuous certification | foundation helpers present |
| Multi-agent research | scaffold via agent-core |
| Enterprise hardening | **partial → first release bar in `docs/operations/production.md`** |
| Ecosystem / SDKs | Python client SDK implemented |
| Advanced trust / transparency logs | planned |

### First production release

Treat `PLATFORM_ENV=production` + `docker-compose.prod.yml` as the deployable configuration: API keys required, Alembic migrations, FORCE RLS, Lean-gated issuance, path-restricted proof service, web+worker images, readiness checks. Remaining gaps before marking all phases `production_ready`: OIDC, full proof-worker cgroup isolation, WORM object-lock, managed backups automation.

## Deliberately postponed

Blockchain/crypto tokens, Neo4j as second canonical DB, complex billing, autonomous agent swarms, custom foundation training.
