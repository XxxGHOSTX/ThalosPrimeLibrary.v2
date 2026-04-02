"""
Validation Layer — Section 10 of the TPL.v2 specification.

The validator is the constitutional court of the architecture.  It must be
stricter than the reasoner.  A claim is admitted only if it passes every
validation stage defined in Section 10.1.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from thalosprime.core.artifact.canonical import CanonicalArtifact
from thalosprime.core.validation.facs import FACSBundle


# ---------------------------------------------------------------------------
# Validation result
# ---------------------------------------------------------------------------

@dataclass
class ValidationResult:
    """Structured outcome of a validation pass."""

    passed: bool
    artifact: CanonicalArtifact
    facs: FACSBundle
    stage_reached: str  # last stage completed before pass/fail

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "artifact_id": self.artifact.artifact_id,
            "stage_reached": self.stage_reached,
            "facs": self.facs.to_dict(),
        }


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class Validator(ABC):
    """Abstract contract for claim validation."""

    @abstractmethod
    def validate(self, candidate_claim: CanonicalArtifact) -> ValidationResult:
        """
        Evaluate *candidate_claim* against all validation stages.

        Returns a ValidationResult.  A result with passed=False means the
        claim must not enter the accepted belief base.
        """


# ---------------------------------------------------------------------------
# Concrete implementation
# ---------------------------------------------------------------------------

class BasicValidator(Validator):
    """
    Validates a candidate claim against the six stages in Section 10.1:

    1. canonicalization  — artifact_id and content must be non-empty
    2. source binding    — source_set must be non-empty
    3. consistency       — provenance_path must be non-empty
    4. contradiction     — placeholder (no cross-claim store in basic mode)
    5. confidence        — confidence must be > 0
    6. admission control — status must be valid
    """

    STAGES = [
        "canonicalization",
        "source_binding",
        "consistency",
        "contradiction_search",
        "confidence_assignment",
        "admission_control",
    ]

    def validate(self, candidate_claim: CanonicalArtifact) -> ValidationResult:
        facs = FACSBundle()
        stage = "init"

        # 1. canonicalization
        stage = "canonicalization"
        if not candidate_claim.artifact_id or not candidate_claim.canonical_content:
            facs.add_flag("MISSING_CONTENT_OR_ID")
            facs.add_suspension("Claim lacks artifact_id or canonical_content")
            return ValidationResult(passed=False, artifact=candidate_claim, facs=facs, stage_reached=stage)

        # 2. source binding
        stage = "source_binding"
        if not candidate_claim.source_set:
            facs.add_flag("NO_SOURCES")
            facs.add_suspension("Claim has no source binding")
            return ValidationResult(passed=False, artifact=candidate_claim, facs=facs, stage_reached=stage)

        # 3. consistency
        stage = "consistency"
        if not candidate_claim.provenance_path:
            facs.add_flag("NO_PROVENANCE_PATH")
            facs.add_annotation("Claim lacks a provenance path; treated as unverifiable")
            return ValidationResult(passed=False, artifact=candidate_claim, facs=facs, stage_reached=stage)

        # 4. contradiction search (basic — no cross-claim store)
        stage = "contradiction_search"
        # No contradictions detectable at this level; mark for annotation
        facs.add_annotation("No cross-claim contradiction store available in BasicValidator")

        # 5. confidence assignment
        stage = "confidence_assignment"
        if candidate_claim.confidence <= 0.0:
            facs.add_flag("ZERO_CONFIDENCE")
            facs.add_suspension("Claim has zero or negative confidence; cannot admit")
            return ValidationResult(passed=False, artifact=candidate_claim, facs=facs, stage_reached=stage)

        # 6. admission control
        stage = "admission_control"
        if candidate_claim.status == "rejected":
            facs.add_flag("PRE_REJECTED")
            return ValidationResult(passed=False, artifact=candidate_claim, facs=facs, stage_reached=stage)

        return ValidationResult(passed=True, artifact=candidate_claim, facs=facs, stage_reached=stage)
