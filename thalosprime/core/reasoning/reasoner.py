"""
Reasoning Layer — Section 9 of the TPL.v2 specification.

The reasoner transforms indexed artifacts and current belief state into
candidate propositions.  Reasoning proposes; only Validation admits.

Output contract (Section 9.2):
* candidate proposition
* derivation trace
* confidence score
* contradiction indicators
* validation handoff metadata
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from thalosprime.core.artifact.canonical import CanonicalArtifact
from thalosprime.core.belief.base import BeliefBase
from thalosprime.core.indexing.deterministic import CoordinateBundle


# ---------------------------------------------------------------------------
# Reasoning result
# ---------------------------------------------------------------------------

@dataclass
class CandidateProposition:
    """A proposed claim produced by the reasoning layer."""

    proposition: CanonicalArtifact
    derivation_trace: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    contradiction_indicators: list[str] = field(default_factory=list)
    handoff_metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "artifact_id": self.proposition.artifact_id,
            "derivation_trace": self.derivation_trace,
            "confidence_score": self.confidence_score,
            "contradiction_indicators": self.contradiction_indicators,
            "handoff_metadata": self.handoff_metadata,
        }


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class Reasoner(ABC):
    """Abstract contract for the reasoning layer."""

    @abstractmethod
    def derive(
        self,
        indexed_artifacts: list[tuple[CanonicalArtifact, CoordinateBundle]],
        belief_state: BeliefBase,
    ) -> list[CandidateProposition]:
        """
        Propose candidate claims from *indexed_artifacts* given *belief_state*.

        May propose many; Validator decides what is admitted.
        """


# ---------------------------------------------------------------------------
# Passthrough reasoner
# ---------------------------------------------------------------------------

class PassthroughReasoner(Reasoner):
    """
    Simple reasoner that treats each indexed artifact as its own candidate.

    Adds provenance annotation to the derivation trace and propagates the
    artifact's own confidence score.  Flags contradictions if an artifact
    with the same content already appears in the disputed or rejected set.
    """

    def derive(
        self,
        indexed_artifacts: list[tuple[CanonicalArtifact, CoordinateBundle]],
        belief_state: BeliefBase,
    ) -> list[CandidateProposition]:
        rejected_ids = set(belief_state.get_rejected())
        disputed_ids = set(belief_state.get_disputed())

        propositions: list[CandidateProposition] = []
        for artifact, bundle in indexed_artifacts:
            indicators: list[str] = []
            if artifact.artifact_id in rejected_ids:
                indicators.append(f"artifact {artifact.artifact_id} previously rejected")
            if artifact.artifact_id in disputed_ids:
                indicators.append(f"artifact {artifact.artifact_id} previously disputed")

            trace = [
                f"source: {src}" for src in artifact.source_set
            ] + [
                f"provenance: {step}" for step in artifact.provenance_path
            ] + [
                f"identity_coord: {bundle.identity_coord[:16]}...",
            ]

            propositions.append(CandidateProposition(
                proposition=artifact,
                derivation_trace=trace,
                confidence_score=artifact.confidence,
                contradiction_indicators=indicators,
                handoff_metadata={"coordinate_bundle": bundle.as_tuple()},
            ))

        return propositions
