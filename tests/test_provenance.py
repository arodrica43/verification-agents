"""Unit tests for canonicalization and provenance roots."""

from __future__ import annotations

import pytest

from formal_provenance.canonical import CanonicalizationError, canonical_json_bytes, content_hash
from formal_provenance.graph import ProvenanceEdge, ProvenanceGraph, compute_provenance_root
from formal_schemas.enums import ProvenanceRelation
from formal_shared.errors import FormalPlatformError


def test_canonical_json_is_deterministic() -> None:
    a = {"b": 1, "a": {"z": 2, "y": [3, 1]}}
    b = {"a": {"y": [3, 1], "z": 2}, "b": 1}
    assert canonical_json_bytes(a) == canonical_json_bytes(b)
    assert content_hash(a) == content_hash(b)


def test_canonical_rejects_nan() -> None:
    with pytest.raises(CanonicalizationError):
        canonical_json_bytes({"x": float("nan")})


def test_provenance_root_changes_when_edge_changes() -> None:
    g1 = ProvenanceGraph()
    g1.add_edge(
        ProvenanceEdge("aaa", "bbb", ProvenanceRelation.DERIVED_FROM)
    )
    g2 = ProvenanceGraph()
    g2.add_edge(
        ProvenanceEdge("aaa", "ccc", ProvenanceRelation.DERIVED_FROM)
    )
    r1 = compute_provenance_root(body_hash="body", graph=g1)
    r2 = compute_provenance_root(body_hash="body", graph=g2)
    assert r1 != r2


def test_provenance_rejects_cycles() -> None:
    g = ProvenanceGraph()
    g.add_edge(ProvenanceEdge("a", "b", ProvenanceRelation.DEPENDS_ON))
    with pytest.raises(FormalPlatformError):
        g.add_edge(ProvenanceEdge("b", "a", ProvenanceRelation.DEPENDS_ON))
