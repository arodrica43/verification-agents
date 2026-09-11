"""Reproducibility: issued bundles must verify without an LLM."""

from __future__ import annotations

from pathlib import Path

from formal_certificate_sdk.bundle import verify_bundle
from formal_certificate_service.issuer import issue_demo_certificate


def test_roundtrip_bundle_reproducible_hashes(tmp_path: Path) -> None:
    bundle = issue_demo_certificate(tmp_path / "cert", lean_verified=False)
    first = verify_bundle(
        bundle,
        signing_secret="dev_signing_secret_change_me_before_prod",
    )
    second = verify_bundle(
        bundle,
        signing_secret="dev_signing_secret_change_me_before_prod",
    )
    assert first["root_hash"] == second["root_hash"]
    assert first["ok"] and second["ok"]
