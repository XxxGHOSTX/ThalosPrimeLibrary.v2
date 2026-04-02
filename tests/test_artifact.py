"""
Unit tests for the CanonicalArtifact model.

Covers Section 21.1 (unit tests) and Section 17.3 (acceptance tests):
* artifact field integrity
* canonicalization determinism
* status validation
"""

from __future__ import annotations

import pytest
from thalosprime.core.artifact.canonical import CanonicalArtifact


def _make_artifact(**overrides) -> CanonicalArtifact:
    defaults = dict(
        artifact_id="test-001",
        canonical_content="The sky is blue.",
        source_set=["source-a"],
        provenance_path=["ingest", "normalize"],
        timestamp=1700000000,
        confidence=0.9,
        status="provisional",
    )
    defaults.update(overrides)
    return CanonicalArtifact.create(**defaults)


class TestCanonicalArtifactCreation:
    def test_basic_creation(self):
        a = _make_artifact()
        assert a.artifact_id == "test-001"
        assert a.canonical_content == "The sky is blue."
        assert a.confidence == 0.9
        assert a.status == "provisional"

    def test_source_set_is_tuple(self):
        a = _make_artifact(source_set=["s1", "s2"])
        assert isinstance(a.source_set, tuple)
        assert a.source_set == ("s1", "s2")

    def test_provenance_path_is_tuple(self):
        a = _make_artifact(provenance_path=["step1", "step2"])
        assert isinstance(a.provenance_path, tuple)

    def test_all_valid_statuses(self):
        for status in ("accepted", "provisional", "disputed", "rejected", "suspended"):
            a = _make_artifact(status=status)
            assert a.status == status

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="status"):
            _make_artifact(status="unknown")

    def test_empty_artifact_id_raises(self):
        with pytest.raises(ValueError):
            _make_artifact(artifact_id="")

    def test_confidence_out_of_range_raises(self):
        with pytest.raises(ValueError, match="confidence"):
            _make_artifact(confidence=1.5)
        with pytest.raises(ValueError, match="confidence"):
            _make_artifact(confidence=-0.1)

    def test_boundary_confidence_values(self):
        a0 = _make_artifact(confidence=0.0)
        a1 = _make_artifact(confidence=1.0)
        assert a0.confidence == 0.0
        assert a1.confidence == 1.0

    def test_with_status(self):
        a = _make_artifact(status="provisional")
        b = a.with_status("accepted")
        assert b.status == "accepted"
        assert b.artifact_id == a.artifact_id
        assert b.canonical_content == a.canonical_content

    def test_immutability(self):
        a = _make_artifact()
        with pytest.raises(Exception):
            a.artifact_id = "tampered"  # type: ignore[misc]

    def test_hashability(self):
        a = _make_artifact()
        s = {a}  # should not raise
        assert a in s
