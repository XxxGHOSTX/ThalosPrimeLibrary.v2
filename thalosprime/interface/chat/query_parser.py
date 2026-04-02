"""
Query Parser — translates raw user input into a CanonicalArtifact query object.
"""

from __future__ import annotations

import hashlib
import time

from thalosprime.core.artifact.canonical import CanonicalArtifact


class QueryParser:
    """
    Parses a user input string into a CanonicalArtifact (Section 24.7).

    The resulting artifact has status='provisional' and serves as a query
    seed that is passed into the indexing and reasoning pipeline.
    """

    def parse(self, user_input: str, session_id: str = "") -> CanonicalArtifact:
        if not user_input or not user_input.strip():
            raise ValueError("user_input must not be empty")

        # Derive a stable artifact_id from the input content + session
        seed = f"{session_id}:{user_input}"
        artifact_id = "query:" + hashlib.sha256(seed.encode()).hexdigest()[:16]

        return CanonicalArtifact.create(
            artifact_id=artifact_id,
            canonical_content=user_input.strip(),
            source_set=["user_input"],
            provenance_path=["query_parser"],
            timestamp=int(time.time()),
            confidence=1.0,
            status="provisional",
            metadata={"session_id": session_id, "raw_input": user_input},
        )
