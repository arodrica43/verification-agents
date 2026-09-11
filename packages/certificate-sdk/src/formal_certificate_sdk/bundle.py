"""Certificate reproducibility bundle builder and verifier."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from formal_certificate_sdk.signing import hmac_sign, hmac_verify
from formal_provenance.canonical import canonical_json_bytes, content_hash
from formal_provenance.graph import ProvenanceGraph, compute_provenance_root
from formal_schemas.certificate import Certificate
from formal_schemas.problem_spec import ProblemSpec
from formal_shared.errors import ErrorCode, FormalPlatformError
from formal_shared.hashing import sha256_hex

VERIFY_SH = """#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
echo "Formal Platform certificate verifier (shell helper)"
echo "Prefer: formal-cert verify $ROOT"
# Manifest + file hashes
python - <<'PY'
import json, hashlib, sys
from pathlib import Path
root = Path(".")
manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
for rel, expected in manifest["files"].items():
    data = (root / rel).read_bytes()
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        print(f"HASH MISMATCH: {rel}")
        sys.exit(1)
print("manifest integrity: OK")
PY
if command -v lake >/dev/null 2>&1; then
  (cd lean && lake build)
  echo "lean build: OK"
else
  echo "lake not found; skipping Lean build (run formal-cert verify with --lean)"
