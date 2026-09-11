"""CLI: formal-cert verify|hash."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from formal_certificate_sdk.bundle import verify_bundle
from formal_provenance.canonical import content_hash
from formal_shared.errors import FormalPlatformError


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="formal-cert", description="Formal certificate toolkit")
    sub = parser.add_subparsers(dest="command", required=True)

    verify_p = sub.add_parser("verify", help="Independently verify a certificate bundle")
    verify_p.add_argument("bundle", type=Path, help="Path to certificate bundle directory")
    verify_p.add_argument(
        "--lean",
        action="store_true",
        help="Also run lake build inside bundle/lean",
    )
    verify_p.add_argument(
        "--signing-secret",
        default=os.environ.get("CERTIFICATE_SIGNING_SECRET"),
        help="HMAC secret for signature verification (or env CERTIFICATE_SIGNING_SECRET)",
    )

    hash_p = sub.add_parser("hash", help="Compute content hash of a JSON file")
    hash_p.add_argument("path", type=Path)

    args = parser.parse_args(argv)

    try:
        if args.command == "verify":
            result = verify_bundle(
                args.bundle,
                signing_secret=args.signing_secret,
                run_lean=args.lean,
            )
            print(json.dumps(result, indent=2))
        elif args.command == "hash":
            data = json.loads(args.path.read_text(encoding="utf-8"))
            print(content_hash(data))
        else:
            parser.error(f"unknown command {args.command}")
    except FormalPlatformError as exc:
        print(json.dumps(exc.to_dict(), indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
