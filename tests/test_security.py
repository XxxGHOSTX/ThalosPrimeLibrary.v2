"""
Unit tests for the security module (GenesisLock).
"""

from __future__ import annotations

import pytest
from thalosprime.core.artifact.canonical import CanonicalArtifact
from thalosprime.security.genesis import GenesisLock


def _artifact() -> CanonicalArtifact:
    return CanonicalArtifact.create(
        artifact_id="sec-001",
        canonical_content="Secure content",
        source_set=["trusted-source"],
        provenance_path=["ingest"],
        timestamp=1700000000,
        confidence=0.99,
        status="accepted",
    )


class TestGenesisLock:
    def test_sign_and_verify(self):
        lock = GenesisLock.create("policy text", b"secret-key-material")
        a = _artifact()
        sig = lock.sign_artifact(a)
        assert lock.verify_artifact(a, sig)

    def test_wrong_signature_fails(self):
        lock = GenesisLock.create("policy text", b"secret-key-material")
        a = _artifact()
        assert not lock.verify_artifact(a, "bad_signature")

    def test_different_content_different_signature(self):
        lock = GenesisLock.create("policy text", b"secret-key-material")
        a = _artifact()
        b = CanonicalArtifact.create(
            artifact_id="sec-002",
            canonical_content="Different content",
            source_set=["trusted-source"],
            provenance_path=["ingest"],
            timestamp=1700000000,
            confidence=0.99,
            status="accepted",
        )
        sig_a = lock.sign_artifact(a)
        sig_b = lock.sign_artifact(b)
        assert sig_a != sig_b

    def test_policy_digest_deterministic(self):
        lock1 = GenesisLock.create("same policy", b"key")
        lock2 = GenesisLock.create("same policy", b"key")
        assert lock1.policy_digest == lock2.policy_digest
