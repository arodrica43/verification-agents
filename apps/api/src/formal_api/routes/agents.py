"""Agent graph runs — modelling, formalization, proof, certification."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from formal_agent_core import (
    AgentGraphState,
    GraphName,
    GraphRunner,
    RunStatus,
    build_certification_graph,
    build_formalization_graph,
    build_problem_modelling_graph,
    build_proof_graph,
)
from formal_api.auth import PrincipalDep, set_rls_organization
from formal_api.deps import get_db_session
from formal_api.settings import get_settings
from formal_certificate_service import issue_lean_project_certificate
from formal_shared.errors import FormalPlatformError
from formal_store.agents import AgentRunStore, new_run_id
from formal_store.identity import IdentityStore

router = APIRouter(prefix="/api/v1", tags=["agents"])
SessionDep = Annotated[AsyncSession, Depends(get_db_session)]


class StartAgentBody(BaseModel):
    organization_id: str
    workspace_id: str
    project_id: str
    graph: GraphName = GraphName.PROBLEM_MODELLING
    problem_text: str = ""
    # Deprecated: clients cannot self-attest verification. Ignored.
    lean_verified: bool = False
    seed_from_run_id: str | None = None


class ResumeAgentBody(BaseModel):
    updates: dict[str, Any] = Field(default_factory=dict)


class IssueFromRunBody(BaseModel):
    timeout_seconds: int = Field(default=600, ge=30, le=1800)


class DbCheckpointStore:
    def __init__(self, store: AgentRunStore) -> None:
        self._store = store

    async def save(self, state: AgentGraphState) -> None:
        await self._store.upsert_state(
            run_id=state.run_id,
            organization_id=state.organization_id,
            workspace_id=state.workspace_id,
            project_id=state.project_id,
            graph=str(state.graph),
            status=str(state.status),
            state=state.model_dump(mode="json"),
            pending_human_review=state.pending_human_review,
        )

    async def load(self, run_id: str) -> AgentGraphState | None:
        raw = await self._store.get_state(run_id)
        if raw is None:
            return None
        return AgentGraphState.model_validate(raw)


def _build_graph(name: GraphName):
    if name == GraphName.PROBLEM_MODELLING:
        return build_problem_modelling_graph()
    if name == GraphName.FORMALIZATION:
        return build_formalization_graph()
    if name == GraphName.PROOF:
        return build_proof_graph()
    if name == GraphName.CERTIFICATION:
        return build_certification_graph()
    raise HTTPException(
        status_code=400,
        detail={
            "code": "unsupported_graph",
            "message": f"Graph {name} is not runnable via the API yet",
        },
    )


def _serialize(state: AgentGraphState) -> dict[str, Any]:
    return state.model_dump(mode="json")


async def _authorize_project(
    session: AsyncSession,
    *,
    organization_id: str,
    workspace_id: str,
    project_id: str,
    principal_id: str,
) -> None:
    store = IdentityStore(session)
    await set_rls_organization(session, organization_id)
    try:
        await store.authorize(
            organization_id=organization_id,
            principal_id=principal_id,
            workspace_id=workspace_id,
        )
    except FormalPlatformError as exc:
        raise HTTPException(status_code=401, detail=exc.to_dict()) from exc
    project = await store.get_project(project_id)
    if project is None or project.organization_id != organization_id:
        raise HTTPException(
            status_code=404,
            detail={"code": "not_found", "message": "Project not found"},
        )


@router.post("/agents/runs")
async def start_agent_run(
    body: StartAgentBody,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    await _authorize_project(
        session,
        organization_id=body.organization_id,
        workspace_id=body.workspace_id,
        project_id=body.project_id,
        principal_id=principal.principal_id,
    )
    store = AgentRunStore(session)
    seed: AgentGraphState | None = None
    if body.seed_from_run_id:
        raw = await store.get_state(body.seed_from_run_id)
        if raw is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "not_found", "message": "seed run not found"},
            )
        seed = AgentGraphState.model_validate(raw)

    # lean_verified is never client-attested. Proof graph sets it via lake;
    # certification may inherit a prior verified seed.
    inherited_verified = bool(seed.lean_verified) if seed and body.graph == GraphName.CERTIFICATION else False

    state = AgentGraphState(
        run_id=new_run_id(),
        organization_id=body.organization_id,
        workspace_id=body.workspace_id,
        project_id=body.project_id,
        graph=body.graph,
        problem_text=body.problem_text or (seed.problem_text if seed else ""),
        entities=list(seed.entities) if seed else [],
        assumptions=list(seed.assumptions) if seed else [],
        goals=list(seed.goals) if seed else [],
        claims=list(seed.claims) if seed else [],
        lean_skeleton=seed.lean_skeleton if seed else None,
        candidate_proof=seed.candidate_proof if seed else None,
        lean_project_path=seed.lean_project_path if seed else None,
        verification_report=seed.verification_report if seed else None,
        lean_verified=inherited_verified,
        data=dict(seed.data) if seed else {},
        status=RunStatus.PENDING,
    )
    if body.graph == GraphName.PROBLEM_MODELLING and not state.problem_text.strip():
        raise HTTPException(
            status_code=400,
            detail={
                "code": "invalid_request",
                "message": "problem_text is required for problem_modelling",
            },
        )

    runner = GraphRunner(_build_graph(body.graph), checkpoints=DbCheckpointStore(store))
    try:
        result = await runner.run(state)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "agent_run_failed", "message": str(exc)},
        ) from exc
    return _serialize(result)


@router.get("/agents/runs/{run_id}")
async def get_agent_run(
    run_id: str,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    store = AgentRunStore(session)
    raw = await store.get_state(run_id)
    if raw is None:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    state = AgentGraphState.model_validate(raw)
    await _authorize_project(
        session,
        organization_id=state.organization_id,
        workspace_id=state.workspace_id,
        project_id=state.project_id,
        principal_id=principal.principal_id,
    )
    return _serialize(state)


@router.post("/agents/runs/{run_id}/resume")
async def resume_agent_run(
    run_id: str,
    body: ResumeAgentBody,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    store = AgentRunStore(session)
    raw = await store.get_state(run_id)
    if raw is None:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    state = AgentGraphState.model_validate(raw)
    await _authorize_project(
        session,
        organization_id=state.organization_id,
        workspace_id=state.workspace_id,
        project_id=state.project_id,
        principal_id=principal.principal_id,
    )
    runner = GraphRunner(_build_graph(state.graph), checkpoints=DbCheckpointStore(store))
    try:
        result = await runner.resume(run_id, updates=body.updates or None)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail={"code": "agent_resume_failed", "message": str(exc)},
        ) from exc
    return _serialize(result)


@router.post("/agents/runs/{run_id}/certificate")
async def issue_certificate_from_run(
    run_id: str,
    body: IssueFromRunBody,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    """Issue a production-gated certificate from a Lean-verified agent run."""
    store = AgentRunStore(session)
    raw = await store.get_state(run_id)
    if raw is None:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    state = AgentGraphState.model_validate(raw)
    await _authorize_project(
        session,
        organization_id=state.organization_id,
        workspace_id=state.workspace_id,
        project_id=state.project_id,
        principal_id=principal.principal_id,
    )
    if not state.lean_verified:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "lean_not_verified",
                "message": (
                    "Certificate requires lean_verified=True from an independent "
                    "lake build (run the proof graph first)."
                ),
            },
        )
    project_path = state.lean_project_path
    if not project_path or not Path(project_path).exists():
        raise HTTPException(
            status_code=400,
            detail={
                "code": "lean_project_missing",
                "message": "Verified run is missing lean_project_path on disk",
            },
        )

    cfg = get_settings()
    require_lean = True
    allow_unverified = False
    if not cfg.is_production and not cfg.require_lean_for_issuance:
        # Still re-run lake when issuing from an agent run; do not allow unverified.
        require_lean = True
        allow_unverified = False

    ed_priv = (
        bytes.fromhex(cfg.certificate_ed25519_private_key_hex)
        if cfg.certificate_ed25519_private_key_hex
        else None
    )
    theorem = None
    if state.candidate_proof and isinstance(state.candidate_proof, dict):
        theorem = state.candidate_proof.get("theorem")

    title = "Verified claim"
    if state.goals:
        title = str(state.goals[0].get("statement", title))[:200]

    try:
        with tempfile.TemporaryDirectory(prefix="formal-agent-cert-") as tmp:
            bundle = issue_lean_project_certificate(
                Path(project_path),
                Path(tmp) / "certificate-demo",
                title=title,
                description=state.problem_text or "Agent-formalized system",
                entities=state.entities,
                goals=state.goals,
                claims=state.claims,
                assumptions_in=state.assumptions,
                theorem_name=str(theorem) if theorem else None,
                signing_secret=cfg.certificate_signing_secret,
                signing_key_id=cfg.certificate_signing_key_id,
                ed25519_private_key=ed_priv,
                require_lean=require_lean,
                allow_unverified=allow_unverified,
                timeout_seconds=body.timeout_seconds,
            )
            certificate = json.loads((bundle / "certificate.json").read_text(encoding="utf-8"))
            verification = json.loads(
                (bundle / "verification" / "verification.json").read_text(encoding="utf-8")
            )
            return {
                "certificate_id": certificate.get("certificate_id"),
                "root_hash": certificate.get("root_hash"),
                "lean_verified": bool(verification.get("success")),
                "issued_by": principal.principal_id,
                "run_id": run_id,
                "certificate": certificate,
                "verification": verification,
            }
    except FormalPlatformError as exc:
        raise HTTPException(status_code=400, detail=exc.to_dict()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


@router.get("/projects/{project_id}/agent-runs")
async def list_project_agent_runs(
    project_id: str,
    session: SessionDep,
    principal: PrincipalDep,
) -> dict[str, Any]:
    identity = IdentityStore(session)
    project = await identity.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    await _authorize_project(
        session,
        organization_id=project.organization_id,
        workspace_id=project.workspace_id,
        project_id=project.id,
        principal_id=principal.principal_id,
    )
    items = await AgentRunStore(session).list_for_project(
        organization_id=project.organization_id, project_id=project.id
    )
    return {"items": items}
