"""Agent graph runs — modelling, formalization, proof, certification."""

from __future__ import annotations

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
from formal_api.certificate_issue import issue_and_persist_from_lean_project
from formal_api.deps import get_db_session
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


async def _issue_from_state(
    session: AsyncSession,
    state: AgentGraphState,
    *,
    principal_id: str,
    timeout_seconds: int = 600,
) -> dict[str, Any]:
    if not state.lean_verified:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "lean_not_verified",
                "message": (
                    "Certificate requires lean_verified=True from an independent "
                    "lake build (run Verify with Lean first)."
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
    theorem = None
    if state.candidate_proof and isinstance(state.candidate_proof, dict):
        theorem = state.candidate_proof.get("theorem")
    title = "Verified claim"
    if state.goals:
        title = str(state.goals[0].get("statement", title))[:200]
    try:
        return await issue_and_persist_from_lean_project(
            session,
            lean_project=Path(project_path),
            organization_id=state.organization_id,
            workspace_id=state.workspace_id,
            project_id=state.project_id,
            run_id=state.run_id,
            issued_by=principal_id,
            title=title,
            description=state.problem_text or "Agent-formalized system",
            entities=state.entities,
            goals=state.goals,
            claims=state.claims,
            assumptions=state.assumptions,
            theorem_name=str(theorem) if theorem else None,
            timeout_seconds=timeout_seconds,
        )
    except FormalPlatformError as exc:
        raise HTTPException(status_code=400, detail=exc.to_dict()) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"message": str(exc)}) from exc


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

    inherited_verified = (
        bool(seed.lean_verified) if seed and body.graph == GraphName.CERTIFICATION else False
    )

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

    if (
        body.graph == GraphName.CERTIFICATION
        and result.status == RunStatus.COMPLETED
        and result.certificate_ready
        and result.lean_verified
    ):
        issued = await _issue_from_state(
            session, result, principal_id=principal.principal_id
        )
        result = result.model_copy(
            update={
                "certificate_id": issued["certificate_id"],
                "issued_certificate": issued,
            }
        )
        await store.upsert_state(
            run_id=result.run_id,
            organization_id=result.organization_id,
            workspace_id=result.workspace_id,
            project_id=result.project_id,
            graph=str(result.graph),
            status=str(result.status),
            state=result.model_dump(mode="json"),
            pending_human_review=result.pending_human_review,
        )
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
    """Issue and persist a Lean-verified certificate from an agent run."""
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
    issued = await _issue_from_state(
        session,
        state,
        principal_id=principal.principal_id,
        timeout_seconds=body.timeout_seconds,
    )
    state = state.model_copy(
        update={
            "certificate_ready": True,
            "certificate_id": issued["certificate_id"],
            "issued_certificate": issued,
        }
    )
    await store.upsert_state(
        run_id=state.run_id,
        organization_id=state.organization_id,
        workspace_id=state.workspace_id,
        project_id=state.project_id,
        graph=str(state.graph),
        status=str(state.status),
        state=state.model_dump(mode="json"),
        pending_human_review=state.pending_human_review,
    )
    return issued


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
