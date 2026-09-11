# Contributing

1. Read [`docs/architecture/overview.md`](docs/architecture/overview.md) and [`docs/roadmap.md`](docs/roadmap.md).
2. Prefer small, complete increments that preserve the trust model (Lean kernel authority, independent verification, provenance).
3. Do not fake verification status, hashes, or signatures.
4. Add tests for deterministic domain logic; mark Lean-dependent tests with `@pytest.mark.lean`.
5. Update ADRs when making architectural decisions.
6. Never commit secrets.

## Development

```bash
uv sync --all-extras
uv run ruff check .
uv run pytest -q
```

## Pull requests

CI runs lint, type checks (where configured), unit tests, and (when available) Lean builds.
