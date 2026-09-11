"""Request auth context — API keys required in production."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from formal_api.settings import get_settings
from formal_domain.organization import Role
from formal_shared.errors import FormalPlatformError
from formal_store.identity import IdentityStore


@dataclass(frozen=True)
class Principal:
    principal_id: str
    principal_type: str = "user"


async def get_principal(
    x_principal_id: Annotated[str | None, Header()] = None,
    authorization: Annotated[str | None, Header()] = None,
) -> Principal:
    """Resolve caller identity.

    Production: Bearer API key required; principal from X-Principal-Id (required).
    Development: optional API keys; defaults to DEFAULT_PRINCIPAL_ID.
    """
    settings = get_settings()
    keys = settings.api_key_set
    if settings.is_production or keys:
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail={"code": "unauthorized", "message": "Bearer API key required"},
            )
        token = authorization.removeprefix("Bearer ").strip()
        if token not in keys:
            raise HTTPException(
                status_code=401,
                detail={"code": "unauthorized", "message": "Invalid API key"},
            )

    if settings.is_production:
        if not x_principal_id:
            raise HTTPException(
                status_code=401,
                detail={"code": "unauthorized", "message": "X-Principal-Id required"},
            )
        principal_id = x_principal_id
    else:
        principal_id = x_principal_id or settings.default_principal_id

    return Principal(principal_id=principal_id, principal_type="user")


async def set_rls_organization(session: AsyncSession, organization_id: str) -> None:
    """Set Postgres session GUC used by RLS policies (no-op on SQLite)."""
    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        return
    await session.execute(
        text("SELECT set_config('app.organization_id', :org, true)"),
        {"org": organization_id},
    )


async def require_org_access(
    session: AsyncSession,
    *,
    organization_id: str,
    principal: Principal,
    workspace_id: str | None = None,
    allowed: set[Role] | None = None,
) -> None:
    await set_rls_organization(session, organization_id)
    store = IdentityStore(session)
    try:
        await store.authorize(
            organization_id=organization_id,
            principal_id=principal.principal_id,
            workspace_id=workspace_id,
            allowed=allowed,
        )
    except FormalPlatformError as exc:
        raise HTTPException(status_code=401, detail=exc.to_dict()) from exc


PrincipalDep = Annotated[Principal, Depends(get_principal)]
