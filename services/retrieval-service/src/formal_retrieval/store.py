"""In-memory tenant-scoped retrieval index (Phase 9 foundation)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RetrievalDocument:
    organization_id: str
    workspace_id: str
    document_id: str
    content_hash: str
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    trust_level: str = "research"


@dataclass
class RetrievalHit:
    document_id: str
    content_hash: str
    score: float
    snippet: str
    trust_level: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "content_hash": self.content_hash,
            "score": self.score,
            "snippet": self.snippet,
            "trust_level": self.trust_level,
        }


_TOKEN = re.compile(r"[a-z0-9_]+", re.IGNORECASE)


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _TOKEN.findall(text)}


class InMemoryRetrievalIndex:
    """Simple keyword retrieval with hard tenant pre-filter."""

    def __init__(self) -> None:
        self._docs: dict[tuple[str, str, str], RetrievalDocument] = {}

    def upsert(self, doc: RetrievalDocument) -> None:
        key = (doc.organization_id, doc.workspace_id, doc.document_id)
        self._docs[key] = doc

    def search(
        self,
        *,
        organization_id: str,
        workspace_id: str,
        query: str,
        limit: int = 10,
    ) -> list[RetrievalHit]:
        # CRITICAL: filter by tenant before scoring (never rank global then filter).
        candidates = [
            d
            for (org, ws, _), d in self._docs.items()
            if org == organization_id and ws == workspace_id
        ]
        q = _tokens(query)
        if not q:
            return []
        scored: list[RetrievalHit] = []
        for doc in candidates:
            overlap = len(q & _tokens(doc.text))
            if overlap == 0:
                continue
            score = overlap / max(len(q), 1)
            scored.append(
                RetrievalHit(
                    document_id=doc.document_id,
                    content_hash=doc.content_hash,
                    score=score,
                    snippet=doc.text[:240],
                    trust_level=doc.trust_level,
                )
            )
        scored.sort(key=lambda h: h.score, reverse=True)
        return scored[:limit]
