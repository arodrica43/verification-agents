"""Identifier helpers."""

from __future__ import annotations

import uuid


def new_id() -> str:
    """Return a new UUID4 string (globally safe identifier)."""
    return str(uuid.uuid4())
