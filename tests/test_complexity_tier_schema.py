from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads(
    (REPO_ROOT / ".aidlc-orchestrator" / "contracts" / "shared" / "complexity-tier.schema.json").read_text()
)


@pytest.fixture
def validator():
    return jsonschema.Draft7Validator(SCHEMA)


class TestComplexityTierSchema:
    def test_large_passes(self, validator):
        doc = {
            "complexity_tier": "LARGE",
            "skip_stages": [],
            "merge_codegen_gate": False,
            "reviewer_pool": ["reviewer-code", "reviewer-security", "reviewer-performance", "reviewer-simplifier"],
        }
        errors = list(validator.iter_errors(doc))
        assert len(errors) == 0

    def test_tiny_rejected(self, validator):
        doc = {"complexity_tier": "TINY"}
        errors = list(validator.iter_errors(doc))
        assert len(errors) >= 1

    def test_small_rejected(self, validator):
        doc = {"complexity_tier": "SMALL"}
        errors = list(validator.iter_errors(doc))
        assert len(errors) >= 1

    def test_medium_rejected(self, validator):
        doc = {"complexity_tier": "MEDIUM"}
        errors = list(validator.iter_errors(doc))
        assert len(errors) >= 1

    def test_skip_stages_must_be_empty(self, validator):
        doc = {
            "complexity_tier": "LARGE",
            "skip_stages": ["story-writer"],
        }
        errors = list(validator.iter_errors(doc))
        assert len(errors) >= 1

    def test_reviewer_pool_must_have_4(self, validator):
        doc = {
            "complexity_tier": "LARGE",
            "reviewer_pool": ["reviewer-code"],
        }
        errors = list(validator.iter_errors(doc))
        assert len(errors) >= 1
