"""
Unit tests for the audit trail.
"""

from __future__ import annotations

import pytest
from thalosprime.audit.trail import (
    AuditEvent,
    AuditEventKind,
    InMemoryAuditTrail,
)


class TestInMemoryAuditTrail:
    def test_append_and_verify_empty(self):
        trail = InMemoryAuditTrail()
        assert trail.verify()

    def test_append_single_event(self):
        trail = InMemoryAuditTrail()
        trail.append(AuditEvent(
            kind=AuditEventKind.STATE_TRANSITION,
            artifact_id="a-1",
            description="test",
        ))
        assert len(trail.events()) == 1
        assert trail.verify()

    def test_chain_integrity_multiple_events(self):
        trail = InMemoryAuditTrail()
        for i in range(10):
            trail.append(AuditEvent(
                kind=AuditEventKind.VALIDATION_OUTCOME,
                artifact_id=f"a-{i}",
                description=f"event {i}",
            ))
        assert trail.verify()

    def test_tampered_chain_detected(self):
        trail = InMemoryAuditTrail()
        trail.append(AuditEvent(
            kind=AuditEventKind.CLAIM_ADMITTED,
            artifact_id="x",
            description="admitted",
        ))
        # Tamper
        trail.events()[0].chain_hash = "bad" + "0" * 61
        assert not trail.verify()

    def test_events_returns_copy(self):
        trail = InMemoryAuditTrail()
        ev = AuditEvent(kind=AuditEventKind.QUERY_RECEIVED, artifact_id=None, description="q")
        trail.append(ev)
        events = trail.events()
        events.clear()
        assert len(trail.events()) == 1

    def test_event_to_dict(self):
        trail = InMemoryAuditTrail()
        ev = AuditEvent(
            kind=AuditEventKind.POLICY_EXCEPTION,
            artifact_id="a-2",
            description="policy exception",
            payload={"detail": "test"},
        )
        trail.append(ev)
        d = ev.to_dict()
        assert d["kind"] == AuditEventKind.POLICY_EXCEPTION
        assert d["artifact_id"] == "a-2"
        assert "chain_hash" in d
