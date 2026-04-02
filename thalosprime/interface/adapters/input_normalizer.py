"""
Input Normalizer — normalises raw user input before it enters the pipeline.
"""

from __future__ import annotations


class InputNormalizer:
    """
    Strips whitespace, collapses internal runs, and enforces max length.
    """

    def __init__(self, max_length: int = 4096) -> None:
        self._max_length = max_length

    def normalize(self, raw: str) -> str:
        if not raw:
            raise ValueError("Input must not be empty")
        normalized = " ".join(raw.split())
        if len(normalized) > self._max_length:
            raise ValueError(
                f"Input exceeds maximum length of {self._max_length} characters"
            )
        return normalized
