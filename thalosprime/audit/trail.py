"""
Audit Trail — Section 13.3 and Section 14 of the TPL.v2 specification.

The audit chain records every state transition, version change, validation
outcome, provenance transformation, and policy exception.  It is append-only
and must never silently drop a record.
"""

from __future__ import annotations

import hashlib
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum


class AuditEventKind(str, Enum):
    STATE_TRANSITION = "state_transition"
    VERSION_CHANGE = "version_change"
    VALIDATION_OUTCOME = "validation_outcome"
    PROVENANCE_TRANSFORM = "provenance_transform"
    POLICY_EXCEPTION = "policy_exception"
    COORDINATE_GENERATED = "coordinate_generated"
    CLAIM_ADMITTED = "claim_admitted"
    CLAIM_REJECTED = "claim_rejected"
    REASONING_STEP = "reasoning_step"
    QUERY_RECEIVED = "query_received"
    RESPONSE_RENDERED = "response_rendered"


@dataclass
class AuditEvent:
    """A single immutable entry in the audit chain."""

    kind: AuditEventKind
    artifact_id: str | None
    description: str
    payload: dict = field(default_factory=dict)
    timestamp: int = field(default_factory=lambda: int(time.time()))
    # Chained hash: SHA-256 of (previous_hash + event content)
    chain_hash: str = field(default="", init=False)

    def compute_hash(self, previous_hash: str) -> str:
        content = json.dumps(
            {
                "kind": self.kind,
                "artifact_id": self.artifact_id,
                "description": self.description,
                "payload": self.payload,
                "timestamp": self.timestamp,
                "previous_hash": previous_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(content).hexdigest()

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "artifact_id": self.artifact_id,
            "description": self.description,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "chain_hash": self.chain_hash,
        }


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class AuditTrail(ABC):
    """Abstract contract for the audit trail."""

    @abstractmethod
    def append(self, event: AuditEvent) -> None:
        """Append *event* to the immutable audit chain."""

    @abstractmethod
    def verify(self) -> bool:
        """
        Verify the integrity of the audit chain.

        Returns True if all chain hashes are consistent; False if tampering
        is detected.
        """

    @abstractmethod
    def events(self) -> list[AuditEvent]:
        """Return all recorded events in append order."""


# ---------------------------------------------------------------------------
# Concrete implementation
# ---------------------------------------------------------------------------

class InMemoryAuditTrail(AuditTrail):
    """
    Append-only, hash-chained audit trail stored in memory.

    Each event's chain_hash is computed over the previous event's hash and
    the current event's content.  This makes post-hoc tampering detectable.
    """

    GENESIS_HASH = "0" * 64

    def __init__(self) -> None:
        self._chain: list[AuditEvent] = []
        self._head_hash: str = self.GENESIS_HASH

    def append(self, event: AuditEvent) -> None:
        event.chain_hash = event.compute_hash(self._head_hash)
        self._chain.append(event)
        self._head_hash = event.chain_hash

    def verify(self) -> bool:
        running_hash = self.GENESIS_HASH
        for event in self._chain:
            expected = event.compute_hash(running_hash)
            if expected != event.chain_hash:
                return False
            running_hash = event.chain_hash
        return True

    def events(self) -> list[AuditEvent]:
        return list(self._chain)
