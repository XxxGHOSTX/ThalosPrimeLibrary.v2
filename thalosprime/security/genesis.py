"""
Security Layer — Section 13 of the TPL.v2 specification.

Implements Genesis Lock (trust root) and artifact state signing.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass

from thalosprime.core.artifact.canonical import CanonicalArtifact


# ---------------------------------------------------------------------------
# Genesis Lock
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class GenesisLock:
    """
    Trust root that binds a policy digest and an authority key (Section 13.1).

    In production this would bind hardware identity as well.  Here we use
    HMAC-SHA256 as the signing primitive.
    """

    policy_digest: str     # SHA-256 of the policy text
    authority_key: bytes   # Secret key material (never stored externally)
    created_at: int        # Unix epoch

    @classmethod
    def create(cls, policy_text: str, authority_key: bytes) -> "GenesisLock":
        digest = hashlib.sha256(policy_text.encode("utf-8")).hexdigest()
        return cls(
            policy_digest=digest,
            authority_key=authority_key,
            created_at=int(time.time()),
        )

    def sign_artifact(self, artifact: CanonicalArtifact) -> str:
        """
        Return an HMAC-SHA256 signature over the artifact's canonical fields.
        """
        payload = json.dumps(
            {
                "artifact_id": artifact.artifact_id,
                "canonical_content": artifact.canonical_content,
                "source_set": list(artifact.source_set),
                "provenance_path": list(artifact.provenance_path),
                "timestamp": artifact.timestamp,
                "confidence": artifact.confidence,
                "status": artifact.status,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hmac.new(self.authority_key, payload, hashlib.sha256).hexdigest()

    def verify_artifact(self, artifact: CanonicalArtifact, signature: str) -> bool:
        """Verify that *signature* was produced by this lock for *artifact*."""
        expected = self.sign_artifact(artifact)
        return hmac.compare_digest(expected, signature)
