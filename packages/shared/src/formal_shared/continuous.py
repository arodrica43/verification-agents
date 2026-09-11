"""Continuous certification helpers (Phase 15 foundation)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass(frozen=True)
class ValidityWindow:
    not_before: datetime
    not_after: datetime
    reason: str = "default_policy"


def default_validity(*, days: int = 90) -> ValidityWindow:
    now = datetime.now(UTC)
    return ValidityWindow(not_before=now, not_after=now + timedelta(days=days))


def is_expired(window: ValidityWindow, *, at: datetime | None = None) -> bool:
    moment = at or datetime.now(UTC)
    return moment < window.not_before or moment > window.not_after


def revalidation_due(
    *,
    last_verified_at: datetime,
    max_age_hours: int = 24,
    at: datetime | None = None,
) -> bool:
    """Whether an independent Lean re-check should be scheduled."""
    moment = at or datetime.now(UTC)
    return moment - last_verified_at > timedelta(hours=max_age_hours)


def continuous_cert_plan(certificate: dict[str, Any]) -> dict[str, Any]:
    """Produce a revalidation plan from certificate metadata (no side effects)."""
    verified = certificate.get("verification_environment", {}).get("verified_at")
    return {
        "certificate_id": certificate.get("certificate_id"),
        "requires_lean_recheck": True,
        "last_verified_at": verified,
        "cadence_hours": 24,
        "note": "Continuous certification never skips independent lake verification.",
    }
