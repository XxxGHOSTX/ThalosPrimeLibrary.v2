"""
Context Tracker — tracks the active artifact context for a chat session.
"""

from __future__ import annotations

from thalosprime.core.artifact.canonical import CanonicalArtifact


class ContextTracker:
    """
    Maintains the set of artifact IDs referenced during a session (Section 24.5).

    Session state is transient and separate from the belief base.
    """

    def __init__(self) -> None:
        self._referenced: dict[str, CanonicalArtifact] = {}
        self._derivations: list[str] = []

    def add_reference(self, artifact: CanonicalArtifact) -> None:
        """Register *artifact* as part of the current context."""
        self._referenced[artifact.artifact_id] = artifact

    def add_derivation(self, note: str) -> None:
        """Log a temporary derivation note."""
        self._derivations.append(note)

    def get_context(self) -> dict[str, CanonicalArtifact]:
        """Return all currently referenced artifacts."""
        return dict(self._referenced)

    def get_derivations(self) -> list[str]:
        return list(self._derivations)

    def clear(self) -> None:
        """Clear session context (e.g. on session end)."""
        self._referenced.clear()
        self._derivations.clear()
