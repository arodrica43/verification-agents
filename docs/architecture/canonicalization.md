# Canonicalization Rules

Content hashes are SHA-256 over **canonical JSON** bytes.

## Rules (v1)

1. Encode as UTF-8.
2. Recursively sort object keys.
3. Use compact separators (`,` and `:`), no extra whitespace.
4. Datetimes must be timezone-aware; serialize as ISO-8601 with `Z` for UTC.
5. Reject `NaN` / `Infinity` floats.
6. Enums serialize to their values.
7. UUIDs serialize as lowercase hyphenated strings via `str`.
8. Do not include volatile fields (e.g. request wall-clock) in hashed payloads unless they are part of the artifact semantics.

Implementation: `formal_provenance.canonical`.

## Certificate body hash

When computing a certificate provenance root, hash the certificate body with:

- `root_hash` empty
- `signatures` empty
- `provenance.root_hash` empty

Then compute the provenance root over `(body_hash, sorted edges, sorted artifact hashes)`.
