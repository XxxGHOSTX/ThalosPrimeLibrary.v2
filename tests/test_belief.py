"""
Unit tests for the belief base.

Property tests (Section 21.3):
* rejected claims never appear as accepted
* state transitions are append-only in history
* query returns correct artifacts
"""

from __future__ import annotations

import pytest
from thalosprime.core.artifact.canonical import CanonicalArtifact
from thalosprime.core.belief.base import InMemoryBeliefBase


def _artifact(artifact_id: str, status: str = "provisional") -> CanonicalArtifact:
    return CanonicalArtifact.create(
        artifact_id=artifact_id,
        canonical_content=f"content of {artifact_id}",
        source_set=["src"],
        provenance_path=["ingest"],
        timestamp=1700000000,
        confidence=0.7,
        status=status,
    )


class TestInMemoryBeliefBase:
    def test_accept(self):
        bb = InMemoryBeliefBase()
        a = _artifact("a-1")
        bb.accept(a)
        assert "a-1" in bb.get_accepted()
        assert "a-1" not in bb.get_rejected()

    def test_reject(self):
        bb = InMemoryBeliefBase()
        a = _artifact("a-1")
        bb.reject(a)
        assert "a-1" in bb.get_rejected()
        assert "a-1" not in bb.get_accepted()

    def test_reject_never_in_accepted(self):
        """Property: rejected claims never appear as accepted."""
        bb = InMemoryBeliefBase()
        a = _artifact("a-1")
        bb.accept(a)
        bb.reject(a)
        assert "a-1" not in bb.get_accepted()
        assert "a-1" in bb.get_rejected()

    def test_suspend(self):
        bb = InMemoryBeliefBase()
        a = _artifact("a-1")
        bb.suspend(a)
        assert "a-1" in bb.get_suspended()

    def test_provisional(self):
        bb = InMemoryBeliefBase()
        a = _artifact("a-1")
        bb.provisional(a)
        assert "a-1" in bb.get_provisional()

    def test_dispute(self):
        bb = InMemoryBeliefBase()
        a = _artifact("a-1")
        bb.dispute(a)
        assert "a-1" in bb.get_disputed()

    def test_state_transitions_recorded_in_history(self):
        """History is append-only; each transition is preserved."""
        bb = InMemoryBeliefBase()
        a = _artifact("a-1")
        bb.accept(a)
        bb.dispute(a)
        bb.reject(a)
        history = bb.history
        assert len(history) == 3
        # Last transition should be to 'rejected'
        assert history[-1][2] == "rejected"

    def test_no_duplicate_across_buckets(self):
        """An artifact lives in exactly one bucket at a time."""
        bb = InMemoryBeliefBase()
        a = _artifact("a-1")
        bb.accept(a)
        bb.suspend(a)
        buckets = [
            bb.get_accepted(), bb.get_disputed(), bb.get_rejected(),
            bb.get_provisional(), bb.get_suspended(),
        ]
        total = sum("a-1" in b for b in buckets)
        assert total == 1

    def test_query(self):
        bb = InMemoryBeliefBase()
        a = _artifact("high-conf")
        b = _artifact("low-conf")
        # Manufacture different confidence via raw creation
        high = CanonicalArtifact.create(
            artifact_id="high-conf",
            canonical_content="high",
            source_set=["s"],
            provenance_path=["p"],
            timestamp=0,
            confidence=0.9,
            status="provisional",
        )
        low = CanonicalArtifact.create(
            artifact_id="low-conf",
            canonical_content="low",
            source_set=["s"],
            provenance_path=["p"],
            timestamp=0,
            confidence=0.1,
            status="provisional",
        )
        bb.accept(high)
        bb.suspend(low)
        results = bb.query(lambda c: c.confidence > 0.5)
        ids = [r.artifact_id for r in results]
        assert "high-conf" in ids
        assert "low-conf" not in ids
