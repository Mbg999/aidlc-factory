from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = REPO_ROOT / ".aidlc-orchestrator" / "contracts"
INPUT_SCHEMA = json.loads((CONTRACTS / "code-generator.input.v1.json").read_text())
OUTPUT_SCHEMA = json.loads((CONTRACTS / "code-generator.output.v1.json").read_text())


@pytest.fixture
def input_validator():
    return jsonschema.Draft7Validator(INPUT_SCHEMA)


@pytest.fixture
def output_validator():
    return jsonschema.Draft7Validator(OUTPUT_SCHEMA)


def _make_doc(**overrides) -> dict:
    doc = {
        "run_id": "test-run",
        "stage_id": "code-generator",
        "user_request": "Build a login page",
        "predecessor_artifacts": ["plan.md"],
        "unit_name": "login-ui",
        "skills_required": ["tdd", "testing", "security", "docs"],
        "skill_paths_resolved": [".agents/skills/tdd/SKILL.md"],
    }
    doc.update(overrides)
    return doc


class TestInputSchema:
    def test_valid_doc_passes(self, input_validator):
        errors = list(input_validator.iter_errors(_make_doc()))
        assert len(errors) == 0

    def test_missing_required_fails(self, input_validator):
        doc = _make_doc()
        del doc["run_id"]
        errors = list(input_validator.iter_errors(doc))
        assert len(errors) >= 1

    def test_skills_required_min_4(self, input_validator):
        doc = _make_doc(skills_required=["tdd"])
        errors = list(input_validator.iter_errors(doc))
        assert any("skills_required" in str(e.path) for e in errors)

    def test_skill_paths_min_1(self, input_validator):
        doc = _make_doc(skill_paths_resolved=[])
        errors = list(input_validator.iter_errors(doc))
        assert any("skill_paths_resolved" in str(e.path) for e in errors)


class TestOutputSchema:
    def test_valid_output_passes(self, output_validator):
        doc = {
            "status": "complete",
            "unit_name": "login-ui",
            "sub_stage": "generated",
            "artifacts": [{"path": "src/login.tsx", "kind": "source"}],
            "audit_entries": ["Generated login component"],
            "skill_compliance": [{"skill": "tdd", "status": "PASS", "evidence": "tests written"}],
        }
        errors = list(output_validator.iter_errors(doc))
        assert len(errors) == 0
