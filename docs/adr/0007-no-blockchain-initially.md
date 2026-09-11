# ADR-0007: No Blockchain in Initial Architecture

- **Status:** Accepted
- **Date:** 2026-03-20

## Context

Distributed trust and public auditability are long-term goals, but cryptocurrency/public blockchain mechanics add complexity, cost, and compliance risk without being required for certificate semantics.

## Decision

**Do not** introduce a blockchain or token system initially. Implement content addressing, cryptographic signatures, Merkle-style roots, and append-only transparency mechanisms. Design interfaces so systems such as Sigstore/Rekor or other anchoring can be added later **without changing the certificate model**.

## Consequences

- Faster path to a trustworthy SaaS MVP.
- Clear upgrade path for Phase 19 advanced trust infrastructure.
- Avoids coupling product value to speculative crypto infrastructure.
