# ADR-0002: Typed Provenance DAG

- **Status:** Accepted
- **Date:** 2026-03-20

## Context

Audit logs alone cannot express scientific/formal dependency structure needed for certificates, impact analysis, and knowledge reuse.

## Decision

Model provenance as a **typed directed acyclic graph** with explicit relation types (`derived_from`, `assumes`, `proven_by`, …). Nodes are content-addressed where meaningful. Certificates expose a deterministic provenance root over the immutable dependency closure.

## Consequences

- Provenance is queryable and enforceable in certificate issuance.
- Requires canonical serialization rules and careful cycle prevention.
- Enables later impact analysis when evidence or libraries are invalidated.
