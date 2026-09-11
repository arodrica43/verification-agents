"""Agent graph runs — modelling, formalization, proof, certification."""

from __future__ import annotations

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
        lean_verified=body.lean_verified or (seed.lean_verified if seed else False),
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
    except Exception as exc:  # noqa: BLE001
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
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=400,
            detail={"code": "agent_resume_failed", "message": str(exc)},
        ) from exc
    return _serialize(result)


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
