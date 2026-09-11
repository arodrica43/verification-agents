"""Issue the Phase 1 demo certificate for the agent-policy theorem."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from formal_certificate_sdk.bundle import BundleInputs, CertificateBundleBuilder
from formal_proof_service.backend import ProofCheckRequest, ProofCheckResult
from formal_proof_service.lean_backend import LeanLakeBackend
from formal_provenance.canonical import content_hash
from formal_provenance.graph import ProvenanceEdge, ProvenanceGraph
from formal_schemas.assumption import Assumption, AssumptionCategory, AssumptionStatus
from formal_schemas.certificate import (
    AssuranceLayer,
    Certificate,
    ClaimBlock,
    EvidenceSummary,
    FormalModelRef,
    FormalTheoremRef,
    ProofRef,
    ProvenanceBlock,
    ScopeBlock,
    VerificationEnvironment,
)
from formal_schemas.enums import ProvenanceRelation
from formal_schemas.problem_spec import (
    ClaimItem,
    GoalItem,
    ProblemScope,
    ProblemSpec,
    SystemEntity,
    SystemModel,
)
from formal_shared.errors import ErrorCode, FormalPlatformError
from formal_shared.hashing import sha256_hex
from formal_shared.ids import new_id


def _repo_root() -> Path:
    # .../services/certificate-service/src/formal_certificate_service/issuer.py → repo root
    return Path(__file__).resolve().parents[4]


def _lean_project_dir() -> Path:
    """Resolve the agent-policy Lean project in editable, installed, or container layouts."""
    env = os.environ.get("LEAN_PROJECT_DIR")
    if env:
        path = Path(env)
        if path.exists():
            return path
        raise FormalPlatformError(
            ErrorCode.DEPENDENCY_MISSING,
            f"LEAN_PROJECT_DIR does not exist: {path}",
        )
    candidates = [
        _repo_root() / "lean" / "examples" / "agent-policy",
        Path("/app/lean/examples/agent-policy"),
        Path("/lean/examples/agent-policy"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FormalPlatformError(
        ErrorCode.DEPENDENCY_MISSING,
        "Could not locate lean/examples/agent-policy; set LEAN_PROJECT_DIR",
    )


def _check_path_for_verifier(lean_project: Path) -> str:
    """Path visible to the verifier process (may differ under Docker)."""
    return os.environ.get("LEAN_CHECK_PROJECT_PATH", str(lean_project))


def _run_independent_lean_check(lean_project: Path, *, timeout_seconds: int = 600) -> ProofCheckResult:
    """Independent lake build: remote proof-service when opted in, else local backend."""
    proof_url = os.environ.get("PROOF_SERVICE_URL", "").rstrip("/")
    remote = os.environ.get("CERTIFICATE_REMOTE_PROOF", "").lower() in {"1", "true", "yes"}
    project_path = _check_path_for_verifier(lean_project)
    if remote and proof_url:
        return _check_via_proof_service(proof_url, project_path, timeout_seconds=timeout_seconds)
    backend = LeanLakeBackend()
    request = ProofCheckRequest(
        project_path=str(lean_project),
        timeout_seconds=timeout_seconds,
    )
    return asyncio.run(backend.check(request))


def _check_via_proof_service(
    proof_url: str,
    project_path: str,
    *,
    timeout_seconds: int,
) -> ProofCheckResult:
    import httpx

    url = f"{proof_url}/proofs/check"
    try:
        response = httpx.post(
            url,
            json={
                "project_path": project_path,
                "timeout_seconds": timeout_seconds,
            },
            timeout=timeout_seconds + 30,
        )
    except httpx.RequestError as exc:
        raise FormalPlatformError(
            ErrorCode.VERIFICATION_ENVIRONMENT_ERROR,
            f"Proof service unreachable at {proof_url}: {exc}",
        ) from exc
    if response.status_code >= 400:
        detail = response.json() if response.headers.get("content-type", "").startswith(
            "application/json"
        ) else {"body": response.text}
        raise FormalPlatformError(
            ErrorCode.VERIFICATION_ENVIRONMENT_ERROR,
            f"Proof service check failed with HTTP {response.status_code}",
            details=detail if isinstance(detail, dict) else {"detail": detail},
        )
    return ProofCheckResult.model_validate(response.json())


def issue_demo_certificate(
    output_dir: Path | None = None,
    *,
    signing_secret: str | None = None,
    signing_key_id: str | None = None,
    ed25519_private_key: bytes | None = None,
    ed25519_public_key: bytes | None = None,
    require_lean: bool = True,
    allow_unverified: bool = False,
    run_lean: bool | None = None,
    lean_version: str | None = None,
    proof_result: ProofCheckResult | None = None,
    timeout_seconds: int = 600,
) -> Path:
    """Create the agent-policy certificate bundle.

    Production semantics: independent Lean verification must succeed unless
    ``allow_unverified`` is explicitly set (tests / offline scaffolding only).

    ``run_lean`` defaults to True when verification is required, and False when
    ``allow_unverified`` is set for offline unit tests. Pass ``run_lean=True``
    with ``allow_unverified=True`` to attempt lake and still issue on failure.
    """
    if require_lean is False and allow_unverified is False:
        raise ValueError("require_lean=False is only valid together with allow_unverified=True")
    if run_lean is None:
        run_lean = not allow_unverified

    root = _repo_root()
    lean_project = _lean_project_dir()
    out = output_dir or (
        root / "examples" / "agent-policy-certificate" / "certificate-demo"
    )
    # When installed as a site package, prefer an explicit output_dir from callers.
    if output_dir is None and not out.parent.exists():
        raise FormalPlatformError(
            ErrorCode.DEPENDENCY_MISSING,
            "output_dir is required when the repository examples/ tree is not available",
        )

    toolchain = lean_version
    if toolchain is None:
        tc_path = lean_project / "lean-toolchain"
        toolchain = (
            tc_path.read_text(encoding="utf-8").strip()
            if tc_path.exists()
            else "leanprover/lean4:v4.14.0"
        )

    check = proof_result
    if check is None and run_lean:
        try:
            check = _run_independent_lean_check(lean_project, timeout_seconds=timeout_seconds)
        except FormalPlatformError:
            if require_lean:
                raise
            check = None

    lean_verified = bool(check and check.success and not check.contains_forbidden)
    if not lean_verified and not allow_unverified:
        detail: dict[str, Any] = {}
        if check is not None:
            detail = {
                "exit_code": check.exit_code,
                "forbidden_matches": check.forbidden_matches,
                "stderr_tail": (check.stderr or "")[-2000:],
            }
        raise FormalPlatformError(
            ErrorCode.LEAN_COMPILATION_ERROR
            if check and not check.contains_forbidden
            else ErrorCode.VERIFICATION_ENVIRONMENT_ERROR,
            "Independent Lean verification failed; certificate not issued",
            details=detail,
        )

    problem = ProblemSpec(
        title="Privileged action requires authorization",
        description=(
            "An agent workflow must not complete a privileged action unless "
            "authorization conditions are satisfied."
        ),
        system=SystemModel(
            entities=[
                SystemEntity(
                    id="ent-agent",
                    name="AgentRuntime",
                    description="Agent execution runtime under policy control",
                )
            ]
        ),
        goals=[
            GoalItem(
                id="goal-1",
                statement="Prove privileged execution implies authorization under policy",
            )
        ],
        claims=[
            ClaimItem(
                id="claim-1",
                statement=(
                    "If policySatisfied(s) and privilegedActionExecuted(s), then authorized(s)"
                ),
            )
        ],
        scope=ProblemScope(
            in_scope=["authorization implication under explicit policy predicate"],
            out_of_scope=[
                "proof that a particular deployed agent satisfies policySatisfied in reality"
            ],
        ),
    )

    assumptions = [
        Assumption(
            id="asm-policy-model",
            statement="System state is accurately modeled by AgentPolicy.SystemState",
            formal_representation="AgentPolicy.SystemState",
            category=AssumptionCategory.USER_ASSERTED,
            status=AssumptionStatus.ACCEPTED,
            validation_method="human_review",
            reviewer="demo-issuer",
        ),
        Assumption(
            id="asm-policy-predicate",
            statement=(
                "policySatisfied means privileged execution is only allowed when authorized=true"
            ),
            formal_representation="AgentPolicy.policySatisfied",
            category=AssumptionCategory.EXTERNALLY_SPECIFIED,
            status=AssumptionStatus.ACCEPTED,
            validation_method="specification_review",
            reviewer="demo-issuer",
        ),
    ]

    lean_src = (lean_project / "AgentPolicy.lean").read_bytes()
    lean_hash = sha256_hex(lean_src)
    problem_hash = content_hash(problem.model_dump(mode="json"))
    assumption_hashes = [content_hash(a.model_dump(mode="json")) for a in assumptions]

    checked_at = (
        check.checked_at.astimezone(UTC).isoformat().replace("+00:00", "Z")
        if check is not None
        else datetime.now(UTC).isoformat().replace("+00:00", "Z")
    )
    verification_report: dict[str, Any] = {
        "success": lean_verified,
        "backend": "lean4",
        "theorem": "AgentPolicy.privileged_action_requires_authorization",
        "checked_at": checked_at,
        "duration_ms": check.duration_ms if check else None,
        "exit_code": check.exit_code if check else None,
        "contains_forbidden": check.contains_forbidden if check else None,
        "forbidden_matches": check.forbidden_matches if check else [],
        "environment": check.environment if check else {},
        "note": (
            "Independent lake build succeeded; Lean kernel verification recorded."
            if lean_verified
            else (
                "Issued with allow_unverified=True; lake success was not required. "
                "Production issuance must set require_lean=True."
            )
        ),
    }
    verification_hash = content_hash(verification_report)

    graph = ProvenanceGraph()
    graph.add_node(problem_hash)
    graph.add_node(lean_hash)
    graph.add_node(verification_hash)
    for h in assumption_hashes:
        graph.add_node(h)
        graph.add_edge(
            ProvenanceEdge(
                source_hash=lean_hash,
                target_hash=h,
                relation=ProvenanceRelation.ASSUMES,
            )
        )
    graph.add_edge(
        ProvenanceEdge(
            source_hash=lean_hash,
            target_hash=problem_hash,
            relation=ProvenanceRelation.FORMALIZES,
        )
    )
    graph.add_edge(
        ProvenanceEdge(
            source_hash=verification_hash,
            target_hash=lean_hash,
            relation=ProvenanceRelation.VERIFIED_BY,
        )
    )

    proof_assurance = (
        AssuranceLayer.FORMALLY_VERIFIED if lean_verified else AssuranceLayer.ASSERTED
    )
    env_toolchain = (check.environment.get("toolchain") if check else None) or toolchain

    cert = Certificate(
        certificate_id=new_id(),
        claim=ClaimBlock(
            id="claim-1",
            statement=(
                "Under the AgentPolicy model, privileged action execution with a satisfied "
                "policy implies authorization."
            ),
        ),
        scope=ScopeBlock(
            description="Formal model only; empirical policy compliance is out of scope",
            in_scope=["Lean theorem privileged_action_requires_authorization"],
            out_of_scope=["Live agent telemetry binding"],
        ),
        formal_theorem=FormalTheoremRef(
            name="AgentPolicy.privileged_action_requires_authorization",
            lean_statement=(
                "theorem privileged_action_requires_authorization "
                "(s : SystemState) (hpolicy : policySatisfied s) "
                "(hexec : s.privilegedActionExecuted = true) : authorized s"
            ),
            human_readable=(
                "If the policy is satisfied and a privileged action executed, "
                "then the actor was authorized."
            ),
            source_path="AgentPolicy.lean",
        ),
        assumptions=assumptions,
        evidence=[
            EvidenceSummary(
                id="ev-lean-proof",
                description=(
                    "Independent lake build of AgentPolicy.lean"
                    if lean_verified
                    else "Manually authored AgentPolicy Lean formalization (unverified demo)"
                ),
                content_hash=lean_hash,
                assurance_layer=proof_assurance,
            ),
            EvidenceSummary(
                id="ev-assumptions",
                description="Accepted modeling assumptions (not Lean-proved)",
                content_hash=content_hash([a.model_dump(mode="json") for a in assumptions]),
                assurance_layer=AssuranceLayer.ASSERTED,
            ),
        ],
        formal_model=FormalModelRef(
            id="model-agent-policy",
            description="Minimal authorization system state",
            content_hash=lean_hash,
            lean_module="AgentPolicy",
        ),
        proof=ProofRef(
            theorem_name="AgentPolicy.privileged_action_requires_authorization",
            lean_source_hash=lean_hash,
            verification_report_hash=verification_hash,
            contains_sorry=False,
            contains_admit=False,
        ),
        verification_environment=VerificationEnvironment(
            lean_version=env_toolchain,
            toolchain=env_toolchain,
            verified_at=datetime.now(UTC) if lean_verified else None,
            dependency_manifest_hash=None,
        ),
        provenance=ProvenanceBlock(root_hash="", edges=graph.sorted_edge_dicts()),
    )

    secret = signing_secret or os.environ.get(
        "CERTIFICATE_SIGNING_SECRET", "dev_signing_secret_change_me_before_prod"
    )
    key_id = signing_key_id or os.environ.get("CERTIFICATE_SIGNING_KEY_ID", "dev-key-1")
    builder = CertificateBundleBuilder()
    return builder.build(
        BundleInputs(
            certificate=cert,
            problem=problem,
            assumptions=[a.model_dump(mode="json") for a in assumptions],
            provenance_graph=graph,
            lean_project_dir=lean_project,
            verification_report=verification_report,
            signing_key_id=key_id,
            signing_secret=secret,
            ed25519_private_key=ed25519_private_key,
            ed25519_public_key=ed25519_public_key,
        ),
        out,
    )
