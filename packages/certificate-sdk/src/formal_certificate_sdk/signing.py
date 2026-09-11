"""Development signing helpers (HMAC). Production will use asymmetric keys."""

from __future__ import annotations

import hashlib
import hmac
from datetime import UTC, datetime

from formal_schemas.certificate import SignatureBlock
from formal_shared.hashing import sha256_hex


def hmac_sign(*, key_id: str, secret: str, payload: bytes) -> SignatureBlock:
    payload_hash = sha256_hex(payload)
    signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return SignatureBlock(
        key_id=key_id,
        algorithm="HMAC-SHA256",
        signature=signature,
        signed_at=datetime.now(UTC),
        signed_payload_hash=payload_hash,
    )


def hmac_verify(*, secret: str, payload: bytes, signature: str) -> bool:
    expected = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
