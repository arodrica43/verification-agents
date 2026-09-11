"""Certificate signing: HMAC (dev) and Ed25519 (production-ready path)."""

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


def ed25519_generate_keypair() -> tuple[bytes, bytes]:
    """Return (private_key_raw_32, public_key_raw_32)."""
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    private = Ed25519PrivateKey.generate()
    return (
        private.private_bytes_raw(),
        private.public_key().public_bytes_raw(),
    )


def ed25519_sign(*, key_id: str, private_key: bytes, payload: bytes) -> SignatureBlock:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    key = Ed25519PrivateKey.from_private_bytes(private_key)
    sig = key.sign(payload).hex()
    return SignatureBlock(
        key_id=key_id,
        algorithm="Ed25519",
        signature=sig,
        signed_at=datetime.now(UTC),
        signed_payload_hash=sha256_hex(payload),
    )


def ed25519_verify(*, public_key: bytes, payload: bytes, signature: str) -> bool:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    key = Ed25519PublicKey.from_public_bytes(public_key)
    try:
        key.verify(bytes.fromhex(signature), payload)
        return True
    except (InvalidSignature, ValueError):
        return False
