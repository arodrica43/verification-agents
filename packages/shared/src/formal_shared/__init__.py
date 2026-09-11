"""Shared primitives: IDs, hashing, errors."""

from formal_shared.errors import ErrorCode, FormalPlatformError
from formal_shared.hashing import sha256_bytes, sha256_hex
from formal_shared.ids import new_id

__all__ = [
    "ErrorCode",
    "FormalPlatformError",
    "new_id",
    "sha256_bytes",
    "sha256_hex",
]
