"""Validate code-generator.output.v1.json skill_compliance minItems conditional.

Regression test for Bug 4 — FAST_PATH runs with < 8 skills were rejected.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = (
    REPO_ROOT
    / ".aidlc-orchestrator"
    / "contracts"
    / "code-generator.output.v1.json"
)

pytest.importorskip("jsonschema")
from jsonschema import Draft7Validator


@pytest.fixture(scope="session")
def validator():
    return Draft7Validator(json.loads(SCHEMA_PATH.read_text()))


def _make_doc(fast_path: bool, n_skills: int, **overrides) -> dict:
    skills = [
        {"skill": f"skill-{i}", "status": "PASS",
         "evidence": "test evidence"}
        for i in range(n_skills)
    ]
    doc = {
        "status": "complete",
        "unit_name": "test-unit",
        "sub_stage": "generated",
        "artifacts": [
            {"path": "src/main.py", "kind": "source",
             "hash": "abc123"}
        ],
        "audit_entries": ["test entry"],
        "skill_compliance": skills,
        "fast_path": fast_path,
        **overrides,
    }
    return doc


class TestFastPathMinItems:
    def test_fast_path_with_2_skills_passes(self, validator):
        doc = _make_doc(fast_path=True, n_skills=2)
        errors = list(validator.iter_errors(doc))
        assert not errors, [e.message for e in errors]

    def test_fast_path_with_8_skills_passes(self, validator):
        doc = _make_doc(fast_path=True, n_skills=8)
        errors = list(validator.iter_errors(doc))
        assert not errors

    def test_fast_path_with_0_skills_fails(self, validator):
        doc = _make_doc(fast_path=True, n_skills=0)
        errors = list(validator.iter_errors(doc))
        assert errors

    def test_fast_path_with_1_skill_fails(self, validator):
        doc = _make_doc(fast_path=True, n_skills=1)
        errors = list(validator.iter_errors(doc))
        assert errors


class TestNormalPathMinItems:
    def test_normal_with_8_skills_passes(self, validator):
        doc = _make_doc(fast_path=False, n_skills=8)
        errors = list(validator.iter_errors(doc))
        assert not errors, [e.message for e in errors]

    def test_normal_with_2_skills_fails(self, validator):
        doc = _make_doc(fast_path=False, n_skills=2)
        errors = list(validator.iter_errors(doc))
        assert errors

    def test_normal_with_0_skills_fails(self, validator):
        doc = _make_doc(fast_path=False, n_skills=0)
        errors = list(validator.iter_errors(doc))
        assert errors

    def test_normal_with_7_skills_fails(self, validator):
        doc = _make_doc(fast_path=False, n_skills=7)
        errors = list(validator.iter_errors(doc))
        assert errors


class TestFastPathDefault:
    def test_fast_path_missing_requires_8(self, validator):
        """When fast_path is absent, the allOf's const: false condition
        matches vacuously (absent property satisfies properties keyword),
        so minItems: 8 is enforced as the safe default."""
        doc = _make_doc(fast_path=False, n_skills=8)
        del doc["fast_path"]
        errors = list(validator.iter_errors(doc))
        assert not errors, [e.message for e in errors]

    def test_fast_path_missing_with_2_skills_fails(self, validator):
        """Absent fast_path defaults to the const: false branch → minItems 8."""
        doc = _make_doc(fast_path=False, n_skills=2)
        del doc["fast_path"]
        errors = list(validator.iter_errors(doc))
        assert errors
