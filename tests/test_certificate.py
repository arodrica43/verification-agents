"""Certificate schema and bundle verification tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from formal_certificate_sdk.bundle import verify_bundle
from formal_certificate_service.issuer import issue_demo_certificate
from formal_schemas.assumption import Assumption, AssumptionCategory, AssumptionStatus
from formal_schemas.certificate import (
    Certificate,
    ClaimBlock,
    FormalTheoremRef,
    ProofRef,
    ProvenanceBlock,
    VerificationEnvironment,
)


def _minimal_cert(**overrides):
    base = {
        "certificate_id": "00000000-0000-0000-0000-000000000001",
        "claim": ClaimBlock(id="c1", statement="demo"),
        "formal_theorem": FormalTheoremRef(
            name="T",
            lean_statement="theorem T : True := trivial",
            human_readable="True",
        ),
        "assumptions": [
            Assumption(
                id="a1",
                statement="ok",
                category=AssumptionCategory.USER_ASSERTED,
                status=AssumptionStatus.ACCEPTED,
            )
        ],
        "proof": ProofRef(
            theorem_name="T",
            lean_source_hash="abc",
            verification_report_hash="def",
            contains_sorry=False,
            contains_admit=False,
        ),
        "verification_environment": VerificationEnvironment(
            lean_version="leanprover/lean4:v4.14.0",
            toolchain="leanprover/lean4:v4.14.0",
        ),
        "provenance": ProvenanceBlock(root_hash="0" * 64),
        "root_hash": "0" * 64,
    }
    base.update(overrides)
    return Certificate(**base)


def test_certificate_rejects_unresolved_assumption() -> None:
    with pytest.raises(ValueError, match="unresolved"):
        _minimal_cert(
            assumptions=[
                Assumption(
                    id="bad",
                    statement="?",
                    category=AssumptionCategory.UNRESOLVED,
                    status=AssumptionStatus.ACCEPTED,
                )
            ]
        )


def test_certificate_rejects_sorry() -> None:
    with pytest.raises(ValueError, match="sorry"):
        _minimal_cert(
            proof=ProofRef(
                theorem_name="T",
                lean_source_hash="abc",
                verification_report_hash="def",
                contains_sorry=True,
            )
        )


def test_issue_and_verify_demo_bundle(tmp_path: Path) -> None:
    bundle = issue_demo_certificate(tmp_path / "certificate-demo", lean_verified=False)
    result = verify_bundle(
        bundle,
        signing_secret="dev_signing_secret_change_me_before_prod",
        run_lean=False,
    )
    assert result["ok"] is True
    assert result["certificate_id"]
    assert len(result["root_hash"]) == 64
    assert (bundle / "lean" / "AgentPolicy.lean").exists()
    assert (bundle / "verify.sh").exists()


def test_problem_spec_version() -> None:
    from formal_schemas import ProblemSpec

    spec = ProblemSpec(title="t", description="d")
    assert spec.schema_version == "1.0"
