# Certificate Semantics

## What a certificate asserts

A Formal Platform certificate asserts:

1. **FORMALLY VERIFIED** — Lean verified theorem `A → G` (or equivalent) under a pinned toolchain.
2. **EXTERNALLY VALIDATED / ASSERTED** — Why the platform believes evidence and human decisions support assumptions `A` (explicit assurance classes; never conflated with kernel verification).
3. **INTEGRITY** — Content hashes, provenance root, and signatures bind the bundle.

It does **not** assert that the physical world necessarily satisfies the model.

## Assurance classes for assumptions

| Category | Meaning |
|----------|---------|
| `formally_derived` | Derived from other verified formal artifacts |
| `externally_specified` | Trusted external specification |
| `empirically_measured` | Measurement with recorded method/uncertainty |
| `statistically_inferred` | Statistical inference with recorded method |
| `user_asserted` | Explicit human assertion |
| `trusted_software` | Trusted software component |
| `trusted_hardware` | Trusted hardware component |
| `imported_certificate` | Premise from another certificate |
| `unresolved` | **Forbidden** in production certificates |

## Certificate states

`valid` · `expired` · `invalidated` · `revoked` · `superseded`

Invalidation retains the original artifact for audit.

## Bundle layout

```text
certificate-<id>/
├── certificate.json
├── manifest.json
├── problem.json
├── assumptions.json
├── provenance.json
├── evidence/manifest.json
├── lean/…
├── verification/verification.json
├── signatures/
└── verify.sh
```

Independent verification must not require an LLM.

## Schema version

Current schema: `certificate_version = "1.0"` (see `formal_schemas.certificate`).
