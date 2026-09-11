# ADR-0004: LangGraph for Agent Orchestration

- **Status:** Accepted
- **Date:** 2026-03-20

## Context

Certification workflows need resumable, typed, human-in-the-loop multi-step agent execution separate from HTTP request lifetimes.

## Decision

Use **LangGraph** for agent orchestration: typed state, subgraphs, checkpoints, interrupts, retries, and tracing. Persist execution checkpoints separately from reusable scientific/formal knowledge artifacts.

## Consequences

- Clear separation of operational vs knowledge state.
- Structured node outputs (Pydantic) are mandatory for critical state.
- Implementation deferred until Phase 5 after the deterministic formal core exists.
