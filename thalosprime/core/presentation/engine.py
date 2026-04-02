"""
Presentation Layer — Section 12 of the TPL.v2 specification.

Transforms verified internal artifacts into human-readable and
machine-readable outputs without hiding the provenance chain.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from typing import Any

from thalosprime.core.artifact.canonical import CanonicalArtifact
from thalosprime.core.validation.facs import FACSBundle


# ---------------------------------------------------------------------------
# Epistemic output (Section 24.3 dual-channel response model)
# ---------------------------------------------------------------------------

@dataclass
class EpistemicOutput:
    """
    Dual-channel output object.

    human_layer  — natural language or structured summary
    machine_layer — machine-readable provenance, coordinates, validation state
    """

    human_layer: str
    machine_layer: dict[str, Any]

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(
            {"human": self.human_layer, "epistemic": self.machine_layer},
            indent=indent,
            default=str,
        )


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class PresentationEngine(ABC):
    """Abstract contract for the presentation layer."""

    @abstractmethod
    def render(self, epistemic_object: CanonicalArtifact) -> EpistemicOutput:
        """Render *epistemic_object* as a dual-channel EpistemicOutput."""


# ---------------------------------------------------------------------------
# Concrete implementation
# ---------------------------------------------------------------------------

class DefaultPresentationEngine(PresentationEngine):
    """
    Renders a CanonicalArtifact as a dual-channel output.

    The human layer is a prose summary.
    The machine layer preserves full artifact metadata for downstream audit.
    """

    def render(
        self,
        epistemic_object: CanonicalArtifact,
        facs: FACSBundle | None = None,
    ) -> EpistemicOutput:
        a = epistemic_object

        human = (
            f"[{a.status.upper()}] {a.artifact_id}\n"
            f"Content: {a.canonical_content}\n"
            f"Sources: {', '.join(a.source_set)}\n"
            f"Confidence: {a.confidence:.2f}\n"
            f"Provenance: {' → '.join(a.provenance_path)}"
        )

        machine: dict[str, Any] = {
            "artifact_id": a.artifact_id,
            "status": a.status,
            "confidence": a.confidence,
            "timestamp": a.timestamp,
            "source_set": list(a.source_set),
            "provenance_path": list(a.provenance_path),
            "canonical_content": a.canonical_content,
            "metadata": a.metadata,
        }
        if facs is not None:
            machine["facs"] = facs.to_dict()

        return EpistemicOutput(human_layer=human, machine_layer=machine)

    def render_table(self, artifacts: list[CanonicalArtifact]) -> str:
        """Render a list of artifacts as a plain-text evidence table."""
        if not artifacts:
            return "(no artifacts)"
        lines = [
            f"{'ID':<36} {'STATUS':<12} {'CONF':>6}  CONTENT",
            "-" * 80,
        ]
        for a in artifacts:
            content_preview = a.canonical_content[:40].replace("\n", " ")
            lines.append(
                f"{a.artifact_id:<36} {a.status:<12} {a.confidence:>6.2f}  {content_preview}"
            )
        return "\n".join(lines)

    def render_lineage_graph(self, artifact: CanonicalArtifact) -> str:
        """Return a textual lineage graph for an artifact."""
        steps = list(artifact.provenance_path)
        if not steps:
            return f"{artifact.artifact_id} (no lineage)"
        chain = " → ".join(steps) + f" → {artifact.artifact_id}"
        return chain
