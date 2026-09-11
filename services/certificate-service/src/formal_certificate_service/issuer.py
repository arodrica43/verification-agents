"""Issue the Phase 1 demo certificate for the agent-policy theorem."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

from formal_certificate_sdk.bundle import BundleInputs, CertificateBundleBuilder
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
from formal_shared.hashing import sha256_hex
from formal_shared.ids import new_id


def _repo_root() -> Path:
    # .../services/certificate-service/src/formal_certificate_service/issuer.py → repo root
    return Path(__file__).resolve().parents[4]


def issue_demo_certificate(
    output_dir: Path | None = None,
    *,
    signing_secret: str | None = None,
    lean_verified: bool = False,
    lean_version: str = "leanprover/lean4:v4.14.0",
) -> Path:
    """Create the manually authored agent-policy certificate bundle."""
    root = _repo_root()
    lean_project = root / "lean" / "examples" / "agent-policy"
    out = output_dir or (
        root / "examples" / "agent-policy-certificate" / "certificate-demo"
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

    verification_report = {
        "success": lean_verified,
        "backend": "lean4",
        "theorem": "AgentPolicy.privileged_action_requires_authorization",
        "note": (
            "Independent lake build must succeed for production issuance. "
            "Demo bundle records lean_verified flag from issuer environment."
        ),
        "checked_at": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
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
                id="ev-spec",
                description="Manually authored AgentPolicy Lean formalization (demo)",
                content_hash=lean_hash,
                assurance_layer=AssuranceLayer.ASSERTED,
            )
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
            lean_version=lean_version,
            toolchain=lean_version,
            verified_at=datetime.now(UTC) if lean_verified else None,
            dependency_manifest_hash=None,
        ),
        provenance=ProvenanceBlock(root_hash="", edges=graph.sorted_edge_dicts()),
    )

    secret = signing_secret or os.environ.get(
        "CERTIFICATE_SIGNING_SECRET", "dev_signing_secret_change_me_before_prod"
    )
    builder = CertificateBundleBuilder()
    return builder.build(
        BundleInputs(
            certificate=cert,
            problem=problem,
            assumptions=[a.model_dump(mode="json") for a in assumptions],
            provenance_graph=graph,
            lean_project_dir=lean_project,
            verification_report=verification_report,
            signing_key_id=os.environ.get("CERTIFICATE_SIGNING_KEY_ID", "dev-key-1"),
            signing_secret=secret,
        ),
        out,
    )
