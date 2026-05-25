"""Validate complexity-tier.schema.json against all four tiers (TINY/SMALL/MEDIUM/LARGE).

Regression tests for Bug A — schema desync with factory_complexity.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = (
    REPO_ROOT
    / ".aidlc-orchestrator"
    / "contracts"
    / "shared"
    / "complexity-tier.schema.json"
)

pytest.importorskip("jsonschema")
from jsonschema import Draft7Validator


# ── fixtures ───────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def schema_validator():
    schema = json.loads(SCHEMA_PATH.read_text())
    return Draft7Validator(schema)


# ── valid documents per tier ───────────────────────────────────────────────────


class TestValidDocuments:
    def test_tiny(self, schema_validator):
        doc = {
            "complexity_tier": "TINY",
            "skip_stages": [
                "story-writer",
                "unit-decomposer",
                "workflow-planner",
                "build-test-agent",
            ],
            "merge_codegen_gate": True,
            "reviewer_pool": [],
        }
        errors = list(schema_validator.iter_errors(doc))
        assert not errors

    def test_small(self, schema_validator):
        doc = {
            "complexity_tier": "SMALL",
            "skip_stages": ["story-writer", "unit-decomposer"],
            "merge_codegen_gate": True,
            "reviewer_pool": ["reviewer-code"],
        }
        errors = list(schema_validator.iter_errors(doc))
        assert not errors

    def test_medium(self, schema_validator):
        doc = {
            "complexity_tier": "MEDIUM",
            "skip_stages": ["story-writer"],
            "merge_codegen_gate": False,
            "reviewer_pool": [
                "reviewer-code",
                "reviewer-security",
                "reviewer-simplifier",
            ],
        }
        errors = list(schema_validator.iter_errors(doc))
        assert not errors

    def test_large(self, schema_validator):
        doc = {
            "complexity_tier": "LARGE",
            "skip_stages": [],
            "merge_codegen_gate": False,
            "reviewer_pool": [
                "reviewer-code",
                "reviewer-security",
                "reviewer-performance",
                "reviewer-simplifier",
            ],
        }
        errors = list(schema_validator.iter_errors(doc))
        assert not errors


# ── invariant violations that MUST be rejected ─────────────────────────────────


class TestRejectedDocuments:
    def test_unknown_tier(self, schema_validator):
        doc = {
            "complexity_tier": "GINORMOUS",
            "skip_stages": [],
            "merge_codegen_gate": True,
            "reviewer_pool": ["reviewer-code"],
        }
        errors = list(schema_validator.iter_errors(doc))
        assert any("GINORMOUS" in e.message for e in errors)

    def test_tiny_with_reviewers_rejected(self, schema_validator):
        """TINY conditional forces reviewer_pool maxItems=0."""
        doc = {
            "complexity_tier": "TINY",
            "skip_stages": [
                "story-writer",
                "unit-decomposer",
                "workflow-planner",
                "build-test-agent",
            ],
            "merge_codegen_gate": True,
            "reviewer_pool": ["reviewer-code"],
        }
        errors = list(schema_validator.iter_errors(doc))
        assert any("reviewer_pool" in str(e.absolute_path) for e in errors)

    def test_tiny_with_merge_gate_false_rejected(self, schema_validator):
        doc = {
            "complexity_tier": "TINY",
            "skip_stages": [
                "story-writer",
                "unit-decomposer",
                "workflow-planner",
                "build-test-agent",
            ],
            "merge_codegen_gate": False,
            "reviewer_pool": [],
        }
        errors = list(schema_validator.iter_errors(doc))
        assert any("merge_codegen_gate" in str(e.absolute_path) for e in errors)

    def test_large_with_skipped_stages_rejected(self, schema_validator):
        doc = {
            "complexity_tier": "LARGE",
            "skip_stages": ["story-writer"],
            "merge_codegen_gate": False,
            "reviewer_pool": [
                "reviewer-code",
                "reviewer-security",
                "reviewer-performance",
                "reviewer-simplifier",
            ],
        }
        errors = list(schema_validator.iter_errors(doc))
        assert any("skip_stages" in str(e.absolute_path) for e in errors)

    def test_unknown_skip_stage_rejected(self, schema_validator):
        doc = {
            "complexity_tier": "SMALL",
            "skip_stages": ["ship-agent"],
            "merge_codegen_gate": True,
            "reviewer_pool": ["reviewer-code"],
        }
        errors = list(schema_validator.iter_errors(doc))
        assert any("ship-agent" in e.message for e in errors)

    def test_unknown_reviewer_rejected(self, schema_validator):
        doc = {
            "complexity_tier": "SMALL",
            "skip_stages": ["story-writer", "unit-decomposer"],
            "merge_codegen_gate": True,
            "reviewer_pool": ["reviewer-llm"],
        }
        errors = list(schema_validator.iter_errors(doc))
        assert any("reviewer-llm" in e.message for e in errors)

    def test_duplicate_skip_stages_rejected(self, schema_validator):
        doc = {
            "complexity_tier": "SMALL",
            "skip_stages": ["story-writer", "story-writer"],
            "merge_codegen_gate": True,
            "reviewer_pool": ["reviewer-code"],
        }
        errors = list(schema_validator.iter_errors(doc))
        assert any("non-unique" in e.message.lower() for e in errors)

    def test_small_with_reviewer_simplifier_rejected(self, schema_validator):
        """SMALL tier pool is constrained by reviewer enum only; this is a valid
        enum value but tests that the allOf doesn't accidentally block it."""
        doc = {
            "complexity_tier": "SMALL",
            "skip_stages": ["story-writer", "unit-decomposer"],
            "merge_codegen_gate": True,
            "reviewer_pool": ["reviewer-code", "reviewer-simplifier"],
        }
        errors = list(schema_validator.iter_errors(doc))
        assert not errors


# ── edge cases ─────────────────────────────────────────────────────────────────


class TestEdgeCases:
    def test_missing_required_field(self, schema_validator):
        doc = {
            "complexity_tier": "TINY",
            "skip_stages": [],
            "merge_codegen_gate": True,
        }
        errors = list(schema_validator.iter_errors(doc))
        assert any("reviewer_pool" in e.message for e in errors)

    def test_additional_properties_allowed(self, schema_validator):
        doc = {
            "complexity_tier": "SMALL",
            "skip_stages": ["story-writer", "unit-decomposer"],
            "merge_codegen_gate": True,
            "reviewer_pool": ["reviewer-code"],
            "fast_path": False,
            "tokens_max": 500_000,
        }
        errors = list(schema_validator.iter_errors(doc))
        assert not errors
