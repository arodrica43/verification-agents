#!/usr/bin/env bash
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
