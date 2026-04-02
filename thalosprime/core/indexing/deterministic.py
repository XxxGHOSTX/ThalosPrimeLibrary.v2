"""
Deterministic Indexing — Section 6 of the TPL.v2 specification.

A coordinate is a stable, content-derived address for a CanonicalArtifact.
The indexer produces coordinates that are:

* stable across runs (same input → same coordinate)
* multi-layered (identity, semantic, provenance, version, trust, neighbourhood)
* local — no network calls
"""

from __future__ import annotations

import hashlib
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

from thalosprime.core.artifact.canonical import CanonicalArtifact


# ---------------------------------------------------------------------------
# Coordinate bundle
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CoordinateBundle:
    """
    Multi-layered coordinate for a single artifact (Section 4.3).

    Each dimension encodes a different epistemic facet so that similarity
    in one dimension does not accidentally imply identity in another.
    """

    identity_coord: str       # c₁ — derived from artifact_id + content
    semantic_coord: str       # c₂ — derived from canonical_content only
    provenance_coord: str     # c₃ — derived from source_set + provenance_path
    version_coord: str        # c₄ — derived from timestamp + metadata
    trust_coord: str          # c₅ — derived from confidence + status

    def as_tuple(self) -> tuple[str, str, str, str, str]:
        return (
            self.identity_coord,
            self.semantic_coord,
            self.provenance_coord,
            self.version_coord,
            self.trust_coord,
        )


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class DeterministicIndexer(ABC):
    """Abstract contract for coordinate generation and resolution."""

    @abstractmethod
    def encode(self, artifact: CanonicalArtifact) -> CoordinateBundle:
        """Map a canonical artifact to its stable coordinate bundle."""

    @abstractmethod
    def decode(self, coordinate: str) -> CanonicalArtifact | None:
        """
        Reverse-map a primary (identity) coordinate to its stored artifact.

        Returns *None* if the coordinate is unknown.
        """


# ---------------------------------------------------------------------------
# Simple concrete implementation
# ---------------------------------------------------------------------------

def _sha256(data: str | bytes) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def _canonical_json(obj: object) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


class SimpleDeterministicIndexer(DeterministicIndexer):
    """
    SHA-256-based deterministic indexer.

    All five coordinate dimensions are derived deterministically from the
    artifact's fields.  The internal registry maps identity coordinates back
    to artifacts so that *decode* is supported within a single process.
    """

    def __init__(self) -> None:
        self._registry: dict[str, CanonicalArtifact] = {}

    # ------------------------------------------------------------------
    # encode
    # ------------------------------------------------------------------

    def encode(self, artifact: CanonicalArtifact) -> CoordinateBundle:
        bundle = CoordinateBundle(
            identity_coord=self._identity(artifact),
            semantic_coord=self._semantic(artifact),
            provenance_coord=self._provenance(artifact),
            version_coord=self._version(artifact),
            trust_coord=self._trust(artifact),
        )
        self._registry[bundle.identity_coord] = artifact
        return bundle

    # ------------------------------------------------------------------
    # decode
    # ------------------------------------------------------------------

    def decode(self, coordinate: str) -> CanonicalArtifact | None:
        return self._registry.get(coordinate)

    # ------------------------------------------------------------------
    # Coordinate generators (one per dimension)
    # ------------------------------------------------------------------

    @staticmethod
    def _identity(a: CanonicalArtifact) -> str:
        payload = _canonical_json({
            "artifact_id": a.artifact_id,
            "canonical_content": a.canonical_content,
        })
        return _sha256(payload)

    @staticmethod
    def _semantic(a: CanonicalArtifact) -> str:
        return _sha256(a.canonical_content)

    @staticmethod
    def _provenance(a: CanonicalArtifact) -> str:
        payload = _canonical_json({
            "source_set": list(a.source_set),
            "provenance_path": list(a.provenance_path),
        })
        return _sha256(payload)

    @staticmethod
    def _version(a: CanonicalArtifact) -> str:
        payload = _canonical_json({
            "timestamp": a.timestamp,
            "metadata": a.metadata,
        })
        return _sha256(payload)

    @staticmethod
    def _trust(a: CanonicalArtifact) -> str:
        payload = _canonical_json({
            "confidence": a.confidence,
            "status": a.status,
        })
        return _sha256(payload)
