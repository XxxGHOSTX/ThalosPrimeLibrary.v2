"""
Internal Babel Archive — Section 4 of the TPL.v2 specification.

The archive is a structured epistemic space rather than a flat database.
Retrieval recovers a claim together with its admissibility conditions.

Key properties:
* stable address generation
* deterministic reconstruction
* version-aware lineage
* semantic neighbourhood discovery
* trust-state access control
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from thalosprime.core.artifact.canonical import CanonicalArtifact
from thalosprime.core.indexing.deterministic import (
    CoordinateBundle,
    SimpleDeterministicIndexer,
)


# ---------------------------------------------------------------------------
# Policy context
# ---------------------------------------------------------------------------

@dataclass
class PolicyContext:
    """
    Governs which artifacts may be reconstructed from the archive.

    Reconstruction is policy-gated (Section 4.4).
    """

    allow_statuses: frozenset[str] = field(
        default_factory=lambda: frozenset({
            "accepted", "provisional", "suspended",
        })
    )
    require_min_confidence: float = 0.0

    def permits(self, artifact: CanonicalArtifact) -> bool:
        if artifact.status not in self.allow_statuses:
            return False
        if artifact.confidence < self.require_min_confidence:
            return False
        return True


# ---------------------------------------------------------------------------
# Stored object
# ---------------------------------------------------------------------------

@dataclass
class StoredObject:
    """
    Full epistemic package stored in the archive (Section 4.2).

    Includes the artifact, its coordinate bundle, and a version history.
    """

    artifact: CanonicalArtifact
    coordinate_bundle: CoordinateBundle
    version_history: list[CanonicalArtifact] = field(default_factory=list)

    @property
    def provenance_path(self) -> tuple[str, ...]:
        return self.artifact.provenance_path

    @property
    def trust_state(self) -> str:
        return self.artifact.status


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class InternalBabelArchive(ABC):
    """Abstract contract for the internal coordinate archive."""

    @abstractmethod
    def store(self, artifact: CanonicalArtifact) -> CoordinateBundle:
        """Store *artifact* and return its coordinate bundle."""

    @abstractmethod
    def resolve(self, coordinate: str) -> StoredObject | None:
        """Resolve an identity coordinate to its stored object."""

    @abstractmethod
    def reconstruct(
        self, coordinate: str, policy_context: PolicyContext
    ) -> CanonicalArtifact | None:
        """
        Reconstruct an artifact from its coordinate under *policy_context*.

        Returns None if the policy does not permit access or the coordinate
        is unknown.
        """

    @abstractmethod
    def semantic_neighbourhood(
        self, coordinate: str, *, limit: int = 10
    ) -> list[StoredObject]:
        """
        Return up to *limit* stored objects whose semantic coordinate matches
        the one at *coordinate* or is in the same neighbourhood bucket.
        """


# ---------------------------------------------------------------------------
# Concrete in-memory implementation
# ---------------------------------------------------------------------------

class InMemoryBabelArchive(InternalBabelArchive):
    """
    In-memory archive backed by SimpleDeterministicIndexer.

    Behaves like a Merkle-style content-addressed structure (Section 6.3):
    identity is derived from content, and the same canonical artifact always
    resolves to the same coordinate.
    """

    def __init__(self) -> None:
        self._indexer = SimpleDeterministicIndexer()
        # identity_coord → StoredObject
        self._store: dict[str, StoredObject] = {}
        # semantic_coord → list[identity_coord] (neighbourhood index)
        self._semantic_index: dict[str, list[str]] = {}

    # ------------------------------------------------------------------
    # store
    # ------------------------------------------------------------------

    def store(self, artifact: CanonicalArtifact) -> CoordinateBundle:
        bundle = self._indexer.encode(artifact)
        identity = bundle.identity_coord
        semantic = bundle.semantic_coord

        if identity in self._store:
            # Version-aware lineage: append to history
            existing = self._store[identity]
            existing.version_history.append(artifact)
        else:
            self._store[identity] = StoredObject(
                artifact=artifact,
                coordinate_bundle=bundle,
            )

        # Update semantic neighbourhood index
        self._semantic_index.setdefault(semantic, [])
        if identity not in self._semantic_index[semantic]:
            self._semantic_index[semantic].append(identity)

        return bundle

    # ------------------------------------------------------------------
    # resolve
    # ------------------------------------------------------------------

    def resolve(self, coordinate: str) -> StoredObject | None:
        return self._store.get(coordinate)

    # ------------------------------------------------------------------
    # reconstruct
    # ------------------------------------------------------------------

    def reconstruct(
        self, coordinate: str, policy_context: PolicyContext
    ) -> CanonicalArtifact | None:
        stored = self._store.get(coordinate)
        if stored is None:
            return None
        if not policy_context.permits(stored.artifact):
            return None
        return stored.artifact

    # ------------------------------------------------------------------
    # semantic neighbourhood
    # ------------------------------------------------------------------

    def semantic_neighbourhood(
        self, coordinate: str, *, limit: int = 10
    ) -> list[StoredObject]:
        stored = self._store.get(coordinate)
        if stored is None:
            return []
        semantic = stored.coordinate_bundle.semantic_coord
        neighbours_ids = self._semantic_index.get(semantic, [])
        results: list[StoredObject] = []
        for nid in neighbours_ids[:limit]:
            obj = self._store.get(nid)
            if obj is not None:
                results.append(obj)
        return results
