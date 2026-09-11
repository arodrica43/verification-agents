# ADR-0003: Lean 4 as First Formal Backend

- **Status:** Accepted
- **Date:** 2026-03-20

## Context

The platform needs a kernel-checked formal system. Multiple provers may be needed long-term.

## Decision

Adopt **Lean 4** (with mathlib and Lake) as the first formal backend. Interact via an abstract `FormalBackend` protocol. Prefer LeanDojo-v2 / Pantograph for search/interaction layers. Keep Lean-specific details out of unrelated domain schemas where avoidable.

## Consequences

- Strong ecosystem and mathlib reuse.
- Proof workers must pin toolchains and isolate execution.
- Future Isabelle/Coq/SMT backends plug into the same abstraction.
