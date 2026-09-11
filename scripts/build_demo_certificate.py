#!/usr/bin/env python3
"""Build the Phase 1 demo certificate bundle."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "services" / "certificate-service" / "src"))
sys.path.insert(0, str(ROOT / "services" / "proof-service" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "certificate-sdk" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "provenance" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "schemas" / "src"))
sys.path.insert(0, str(ROOT / "packages" / "shared" / "src"))

from formal_certificate_service.issuer import issue_demo_certificate
from formal_shared.errors import FormalPlatformError


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the agent-policy demo certificate (Lean-gated by default)."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "examples" / "agent-policy-certificate" / "certificate-demo",
    )
    parser.add_argument(
        "--allow-unverified",
        action="store_true",
        help="Issue even if lake build fails or is unavailable (dev/offline only)",
    )
    parser.add_argument(
        "--skip-lean",
        action="store_true",
        help="Do not invoke lake at all (implies --allow-unverified)",
    )
    args = parser.parse_args()

    allow_unverified = args.allow_unverified or args.skip_lean
    run_lean = not args.skip_lean

    try:
        out = issue_demo_certificate(
            args.output,
            require_lean=not allow_unverified,
            allow_unverified=allow_unverified,
            run_lean=run_lean,
        )
    except FormalPlatformError as exc:
        print(json.dumps(exc.to_dict(), indent=2), file=sys.stderr)
        sys.exit(1)

    verification = json.loads(
        (out / "verification" / "verification.json").read_text(encoding="utf-8")
    )
    print(
        json.dumps(
            {
                "bundle": str(out),
                "lean_verified": bool(verification.get("success")),
                "root_hash_file": str(out / "certificate.json"),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
