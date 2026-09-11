#!/usr/bin/env python3
"""Build the Phase 1 demo certificate bundle."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "certificate-service" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "certificate-sdk" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "provenance" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "schemas" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "shared" / "src"))

from formal_certificate_service.issuer import issue_demo_certificate


def try_lake_build(lean_dir: Path) -> bool:
    try:
        result = subprocess.run(
            ["lake", "build"],
            cwd=lean_dir,
            capture_output=True,
            text=True,
            timeout=600,
            check=False,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "examples" / "agent-policy-certificate" / "certificate-demo",
    )
    parser.add_argument(
        "--require-lean",
        action="store_true",
        help="Fail if lake build does not succeed",
    )
    args = parser.parse_args()

    lean_dir = ROOT / "lean" / "examples" / "agent-policy"
    lean_ok = try_lake_build(lean_dir)
    if args.require_lean and not lean_ok:
        print("lake build failed and --require-lean was set", file=sys.stderr)
        sys.exit(1)

    out = issue_demo_certificate(args.output, lean_verified=lean_ok)
    print(json.dumps({"bundle": str(out), "lean_verified": lean_ok}, indent=2))


if __name__ == "__main__":
    main()
