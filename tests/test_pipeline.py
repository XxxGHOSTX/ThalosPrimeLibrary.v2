"""
Integration tests for the full pipeline.

Covers Section 21.2:
* ingest → index → reason → validate → present
* audit chain replay
* coordinate round-trip recovery
* policy failures produce suspension
"""

from __future__ import annotations

import pytest
from thalosprime.core.artifact.canonical import CanonicalArtifact
from thalosprime.archive.coordinate_space.babel import InMemoryBabelArchive, PolicyContext
from thalosprime.audit.trail import InMemoryAuditTrail, AuditEvent, AuditEventKind
from thalosprime.core.belief.base import InMemoryBeliefBase
from thalosprime.core.indexing.deterministic import SimpleDeterministicIndexer
from thalosprime.core.reasoning.reasoner import PassthroughReasoner
from thalosprime.core.validation.validator import BasicValidator
from thalosprime.core.presentation.engine import DefaultPresentationEngine
from thalosprime.interface.chat.response_orchestrator import ResponseOrchestrator


def _artifact(artifact_id: str, **kw) -> CanonicalArtifact:
    defaults = dict(
        canonical_content="Test content for integration.",
        source_set=["integration-test"],
        provenance_path=["ingest", "normalize"],
        timestamp=1700000000,
        confidence=0.85,
        status="provisional",
    )
    defaults.update(kw)
    return CanonicalArtifact.create(artifact_id=artifact_id, **defaults)


class TestFullPipeline:
    def test_ingest_then_retrieve(self):
        archive = InMemoryBabelArchive()
        a = _artifact("p-001")
        bundle = archive.store(a)
        stored = archive.resolve(bundle.identity_coord)
        assert stored is not None
        assert stored.artifact.artifact_id == "p-001"

    def test_coordinate_round_trip(self):
        """Same canonical artifact → same coordinate across two indexers."""
        a = _artifact("rt-001")
        coord1 = SimpleDeterministicIndexer().encode(a).identity_coord
        coord2 = SimpleDeterministicIndexer().encode(a).identity_coord
        assert coord1 == coord2

    def test_policy_gate_rejects_low_trust(self):
        archive = InMemoryBabelArchive()
        a = _artifact("low-trust", status="rejected")
        bundle = archive.store(a)
        policy = PolicyContext(
            allow_statuses=frozenset({"accepted", "provisional"}),
            require_min_confidence=0.5,
        )
        result = archive.reconstruct(bundle.identity_coord, policy)
        assert result is None

    def test_policy_gate_allows_accepted(self):
        archive = InMemoryBabelArchive()
        a = _artifact("accepted-art", status="accepted")
        bundle = archive.store(a)
        policy = PolicyContext(allow_statuses=frozenset({"accepted"}))
        result = archive.reconstruct(bundle.identity_coord, policy)
        assert result is not None
        assert result.artifact_id == "accepted-art"

    def test_audit_chain_integrity(self):
        trail = InMemoryAuditTrail()
        for i in range(5):
            trail.append(AuditEvent(
                kind=AuditEventKind.STATE_TRANSITION,
                artifact_id=f"art-{i}",
                description=f"Transition {i}",
            ))
        assert trail.verify()

    def test_audit_chain_detects_tampering(self):
        trail = InMemoryAuditTrail()
        trail.append(AuditEvent(
            kind=AuditEventKind.CLAIM_ADMITTED,
            artifact_id="art-1",
            description="Admitted",
        ))
        # Tamper with the hash
        trail.events()[0].chain_hash = "tampered" + "0" * 57
        assert not trail.verify()

    def test_reasoner_produces_candidates(self):
        indexer = SimpleDeterministicIndexer()
        belief = InMemoryBeliefBase()
        reasoner = PassthroughReasoner()
        a = _artifact("r-001")
        bundle = indexer.encode(a)
        props = reasoner.derive([(a, bundle)], belief)
        assert len(props) == 1
        assert props[0].proposition.artifact_id == "r-001"

    def test_validator_gates_claim(self):
        v = BasicValidator()
        good = _artifact("good")
        bad = _artifact("bad", source_set=[])
        assert v.validate(good).passed
        assert not v.validate(bad).passed

    def test_presentation_renders_output(self):
        engine = DefaultPresentationEngine()
        a = _artifact("p-001", status="accepted")
        output = engine.render(a)
        assert "p-001" in output.human_layer
        assert output.machine_layer["artifact_id"] == "p-001"


class TestResponseOrchestrator:
    def test_handle_query_returns_output(self):
        orch = ResponseOrchestrator()
        result = orch.handle_query("What is the capital of France?")
        assert result.human_layer
        assert result.machine_layer

    def test_handle_query_creates_audit_events(self):
        orch = ResponseOrchestrator()
        orch.handle_query("Test query")
        events = orch.audit_trail.events()
        assert len(events) >= 1
        kinds = {e.kind for e in events}
        assert AuditEventKind.QUERY_RECEIVED in kinds

    def test_ingest_valid_artifact_accepted(self):
        orch = ResponseOrchestrator()
        a = _artifact("ingest-001", status="provisional")
        orch.ingest(a)
        accepted = orch.belief_base.get_accepted()
        assert "ingest-001" in accepted

    def test_ingest_invalid_artifact_suspended(self):
        orch = ResponseOrchestrator()
        a = _artifact("bad-ingest", source_set=[], status="provisional")
        orch.ingest(a)
        accepted = orch.belief_base.get_accepted()
        assert "bad-ingest" not in accepted

    def test_audit_chain_valid_after_pipeline(self):
        orch = ResponseOrchestrator()
        orch.handle_query("Query one")
        orch.handle_query("Query two")
        assert orch.audit_trail.verify()
