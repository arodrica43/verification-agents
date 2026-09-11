"""Python client SDK scaffold — full surface in later phases."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FormalPlatform:
    """Placeholder client. Real methods arrive with API resources (Phase 2+)."""

    base_url: str
    api_key: str | None = None

    def __repr__(self) -> str:
        return f"FormalPlatform(base_url={self.base_url!r})"
