"""
Canonical Artifact — the atomic epistemic unit in TPL.v2.

Every knowledge object carries identity, content, provenance, validation state,
and confidence state. Artifacts are immutable once created; state transitions
produce new versioned artifacts rather than mutating in place.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class Artifact(ABC):
    """Abstract base for all knowledge objects managed by TPL.v2."""

    @property
    @abstractmethod
    def artifact_id(self) -> str:
        """Stable unique identifier."""

    @property
    @abstractmethod
    def canonical_content(self) -> str:
        """Normalised content string."""

    @property
    @abstractmethod
    def source_set(self) -> list[str]:
        """Ordered list of source references."""

    @property
    @abstractmethod
    def provenance_path(self) -> list[str]:
        """Ordered chain of transformations applied to the raw source."""

    @property
    @abstractmethod
    def timestamp(self) -> int:
        """Unix epoch timestamp (integer seconds)."""

    @property
    @abstractmethod
    def confidence(self) -> float:
        """Epistemic confidence in [0.0, 1.0]."""

    @property
    @abstractmethod
    def status(self) -> str:
        """Validation/belief status string."""


# ---------------------------------------------------------------------------
# Canonical artifact (concrete, frozen dataclass)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CanonicalArtifact:
    """
    Frozen, hashable representation of a canonical epistemic artifact.

    Required fields map directly to Section 5.1 of the TPL.v2 specification.
    Extended fields (Section 5.2) are kept in *metadata*.
    """

    artifact_id: str
    canonical_content: str
    source_set: tuple[str, ...]
    provenance_path: tuple[str, ...]
    timestamp: int
    confidence: float
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Validation helpers
    # ------------------------------------------------------------------

    def __post_init__(self) -> None:
        if not self.artifact_id:
            raise ValueError("artifact_id must not be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be in [0.0, 1.0]")
        valid_statuses = {
            "accepted", "provisional", "disputed", "rejected", "suspended",
        }
        if self.status not in valid_statuses:
            raise ValueError(
                f"status '{self.status}' is not one of {valid_statuses}"
            )

    def __hash__(self) -> int:
        # Hash on stable identity fields; metadata dict is intentionally excluded
        return hash((
            self.artifact_id,
            self.canonical_content,
            self.source_set,
            self.provenance_path,
            self.timestamp,
            self.confidence,
            self.status,
        ))

    # ------------------------------------------------------------------
    # Convenience constructors
    # ------------------------------------------------------------------

    @classmethod
    def create(
        cls,
        artifact_id: str,
        canonical_content: str,
        source_set: list[str] | tuple[str, ...],
        provenance_path: list[str] | tuple[str, ...],
        timestamp: int,
        confidence: float,
        status: str = "provisional",
        metadata: dict[str, Any] | None = None,
    ) -> "CanonicalArtifact":
        return cls(
            artifact_id=artifact_id,
            canonical_content=canonical_content,
            source_set=tuple(source_set),
            provenance_path=tuple(provenance_path),
            timestamp=timestamp,
            confidence=confidence,
            status=status,
            metadata=metadata or {},
        )

    def with_status(self, new_status: str) -> "CanonicalArtifact":
        """Return a new artifact identical to this one except for *status*."""
        return CanonicalArtifact(
            artifact_id=self.artifact_id,
            canonical_content=self.canonical_content,
            source_set=self.source_set,
            provenance_path=self.provenance_path,
            timestamp=self.timestamp,
            confidence=self.confidence,
            status=new_status,
            metadata=dict(self.metadata),
        )
