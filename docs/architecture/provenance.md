# Provenance Model

## Goals

Provenance is **structural**, not a textual audit log alone.

Every artifact participates in a typed directed acyclic graph (DAG) of relations. Certificates compute a deterministic **provenance root** over the immutable closure of semantically relevant dependencies.

## Relation types (initial)

| Relation | Meaning |
|----------|---------|
| `derived_from` | Produced from another artifact |
| `supports` | Evidence supports an assumption/claim |
| `contradicts` | Explicit contradiction |
| `refines` | More precise version |
| `formalizes` | Natural-language/math → formal artifact |
| `assumes` | Claim/proof depends on assumption |
| `depends_on` | Formal/build dependency |
| `proven_by` | Theorem linked to proof |
| `verified_by` | Proof linked to verification report |
| `generated_by` | Produced by agent/run/tool |
| `reviewed_by` | Human decision artifact |
| `supersedes` | Newer version replaces older |
| `validates` | Validation relationship |
| `invalidates` | Invalidation relationship |
| `extracted_from` | Extraction source |
| `cites` | Citation |
| `imports` | Imported certificate/library |
| `instantiated_from` | Temporal/instance certificate from reusable theorem |

## Content addressing

1. Serialize with **canonical JSON** (UTF-8, sorted keys, no insignificant whitespace variance, RFC 8785-style where applicable).
2. Hash with SHA-256 over the canonical bytes.
3. Never hash non-deterministic JSON (unordered maps without sorting, floating timestamps injected at hash time, etc.).

See `formal_provenance.canonical` for the implementation.

## Provenance root

For a certificate, the root is a Merkle-style digest over the sorted list of `(relation, artifact_content_hash)` pairs in the immutable dependency closure, plus the certificate body hash excluding the root and signatures (to avoid circularity).

Any semantically relevant dependency change **must** change the root.

## Storage

Phase 2 stores nodes/edges relationally in PostgreSQL. A graph-database abstraction may be added later; PostgreSQL remains the initial canonical store (ADR-0001).
