"""Validate ship-agent.output.v1.json skill_compliance minItems reduced to 4.

Regression test for Bug 5 — 6 skills just at the limit, any missing skill broke it.
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
    / "ship-agent.output.v1.json"
)

pytest.importorskip("jsonschema")
from jsonschema import Draft7Validator


@pytest.fixture(scope="session")
def validator():
    return Draft7Validator(json.loads(SCHEMA_PATH.read_text()))


def _make_doc(n_skills: int, **overrides) -> dict:
    skills = [
        {"skill": f"skill-{i}", "status": "PASS",
         "evidence": "test evidence"}
        for i in range(n_skills)
    ]
    doc = {
        "status": "complete",
        "artifacts": [
            {"path": "CHANGELOG.md", "kind": "doc", "hash": "abc"},
            {"path": "RELEASE.md", "kind": "doc", "hash": "def"},
        ],
        "audit_entries": ["test entry"],
        "skill_compliance": skills,
        "version_proposal": {
            "from": "0.1.0", "to": "0.2.0",
            "kind": "minor", "rationale": "test",
        },
        "adr_count": 2,
        "release_sections_covered": ["Added"],
        **overrides,
    }
    return doc


class TestMinItems:
    def test_6_skills_base_passes(self, validator):
        """6 core skills match ship-agent unconditional skills."""
        doc = _make_doc(n_skills=6)
        errors = list(validator.iter_errors(doc))
        assert not errors, [e.message for e in errors]

    def test_6_skills_passes(self, validator):
        doc = _make_doc(n_skills=6)
        errors = list(validator.iter_errors(doc))
        assert not errors

    def test_8_skills_passes(self, validator):
        doc = _make_doc(n_skills=8)
        errors = list(validator.iter_errors(doc))
        assert not errors

    def test_0_skills_fails(self, validator):
        doc = _make_doc(n_skills=0)
        errors = list(validator.iter_errors(doc))
        assert errors

    def test_3_skills_fails(self, validator):
        doc = _make_doc(n_skills=3)
        errors = list(validator.iter_errors(doc))
        assert errors
