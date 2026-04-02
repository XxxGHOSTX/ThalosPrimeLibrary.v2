"""
Output Formatter — formats EpistemicOutput for different surfaces.
"""

from __future__ import annotations

import json

from thalosprime.core.presentation.engine import EpistemicOutput


class OutputFormatter:
    """
    Converts an EpistemicOutput to various surface-specific formats.
    """

    def to_text(self, output: EpistemicOutput) -> str:
        """Plain-text representation (human layer only)."""
        return output.human_layer

    def to_json(self, output: EpistemicOutput, indent: int = 2) -> str:
        """Full dual-channel JSON."""
        return output.to_json(indent=indent)

    def to_machine_dict(self, output: EpistemicOutput) -> dict:
        """Machine layer only."""
        return output.machine_layer
