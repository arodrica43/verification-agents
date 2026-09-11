"""In-memory provenance DAG and root hash computation."""

from __future__ import annotations

from dataclasses import dataclass, field

from formal_provenance.canonical import content_hash
from formal_schemas.enums import ProvenanceRelation
from formal_shared.errors import ErrorCode, FormalPlatformError


@dataclass(frozen=True)
class ProvenanceEdge:
    source_hash: str
    target_hash: str
    relation: ProvenanceRelation

    def as_dict(self) -> dict[str, str]:
        return {
            "source_hash": self.source_hash,
            "target_hash": self.target_hash,
            "relation": str(self.relation),
        }


@dataclass
class ProvenanceGraph:
    """Typed provenance DAG (acyclic by construction check)."""

    edges: list[ProvenanceEdge] = field(default_factory=list)
    _nodes: set[str] = field(default_factory=set)

    def add_node(self, content_hash_value: str) -> None:
        self._nodes.add(content_hash_value)

    def add_edge(self, edge: ProvenanceEdge) -> None:
        self._nodes.add(edge.source_hash)
        self._nodes.add(edge.target_hash)
        # Cycle check: edge source -> target means source depends on / relates to target.
        # Treat direction as "from source to target"; reject if target can reach source.
        if self._reaches(edge.target_hash, edge.source_hash):
            raise FormalPlatformError(
                ErrorCode.CONFLICT,
                "Provenance edge would introduce a cycle",
                details=edge.as_dict(),
            )
        self.edges.append(edge)

    def _reaches(self, start: str, goal: str) -> bool:
        if start == goal:
            return True
        stack = [start]
        seen: set[str] = set()
        adjacency: dict[str, list[str]] = {}
        for e in self.edges:
            adjacency.setdefault(e.source_hash, []).append(e.target_hash)
        while stack:
            node = stack.pop()
            if node in seen:
                continue
            seen.add(node)
            for nxt in adjacency.get(node, []):
                if nxt == goal:
                    return True
                stack.append(nxt)
        return False

    def sorted_edge_dicts(self) -> list[dict[str, str]]:
        return sorted(
            (e.as_dict() for e in self.edges),
            key=lambda d: (d["relation"], d["source_hash"], d["target_hash"]),
        )


def compute_provenance_root(
    *,
    body_hash: str,
    graph: ProvenanceGraph,
    extra_artifact_hashes: list[str] | None = None,
) -> str:
    """Compute deterministic provenance root for a certificate body.

    The body_hash must exclude root_hash and signatures to avoid circularity.
    """
    payload = {
        "body_hash": body_hash,
        "edges": graph.sorted_edge_dicts(),
        "artifacts": sorted(set(extra_artifact_hashes or [])),
    }
    return content_hash(payload)
