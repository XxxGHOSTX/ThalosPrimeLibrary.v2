"""
Distributed Validation — Section 10.2 of the TPL.v2 specification.

Optional module for multi-node veridiction.  Disagreement is retained,
not hidden.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from thalosprime.core.artifact.canonical import CanonicalArtifact
from thalosprime.core.validation.validator import ValidationResult, Validator


@dataclass
class NodeVote:
    node_id: str
    passed: bool
    reason: str


@dataclass
class DistributedValidationResult:
    """Aggregated result from multiple validation nodes."""

    artifact_id: str
    votes: list[NodeVote] = field(default_factory=list)

    @property
    def consensus_passed(self) -> bool:
        if not self.votes:
            return False
        passed_count = sum(1 for v in self.votes if v.passed)
        return passed_count > len(self.votes) / 2

    @property
    def dissent_count(self) -> int:
        return sum(1 for v in self.votes if not v.passed)

    def to_dict(self) -> dict:
        return {
            "artifact_id": self.artifact_id,
            "consensus_passed": self.consensus_passed,
            "votes": [
                {"node_id": v.node_id, "passed": v.passed, "reason": v.reason}
                for v in self.votes
            ],
            "dissent_count": self.dissent_count,
        }


class DistributedValidator:
    """
    Runs a claim through a set of Validator nodes and aggregates votes.

    Disagreement is retained in the result (Section 10.2).
    """

    def __init__(self, nodes: list[tuple[str, Validator]]) -> None:
        """*nodes* is a list of (node_id, Validator) pairs."""
        self._nodes = nodes

    def validate(self, candidate: CanonicalArtifact) -> DistributedValidationResult:
        result = DistributedValidationResult(artifact_id=candidate.artifact_id)
        for node_id, validator in self._nodes:
            vr: ValidationResult = validator.validate(candidate)
            reason = vr.stage_reached if not vr.passed else "all stages passed"
            result.votes.append(NodeVote(
                node_id=node_id,
                passed=vr.passed,
                reason=reason,
            ))
        return result
