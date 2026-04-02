"""
Belief Base — Section 7 of the TPL.v2 specification.

The belief base is the persistent memory of epistemic status.  It is
append-aware and audit-preserving: no prior state is silently overwritten.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable

from thalosprime.core.artifact.canonical import CanonicalArtifact


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BeliefBase(ABC):
    """Abstract contract for the belief base."""

    @abstractmethod
    def accept(self, claim: CanonicalArtifact) -> None:
        """Admit a validated claim into the accepted set."""

    @abstractmethod
    def dispute(self, claim: CanonicalArtifact) -> None:
        """Mark a claim as disputed (conflicting evidence)."""

    @abstractmethod
    def reject(self, claim: CanonicalArtifact) -> None:
        """Explicitly reject a claim."""

    @abstractmethod
    def suspend(self, claim: CanonicalArtifact) -> None:
        """Suspend a claim pending more evidence."""

    @abstractmethod
    def provisional(self, claim: CanonicalArtifact) -> None:
        """Admit a claim provisionally (not yet fully validated)."""

    @abstractmethod
    def query(self, predicate: Callable[[CanonicalArtifact], bool]) -> list[CanonicalArtifact]:
        """Return all claims from any state that satisfy *predicate*."""

    @abstractmethod
    def get_accepted(self) -> dict[str, CanonicalArtifact]:
        """Return the accepted belief set."""

    @abstractmethod
    def get_disputed(self) -> dict[str, CanonicalArtifact]:
        """Return the disputed belief set."""

    @abstractmethod
    def get_rejected(self) -> dict[str, CanonicalArtifact]:
        """Return the rejected belief set."""

    @abstractmethod
    def get_provisional(self) -> dict[str, CanonicalArtifact]:
        """Return the provisional belief set."""

    @abstractmethod
    def get_suspended(self) -> dict[str, CanonicalArtifact]:
        """Return the suspended belief set."""


# ---------------------------------------------------------------------------
# In-memory implementation
# ---------------------------------------------------------------------------

class InMemoryBeliefBase(BeliefBase):
    """
    Concrete in-memory belief base.

    State transitions are append-aware: moving a claim between epistemic
    states records the transition rather than silently overwriting it.
    The audit log is separate (handled by AuditTrail); here each mutation
    stores a transition record in *_history*.
    """

    def __init__(self) -> None:
        self._accepted: dict[str, CanonicalArtifact] = {}
        self._disputed: dict[str, CanonicalArtifact] = {}
        self._rejected: dict[str, CanonicalArtifact] = {}
        self._provisional: dict[str, CanonicalArtifact] = {}
        self._suspended: dict[str, CanonicalArtifact] = {}
        # Append-only transition log: (artifact_id, from_state, to_state)
        self._history: list[tuple[str, str | None, str]] = []

    # ------------------------------------------------------------------
    # State mutation helpers
    # ------------------------------------------------------------------

    def _remove_from_all(self, artifact_id: str) -> str | None:
        """Remove artifact from all state buckets; return previous state."""
        prev: str | None = None
        for state, bucket in self._all_buckets():
            if artifact_id in bucket:
                del bucket[artifact_id]
                prev = state
        return prev

    def _all_buckets(self) -> list[tuple[str, dict[str, CanonicalArtifact]]]:
        return [
            ("accepted", self._accepted),
            ("disputed", self._disputed),
            ("rejected", self._rejected),
            ("provisional", self._provisional),
            ("suspended", self._suspended),
        ]

    def _transition(self, claim: CanonicalArtifact, new_state: str) -> None:
        prev = self._remove_from_all(claim.artifact_id)
        self._history.append((claim.artifact_id, prev, new_state))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def accept(self, claim: CanonicalArtifact) -> None:
        self._transition(claim, "accepted")
        self._accepted[claim.artifact_id] = claim

    def dispute(self, claim: CanonicalArtifact) -> None:
        self._transition(claim, "disputed")
        self._disputed[claim.artifact_id] = claim

    def reject(self, claim: CanonicalArtifact) -> None:
        self._transition(claim, "rejected")
        self._rejected[claim.artifact_id] = claim

    def suspend(self, claim: CanonicalArtifact) -> None:
        self._transition(claim, "suspended")
        self._suspended[claim.artifact_id] = claim

    def provisional(self, claim: CanonicalArtifact) -> None:
        self._transition(claim, "provisional")
        self._provisional[claim.artifact_id] = claim

    def query(self, predicate: Callable[[CanonicalArtifact], bool]) -> list[CanonicalArtifact]:
        results: list[CanonicalArtifact] = []
        for _, bucket in self._all_buckets():
            results.extend(c for c in bucket.values() if predicate(c))
        return results

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_accepted(self) -> dict[str, CanonicalArtifact]:
        return dict(self._accepted)

    def get_disputed(self) -> dict[str, CanonicalArtifact]:
        return dict(self._disputed)

    def get_rejected(self) -> dict[str, CanonicalArtifact]:
        return dict(self._rejected)

    def get_provisional(self) -> dict[str, CanonicalArtifact]:
        return dict(self._provisional)

    def get_suspended(self) -> dict[str, CanonicalArtifact]:
        return dict(self._suspended)

    @property
    def history(self) -> list[tuple[str, str | None, str]]:
        """Read-only view of state-transition history."""
        return list(self._history)
