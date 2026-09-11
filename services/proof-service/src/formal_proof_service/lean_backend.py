"""Lean 4 + Lake backend for independent verification."""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any

from formal_proof_service.backend import ProofCheckRequest, ProofCheckResult
from formal_shared.errors import ErrorCode, FormalPlatformError

_IGNORE_NAMES = {".lake", ".git", "__pycache__", ".DS_Store"}


def _ignore_build_artifacts(directory: str, names: list[str]) -> set[str]:
    return {name for name in names if name in _IGNORE_NAMES}


def _strip_lean_comments(text: str) -> str:
    """Remove Lean line and block comments, preserving string literals.

    Handles nested ``/- ... -/`` (including ``/-!`` / ``/--`` docs) and ``--``
    line comments. Comment bodies are replaced with spaces (newlines kept) so
    word-boundary scans do not match tokens that only appear in comments.
    """
    out: list[str] = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == '"':
            out.append(ch)
            i += 1
            while i < n:
                if text[i] == "\\" and i + 1 < n:
                    out.append(text[i])
                    out.append(text[i + 1])
                    i += 2
                    continue
                out.append(text[i])
                if text[i] == '"':
                    i += 1
                    break
                i += 1
            continue
        if ch == "/" and i + 1 < n and text[i + 1] == "-":
            depth = 1
            out.extend("  ")
            i += 2
            while i < n and depth > 0:
                if text[i] == "/" and i + 1 < n and text[i + 1] == "-":
                    depth += 1
                    out.extend("  ")
                    i += 2
                elif text[i] == "-" and i + 1 < n and text[i + 1] == "/":
                    depth -= 1
                    out.extend("  ")
                    i += 2
                else:
                    out.append("\n" if text[i] == "\n" else " ")
                    i += 1
            continue
        if ch == "-" and i + 1 < n and text[i + 1] == "-":
            while i < n and text[i] != "\n":
                out.append(" ")
                i += 1
            continue
        out.append(ch)
        i += 1
    return "".join(out)


class LeanLakeBackend:
    """Runs `lake build` on a clean copy of the project.

    Production workers add network/cgroup isolation; this adapter focuses on
    deterministic check semantics, forbidden-construct scanning, and a fresh
    working tree so generation artifacts cannot leak into verification.
    """

    backend_name = "lean4"

    def __init__(self, lake_executable: str | None = None) -> None:
        self.lake_executable = lake_executable or os.environ.get("LAKE_EXECUTABLE", "lake")

    async def check(self, request: ProofCheckRequest) -> ProofCheckResult:
        project = Path(request.project_path)
        if not project.exists():
            raise FormalPlatformError(
                ErrorCode.DEPENDENCY_MISSING,
                f"Lean project path does not exist: {project}",
            )

        forbidden = self._scan_forbidden(project, request.forbidden_constructs)
        if forbidden:
            return ProofCheckResult(
                request_id=request.request_id,
                success=False,
                exit_code=None,
                stdout="",
                stderr="Forbidden constructs present in sources",
                contains_forbidden=True,
                forbidden_matches=forbidden,
                environment=await self._env_info(project, work_path=None),
            )

        with tempfile.TemporaryDirectory(prefix="formal-lean-check-") as tmp:
            work = Path(tmp) / "project"
            await asyncio.to_thread(
                shutil.copytree,
                project,
                work,
                ignore=_ignore_build_artifacts,
            )
            return await self._lake_build(request, source=project, work=work)

    async def _lake_build(
        self,
        request: ProofCheckRequest,
        *,
        source: Path,
        work: Path,
    ) -> ProofCheckResult:
        started = time.perf_counter()
        try:
            proc = await asyncio.create_subprocess_exec(
                self.lake_executable,
                "build",
                cwd=str(work),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "LEAN_ABORT_ON_PANIC": "1"},
            )
            try:
                stdout_b, stderr_b = await asyncio.wait_for(
                    proc.communicate(), timeout=request.timeout_seconds
                )
            except TimeoutError:
                proc.kill()
                await proc.wait()
                raise FormalPlatformError(
                    ErrorCode.TIMEOUT,
                    f"lake build timed out after {request.timeout_seconds}s",
                ) from None
        except FileNotFoundError as exc:
            raise FormalPlatformError(
                ErrorCode.VERIFICATION_ENVIRONMENT_ERROR,
                f"lake executable not found: {self.lake_executable}",
            ) from exc

        duration_ms = int((time.perf_counter() - started) * 1000)
        stdout = stdout_b.decode("utf-8", errors="replace")
        stderr = stderr_b.decode("utf-8", errors="replace")
        success = proc.returncode == 0
        return ProofCheckResult(
            request_id=request.request_id,
            success=success,
            exit_code=proc.returncode,
            stdout=stdout,
            stderr=stderr,
            duration_ms=duration_ms,
            contains_forbidden=False,
            environment=await self._env_info(source, work_path=work),
        )

    async def inspect(self, project_path: str) -> dict[str, Any]:
        project = Path(project_path)
        lean_files = sorted(
            str(p.relative_to(project))
            for p in project.rglob("*.lean")
            if ".lake" not in p.parts
        )
        toolchain = None
        tc = project / "lean-toolchain"
        if tc.exists():
            toolchain = tc.read_text(encoding="utf-8").strip()
        return {
            "backend": self.backend_name,
            "toolchain": toolchain,
            "lean_files": lean_files,
        }

    async def search_proof(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {
            "status": "not_implemented",
            "message": "Proof search via LeanDojo-v2 planned for Phase 8",
        }

    async def extract_dependencies(self, project_path: str) -> dict[str, Any]:
        project = Path(project_path)
        manifest = project / "lake-manifest.json"
        return {
            "lake_manifest_present": manifest.exists(),
            "toolchain": (project / "lean-toolchain").read_text(encoding="utf-8").strip()
            if (project / "lean-toolchain").exists()
            else None,
        }

    def _scan_forbidden(self, project: Path, constructs: list[str]) -> list[str]:
        matches: list[str] = []
        patterns = {
            name: re.compile(rf"\b{re.escape(name)}\b")
            for name in constructs
        }
        for lean_file in project.rglob("*.lean"):
            if ".lake" in lean_file.parts:
                continue
            text = _strip_lean_comments(lean_file.read_text(encoding="utf-8"))
            for name, pattern in patterns.items():
                if pattern.search(text):
                    matches.append(f"{lean_file.relative_to(project).as_posix()}:{name}")
        return matches

    async def _env_info(self, project: Path, *, work_path: Path | None) -> dict[str, Any]:
        toolchain = None
        tc = project / "lean-toolchain"
        if tc.exists():
            toolchain = tc.read_text(encoding="utf-8").strip()
        info: dict[str, Any] = {
            "toolchain": toolchain,
            "lake_executable": self.lake_executable,
            "project_path": str(project.resolve()),
            "isolated_workdir": work_path is not None,
        }
        if work_path is not None:
            info["workdir"] = str(work_path.resolve())
        return info
