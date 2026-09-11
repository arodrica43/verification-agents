# ADR-0001: PostgreSQL as Canonical Store

- **Status:** Accepted
- **Date:** 2026-03-20

## Context

The platform needs transactional multi-tenant storage for artifacts, provenance edges, identity, audit events, and (initially) vector embeddings.

## Decision

Use **PostgreSQL** as the single canonical transactional datastore, with **pgvector** for embeddings initially. Represent provenance relations as relational tables. Do not introduce Neo4j (or another graph DB) as a second source of truth in early phases.

## Consequences

- Strong ACID semantics and mature RLS for tenant isolation.
- Simpler operations for SaaS and self-hosted deployments.
- Graph traversal may need careful SQL/recursive CTEs; a graph index abstraction can be added later without changing domain semantics.
