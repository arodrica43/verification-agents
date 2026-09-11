"""Materialize generated Lean sources into a Lake project for independent checks."""

from __future__ import annotations

import re
from pathlib import Path

DEFAULT_TOOLCHAIN = "leanprover/lean4:v4.14.0"
DEFAULT_MODULE = "GeneratedModel"

# Constructs that must not appear in agent-produced, production-bound Lean.
AGENT_FORBIDDEN = ("sorry", "admit", "native_decide", "axiom")


def lean_toolchain_text(*, repo_root: Path | None = None) -> str:
    if repo_root is not None:
        candidate = repo_root / "lean" / "examples" / "agent-policy" / "lean-toolchain"
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip() + "\n"
    return DEFAULT_TOOLCHAIN + "\n"


def lakefile_toml(module_name: str = DEFAULT_MODULE) -> str:
    return (
        f'name = "{module_name}"\n'
        f'version = "0.1.0"\n'
        f'defaultTargets = ["{module_name}"]\n'
        f"\n"
        f"[[lean_lib]]\n"
        f'name = "{module_name}"\n'
    )


def ensure_module_wrapper(skeleton: str, module_name: str = DEFAULT_MODULE) -> str:
    """Keep generated content; Lake compiles ``{module_name}.lean`` as the lib root."""
    text = skeleton.strip() + "\n"
    # Drop accidental forbidden leftovers if a caller passed older stubs.
    if re.search(r"\b(sorry|admit|axiom)\b", text):
        # Still write as-is; the verifier scan will reject. Do not silently rewrite proofs.
        pass
    return text


def materialize_lean_project(
    skeleton: str,
    dest: Path,
    *,
    module_name: str = DEFAULT_MODULE,
    repo_root: Path | None = None,
) -> Path:
    """Write a minimal Lake project and return ``dest``."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "lean-toolchain").write_text(
        lean_toolchain_text(repo_root=repo_root), encoding="utf-8"
    )
    (dest / "lakefile.toml").write_text(lakefile_toml(module_name), encoding="utf-8")
    (dest / f"{module_name}.lean").write_text(
        ensure_module_wrapper(skeleton, module_name), encoding="utf-8"
    )
    return dest


def find_repo_root(start: Path | None = None) -> Path | None:
    cur = (start or Path(__file__)).resolve()
    for parent in [cur, *cur.parents]:
        if (parent / "lean" / "examples" / "agent-policy").exists():
            return parent
    return None
