"""End-to-end smoke test against a running Formal Platform API."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from typing import Any


def _request(
    method: str,
    url: str,
    *,
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, Any]:
    body = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={
            "Accept": "application/json",
            **({"Content-Type": "application/json"} if data is not None else {}),
            **(headers or {}),
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            payload = json.loads(raw) if raw else {"body": raw}
        except json.JSONDecodeError:
            payload = {"body": raw}
        return exc.code, payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--principal", default="smoke-user")
    parser.add_argument(
        "--require-lean",
        action="store_true",
        help="Fail if demo certificate is not Lean-verified",
    )
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    headers = {"X-Principal-Id": args.principal}

    status, health = _request("GET", f"{base}/health")
    assert status == 200 and health.get("status") == "ok", health
    print("health: ok")

    status, ready = _request("GET", f"{base}/ready")
    assert status == 200 and ready.get("db") == "ok", ready
    print("ready: ok")

    status, meta = _request("GET", f"{base}/api/v1/meta")
    assert status == 200 and "api_version" in meta, meta
    print(f"meta: phase={meta.get('phase')} env={meta.get('platform_env')}")

    slug = f"smoke-org-{args.principal}"
    status, org = _request(
        "POST",
        f"{base}/api/v1/organizations",
        data={"name": "Smoke Org", "slug": slug},
        headers=headers,
    )
    if status == 409:
        print("org: already exists (ok)")
        org_id = None
        workspace_id = None
    else:
        assert status == 200, org
        org_id = org["id"]
        workspace = org.get("default_workspace") or {}
        workspace_id = workspace.get("id")
        print(f"org: {org_id}")
        print(f"workspace: {workspace_id}")

    if org_id and workspace_id:
        status, project = _request(
            "POST",
            f"{base}/api/v1/projects",
            data={
                "organization_id": org_id,
                "workspace_id": workspace_id,
                "name": "Smoke Project",
                "description": "created by smoke_system.py",
            },
            headers=headers,
        )
        assert status == 200, project
        print(f"project: {project.get('id')}")

        status, projects = _request(
            "GET",
            f"{base}/api/v1/workspaces/{org_id}/{workspace_id}/projects",
            headers=headers,
        )
        assert status == 200, projects
        items = projects.get("items") if isinstance(projects, dict) else projects
        assert isinstance(items, list) and items, projects
        print(f"projects listed: {len(items)}")

    status, cert = _request(
        "POST",
        f"{base}/api/v1/certificates/demo/issue",
        data={
            "require_lean": args.require_lean,
            "allow_unverified": not args.require_lean,
        },
        headers=headers,
    )
    assert status == 200, cert
    lean_ok = bool(cert.get("lean_verified"))
    print(f"certificate: id={cert.get('certificate_id')} lean_verified={lean_ok}")
    if args.require_lean and not lean_ok:
        print("FAIL: Lean verification required but not recorded", file=sys.stderr)
        return 1

    print("smoke: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
