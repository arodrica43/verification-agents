# ADR-0005: Independent Proof Verification

- **Status:** Accepted
- **Date:** 2026-03-20

## Context

LLM-assisted proof generation is untrusted. A proof that “looked good” in the generating session must not be treated as verified.

## Decision

Separate **proof generation/search** from **independent final verification**. Final verification runs in a clean isolated worker with pinned toolchain, no tenant secrets, network disabled by default, and resource limits. Only kernel success in that environment may mark a proof as verified.

## Consequences

- Higher compute cost and operational complexity.
- Certificate issuance depends on verification reports, not agent self-reports.
- Reproducibility bundles must include enough environment metadata to replay checks.
