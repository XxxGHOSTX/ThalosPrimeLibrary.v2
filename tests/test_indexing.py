"""
Unit tests for the deterministic indexing subsystem.

Acceptance tests from Section 17.3:
* same input → same coordinate (determinism invariant)
* coordinate round-trip
* multi-dimensional coordinate bundle
"""

from __future__ import annotations

import pytest
from thalosprime.core.artifact.canonical import CanonicalArtifact
from thalosprime.core.indexing.deterministic import SimpleDeterministicIndexer


def _make_artifact(artifact_id="a-001", content="test content") -> CanonicalArtifact:
    return CanonicalArtifact.create(
        artifact_id=artifact_id,
        canonical_content=content,
        source_set=["src"],
        provenance_path=["ingest"],
        timestamp=1700000000,
        confidence=0.8,
        status="provisional",
    )


class TestSimpleDeterministicIndexer:
    def test_encode_returns_bundle(self):
        indexer = SimpleDeterministicIndexer()
        a = _make_artifact()
        bundle = indexer.encode(a)
        assert bundle.identity_coord
        assert bundle.semantic_coord
        assert bundle.provenance_coord
        assert bundle.version_coord
        assert bundle.trust_coord

    def test_determinism_same_input(self):
        """Identical canonical inputs must yield identical coordinates."""
        indexer = SimpleDeterministicIndexer()
        a = _make_artifact()
        b = _make_artifact()
        assert indexer.encode(a).identity_coord == indexer.encode(b).identity_coord

    def test_different_content_different_coord(self):
        indexer = SimpleDeterministicIndexer()
        a = _make_artifact(content="alpha")
        b = _make_artifact(content="beta")
        assert indexer.encode(a).identity_coord != indexer.encode(b).identity_coord
        assert indexer.encode(a).semantic_coord != indexer.encode(b).semantic_coord

    def test_decode_returns_artifact(self):
        """Round-trip: encode then decode recovers the artifact."""
        indexer = SimpleDeterministicIndexer()
        a = _make_artifact()
        bundle = indexer.encode(a)
        recovered = indexer.decode(bundle.identity_coord)
        assert recovered is not None
        assert recovered.artifact_id == a.artifact_id

    def test_decode_unknown_returns_none(self):
        indexer = SimpleDeterministicIndexer()
        assert indexer.decode("nonexistent_coord") is None

    def test_semantic_coord_depends_only_on_content(self):
        """Two artifacts with same content but different IDs share semantic coord."""
        indexer = SimpleDeterministicIndexer()
        a = _make_artifact(artifact_id="id-1", content="same content")
        b = _make_artifact(artifact_id="id-2", content="same content")
        assert indexer.encode(a).semantic_coord == indexer.encode(b).semantic_coord

    def test_as_tuple_length(self):
        indexer = SimpleDeterministicIndexer()
        bundle = indexer.encode(_make_artifact())
        assert len(bundle.as_tuple()) == 5

    def test_cross_instance_determinism(self):
        """Determinism holds across fresh indexer instances."""
        a = _make_artifact()
        coord1 = SimpleDeterministicIndexer().encode(a).identity_coord
        coord2 = SimpleDeterministicIndexer().encode(a).identity_coord
        assert coord1 == coord2
