# Threat Model (Initial)

**Status:** living document — Phases 0–12 foundations  
**Scope:** architecture threats; refine as OIDC and connectors land.

## Assets

- Tenant data (problems, evidence, models, proofs)
- Certificates and signing keys
- Provenance integrity
- Isolation of proof workers
- Service credentials and LLM API keys

## Adversaries

| Actor | Capability |
|-------|------------|
| External anonymous | API abuse, upload malware |
| Malicious tenant user | Cross-tenant IDOR, poisoned artifacts |
| Compromised agent/LLM output | Prompt injection, weakened theorems |
| Compromised proof worker host | Escape, exfiltration |
| Supply-chain attacker | Malicious Lean deps, container images |

## Key threats & mitigations

| ID | Threat | Mitigation (current / planned) |
|----|--------|--------------------------------|
| T01 | Cross-tenant leakage | RLS, authz tests, no shared vector index without filters |
| T02 | Malicious uploads | Type validation, size limits, virus scan (planned), no exec on upload |
| T03 | Prompt injection via documents | Tool allowlists, structured outputs, human review gates |
| T04 | Poisoned knowledge | Trust levels; certified deps only from kernel-verified artifacts |
| T05 | Malicious Lean projects | Isolated workers, no network, timeouts, resource limits |
| T06 | Proof-worker escape | Immutable images, seccomp, ephemeral FS, no cloud metadata |
| T07 | Secret exfil via LLM | Classification flags (`allow_external_llm`), redaction |
| T08 | Authorization bypass | Central authz, RLS defense-in-depth, security tests |
| T09 | Vector-search leakage | Pre-filter by tenant before similarity |
| T10 | Certificate forgery | Content hashes, signatures, independent verify CLI |
| T11 | Artifact tampering | Content addressing, WORM for issued certs (planned) |
| T12 | Dependency supply chain | Pin Lean/mathlib, record digests, SBOM (planned) |
| T13 | Stale evidence | Validity intervals, continuous certification (later) |
| T14 | Vacuous / weakened theorems | Critics + human review (Phases 6–8) |

## Non-goals (Phase 0)

- Full red-team of LLM jailbreaks
- Formal proofs of the platform's own security (Demo A is planned later)
- Public transparency log operation

## Review cadence

Update this document when adding connectors, changing auth, or enabling external model providers.