fi
"""


@dataclass
class BundleInputs:
    certificate: Certificate
    problem: ProblemSpec
    assumptions: list[dict[str, Any]]
    provenance_graph: ProvenanceGraph
    lean_project_dir: Path
    verification_report: dict[str, Any]
    signing_key_id: str
    signing_secret: str


class CertificateBundleBuilder:
    """Build a portable certificate directory."""

    def build(self, inputs: BundleInputs, output_dir: Path) -> Path:
        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True)

        lean_out = output_dir / "lean"
        lean_out.mkdir()
        self._copy_lean_project(inputs.lean_project_dir, lean_out)

        evidence_dir = output_dir / "evidence"
        evidence_dir.mkdir()
        evidence_items = [e.model_dump(mode="json") for e in inputs.certificate.evidence]
        self._write_json(evidence_dir / "manifest.json", {"items": evidence_items})

        problem_path = output_dir / "problem.json"
        assumptions_path = output_dir / "assumptions.json"
        provenance_path = output_dir / "provenance.json"
        verification_dir = output_dir / "verification"
        verification_dir.mkdir()
        verification_path = verification_dir / "verification.json"
        signatures_dir = output_dir / "signatures"
        signatures_dir.mkdir()

        self._write_json(problem_path, inputs.problem.model_dump(mode="json"))
        self._write_json(assumptions_path, inputs.assumptions)
        self._write_json(
            provenance_path,
            {
                "edges": inputs.provenance_graph.sorted_edge_dicts(),
                "artifact_hashes": sorted(inputs.provenance_graph._nodes),
            },
        )
        self._write_json(verification_path, inputs.verification_report)

        # Body without root/signatures for hashing (avoid circularity).
        cert = inputs.certificate.model_copy(deep=True)
        cert.root_hash = ""
        cert.signatures = []
        cert.provenance.root_hash = ""
        body = cert.model_dump(mode="json")
        body_hash = content_hash(body)
        root = compute_provenance_root(
            body_hash=body_hash,
            graph=inputs.provenance_graph,
            extra_artifact_hashes=sorted(inputs.provenance_graph._nodes),
        )
        cert.root_hash = root
        cert.provenance.root_hash = root

        payload = canonical_json_bytes({**body, "root_hash": root})
        signature = hmac_sign(
            key_id=inputs.signing_key_id,
            secret=inputs.signing_secret,
            payload=payload,
        )
        cert.signatures = [signature]
        self._write_json(output_dir / "certificate.json", cert.model_dump(mode="json"))
        self._write_json(
            signatures_dir / f"{signature.key_id}.json",
            signature.model_dump(mode="json"),
        )

        (output_dir / "verify.sh").write_text(VERIFY_SH, encoding="utf-8", newline="\n")

        files: dict[str, str] = {}
        for path in sorted(output_dir.rglob("*")):
            if path.is_file() and path.name != "manifest.json":
                rel = path.relative_to(output_dir).as_posix()
                files[rel] = sha256_hex(path.read_bytes())

        manifest = {
            "certificate_id": cert.certificate_id,
            "root_hash": root,
            "files": files,
        }
        self._write_json(output_dir / "manifest.json", manifest)
        return output_dir

    def _copy_lean_project(self, src: Path, dest: Path) -> None:
        if not src.exists():
            raise FormalPlatformError(
                ErrorCode.DEPENDENCY_MISSING,
                f"Lean project not found: {src}",
            )
        for item in src.iterdir():
            if item.name in {".lake", "build", "lake-packages"}:
                continue
            target = dest / item.name
            if item.is_dir():
                shutil.copytree(item, target, ignore=shutil.ignore_patterns(".lake", "build"))
            else:
                shutil.copy2(item, target)

    def _write_json(self, path: Path, data: Any) -> None:
        path.write_bytes(canonical_json_bytes(data))


def verify_bundle(
    bundle_dir: Path,
    *,
    signing_secret: str | None = None,
    run_lean: bool = False,
) -> dict[str, Any]:
    """Independently verify a certificate bundle (no LLM)."""
    bundle_dir = bundle_dir.resolve()
    manifest_path = bundle_dir / "manifest.json"
    cert_path = bundle_dir / "certificate.json"
    if not manifest_path.exists() or not cert_path.exists():
        raise FormalPlatformError(
            ErrorCode.INTEGRITY_FAILURE,
            "Bundle missing manifest.json or certificate.json",
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []

    for rel, expected in manifest.get("files", {}).items():
        path = bundle_dir / rel
        if not path.exists():
            failures.append(f"missing file: {rel}")
            continue
        actual = sha256_hex(path.read_bytes())
        if actual != expected:
            failures.append(f"hash mismatch: {rel}")

    cert_data = json.loads(cert_path.read_text(encoding="utf-8"))
    cert = Certificate.model_validate(cert_data)

    # Recompute root from body excluding circular fields
    body = dict(cert_data)
    body["root_hash"] = ""
    body["signatures"] = []
    if isinstance(body.get("provenance"), dict):
        body["provenance"] = dict(body["provenance"])
        body["provenance"]["root_hash"] = ""
    body_hash = content_hash(body)
    provenance = json.loads((bundle_dir / "provenance.json").read_text(encoding="utf-8"))
    graph = ProvenanceGraph()
    from formal_provenance.graph import ProvenanceEdge
    from formal_schemas.enums import ProvenanceRelation

    for edge in provenance.get("edges", []):
        graph.add_edge(
            ProvenanceEdge(
                source_hash=edge["source_hash"],
                target_hash=edge["target_hash"],
                relation=ProvenanceRelation(edge["relation"]),
            )
        )
    expected_root = compute_provenance_root(
        body_hash=body_hash,
        graph=graph,
        extra_artifact_hashes=provenance.get("artifact_hashes", []),
    )
    if cert.root_hash != expected_root or manifest.get("root_hash") != expected_root:
        failures.append("provenance root mismatch")

    if signing_secret and cert.signatures:
        payload = canonical_json_bytes({**body, "root_hash": cert.root_hash})
        for sig in cert.signatures:
            if not hmac_verify(secret=signing_secret, payload=payload, signature=sig.signature):
                failures.append(f"signature invalid: {sig.key_id}")

    lean_ok: bool | None = None
    if run_lean:
        lean_dir = bundle_dir / "lean"
        if not (lean_dir / "lakefile.toml").exists() and not (lean_dir / "lakefile.lean").exists():
            failures.append("lean project missing lakefile")
        else:
            try:
                result = subprocess.run(
                    ["lake", "build"],
                    cwd=lean_dir,
                    capture_output=True,
                    text=True,
                    timeout=int(os.environ.get("PROOF_WORKER_TIMEOUT_SECONDS", "300")),
                    check=False,
                )
                lean_ok = result.returncode == 0
                if result.returncode != 0:
                    failures.append(f"lean build failed: {result.stderr[-2000:]}")
            except FileNotFoundError:
                failures.append("lake executable not found")
            except subprocess.TimeoutExpired:
                failures.append("lean build timeout")

    if failures:
        raise FormalPlatformError(
            ErrorCode.INTEGRITY_FAILURE,
            "Certificate bundle verification failed",
            details={"failures": failures},
        )

    return {
        "ok": True,
        "certificate_id": cert.certificate_id,
        "root_hash": cert.root_hash,
        "lean_verified": lean_ok,
    }
