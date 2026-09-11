# Retrieval service

Hybrid knowledge retrieval with **mandatory tenant pre-filter** before ranking
(threat model T09).

```bash
# from repo root with PYTHONPATH / uv
python -m formal_retrieval.app
# http://localhost:8003/health
```

Current implementation: in-memory keyword index suitable for Phase 9 foundation.
Postgres+pgvector and FTS land as the next hardening step on the same API.
