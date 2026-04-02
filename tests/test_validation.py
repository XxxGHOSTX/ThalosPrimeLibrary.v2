"""
Unit tests for the validation layer.

Acceptance tests from Section 17.3:
* invalid claim never enters accepted state
* withheld evidence produces suspension, not invention
"""

from __future__ import annotations

import pytest
from thalosprime.core.artifact.canonical import CanonicalArtifact
from thalosprime.core.validation.validator import BasicValidator
from thalosprime.core.validation.facs import FACSBundle


def _valid_artifact(**overrides) -> CanonicalArtifact:
    defaults = dict(
        artifact_id="v-001",
        canonical_content="Water is H2O.",
        source_set=["chemistry-db"],
        provenance_path=["ingest", "normalize"],
        timestamp=1700000000,
        confidence=0.95,
        status="provisional",
    )
    defaults.update(overrides)
    return CanonicalArtifact.create(**defaults)


class TestBasicValidator:
    def test_valid_claim_passes(self):
        v = BasicValidator()
        result = v.validate(_valid_artifact())
        assert result.passed

    def test_missing_content_fails_canonicalization(self):
        v = BasicValidator()
        result = v.validate(_valid_artifact(canonical_content=""))
        assert not result.passed
        assert result.stage_reached == "canonicalization"
        assert any("MISSING" in f for f in result.facs.flags)

    def test_missing_sources_fails_source_binding(self):
        v = BasicValidator()
        result = v.validate(_valid_artifact(source_set=[]))
        assert not result.passed
        assert result.stage_reached == "source_binding"

    def test_missing_provenance_fails_consistency(self):
        v = BasicValidator()
        result = v.validate(_valid_artifact(provenance_path=[]))
        assert not result.passed
        assert result.stage_reached == "consistency"

    def test_zero_confidence_fails(self):
        v = BasicValidator()
        result = v.validate(_valid_artifact(confidence=0.0))
        assert not result.passed
        assert result.stage_reached == "confidence_assignment"

    def test_pre_rejected_fails_admission(self):
        v = BasicValidator()
        result = v.validate(_valid_artifact(status="rejected"))
        assert not result.passed
        assert result.stage_reached == "admission_control"

    def test_facs_bundle_populated_on_failure(self):
        v = BasicValidator()
        result = v.validate(_valid_artifact(source_set=[]))
        assert isinstance(result.facs, FACSBundle)
        assert result.facs.has_issues

    def test_all_stages_reached_on_valid(self):
        v = BasicValidator()
        result = v.validate(_valid_artifact())
        assert result.stage_reached == "admission_control"

    def test_to_dict_contains_required_keys(self):
        v = BasicValidator()
        result = v.validate(_valid_artifact())
        d = result.to_dict()
        assert "passed" in d
        assert "artifact_id" in d
        assert "stage_reached" in d
        assert "facs" in d
