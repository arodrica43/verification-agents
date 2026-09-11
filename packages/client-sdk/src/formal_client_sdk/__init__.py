"""Python HTTP client for the Formal Platform API."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Self

import httpx


@dataclass
class FormalPlatform:
    base_url: str
    api_key: str | None = None
    principal_id: str | None = None
    timeout: float = 60.0
    _client: httpx.Client = field(init=False, repr=False)

    def __post_init__(self) -> None:
        headers: dict[str, str] = {"Accept": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if self.principal_id:
            headers["X-Principal-Id"] = self.principal_id
        self._client = httpx.Client(
            base_url=self.base_url.rstrip("/"),
            headers=headers,
            timeout=self.timeout,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def health(self) -> dict[str, Any]:
        return self._client.get("/health").raise_for_status().json()

    def meta(self) -> dict[str, Any]:
        return self._client.get("/api/v1/meta").raise_for_status().json()

    def create_organization(self, *, name: str, slug: str) -> dict[str, Any]:
        return (
            self._client.post(
                "/api/v1/organizations",
                json={"name": name, "slug": slug},
            )
            .raise_for_status()
            .json()
        )

    def create_workspace(
        self, *, organization_id: str, name: str, slug: str
    ) -> dict[str, Any]:
        return (
            self._client.post(
                "/api/v1/workspaces",
                json={
                    "organization_id": organization_id,
                    "name": name,
                    "slug": slug,
                },
            )
            .raise_for_status()
            .json()
        )

    def create_project(
        self,
        *,
        organization_id: str,
        workspace_id: str,
        name: str,
        description: str = "",
    ) -> dict[str, Any]:
        return (
            self._client.post(
                "/api/v1/projects",
                json={
                    "organization_id": organization_id,
                    "workspace_id": workspace_id,
                    "name": name,
                    "description": description,
                },
            )
            .raise_for_status()
            .json()
        )

    def put_artifact(self, body: dict[str, Any]) -> dict[str, Any]:
        return self._client.post("/api/v1/artifacts", json=body).raise_for_status().json()

    def put_blob(
        self,
        *,
        organization_id: str,
        workspace_id: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> dict[str, Any]:
        files = {"file": ("blob.bin", data, content_type)}
        return (
            self._client.post(
                "/api/v1/blobs",
                params={
                    "organization_id": organization_id,
                    "workspace_id": workspace_id,
                },
                files=files,
            )
            .raise_for_status()
            .json()
        )

    def issue_demo_certificate(
        self, *, require_lean: bool = True, allow_unverified: bool = False
    ) -> dict[str, Any]:
        return (
            self._client.post(
                "/api/v1/certificates/demo/issue",
                json={
                    "require_lean": require_lean,
                    "allow_unverified": allow_unverified,
                },
            )
            .raise_for_status()
            .json()
        )
