"""Canonical JSON serialization for content addressing.

Rules (Phase 1):
- UTF-8 encoding
- Objects sorted by key (recursive)
- No insignificant whitespace (separators compact)
- Datetimes serialized as ISO-8601 with timezone
- Reject float NaN/Infinity (non-JSON / non-deterministic across platforms)

These rules intentionally mirror RFC 8785 goals without requiring a full JCS
dependency in Phase 0; upgrade path is documented in docs/architecture/provenance.md.
"""

from __future__ import annotations

import json
import math
from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from formal_shared.hashing import sha256_hex


class CanonicalizationError(ValueError):
    pass


def _normalize(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise CanonicalizationError("NaN/Infinity floats are not canonicalizable")
        # Represent floats via shortest round-trip then parse to ensure stability
        return float(format(value, ".17g"))
    if isinstance(value, datetime):
        if value.tzinfo is None:
            raise CanonicalizationError("Naive datetime is not allowed; use timezone-aware UTC")
        return value.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {k: _normalize(value[k]) for k in sorted(value.keys())}
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    if hasattr(value, "model_dump"):
        return _normalize(value.model_dump(mode="python"))
    raise CanonicalizationError(f"Unsupported type for canonicalization: {type(value)!r}")


def canonical_json_bytes(data: Any) -> bytes:
    """Return deterministic UTF-8 JSON bytes for hashing."""
    normalized = _normalize(data)
    text = json.dumps(
        normalized,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
        allow_nan=False,
    )
    return text.encode("utf-8")


def content_hash(data: Any) -> str:
    """SHA-256 hex digest of canonical JSON bytes."""
    return sha256_hex(canonical_json_bytes(data))
