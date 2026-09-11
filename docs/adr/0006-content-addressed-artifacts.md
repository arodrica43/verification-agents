# ADR-0006: Content-Addressed Artifacts

- **Status:** Accepted
- **Date:** 2026-03-20

## Context

Certificates and provenance require integrity: any semantic change must be detectable.

## Decision

Immutable artifacts are **content-addressed** (SHA-256 over canonical serialization). Large blobs live in S3-compatible object storage; PostgreSQL stores metadata, hashes, URIs, and relations. Issued certificates should eventually use WORM/immutability policies.

## Consequences

- Deterministic hashing and canonicalization are core platform code.
- Deduplication and idempotent retries become natural.
- Non-canonical JSON must never be hashed.
