"""Validate workspace-scope.output.v1.json ecosystem is now a free string.

Regression test for Bug 3 — ecosystem enum too restrictive (rejected Maven,
Gradle, Yarn, pnpm, Composer, etc.).
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
    / "workspace-scout.output.v1.json"
)

pytest.importorskip("jsonschema")
from jsonschema import Draft7Validator


@pytest.fixture(scope="session")
def validator():
    return Draft7Validator(json.loads(SCHEMA_PATH.read_text()))


class TestEcosystemFreeString:
    def test_ecosystem_maven_passes(self, validator):
        """Previously rejected 'maven' — now must pass."""
        doc = {
            "status": "complete",
            "artifacts": [{"path": "README.md", "kind": "doc"}],
            "audit_entries": ["test entry"],
            "skill_compliance": [
                {"skill": "x", "status": "PASS", "evidence": "ok"}
            ],
            "workspace_state": {
                "project_type": "greenfield",
                "existing_code": False,
                "next_phase": "requirements-analysis",
                "tech_stack": [
                    {"package": "maven-compiler", "version": "3.11",
                     "ecosystem": "maven"}
                ],
            },
        }
        errors = list(validator.iter_errors(doc))
        assert not errors, [e.message for e in errors]

    def test_ecosystem_gradle_passes(self, validator):
        doc = {
            "status": "complete",
            "artifacts": [{"path": "build.gradle", "kind": "config"}],
            "audit_entries": ["test entry"],
            "skill_compliance": [
                {"skill": "x", "status": "PASS", "evidence": "ok"}
            ],
            "workspace_state": {
                "project_type": "greenfield",
                "existing_code": True,
                "next_phase": "reverse-engineering",
                "tech_stack": [
                    {"package": "spring-boot", "version": "3.2",
                     "ecosystem": "gradle"}
                ],
            },
        }
        errors = list(validator.iter_errors(doc))
        assert not errors

    def test_ecosystem_yarn_pnpm_composer_passes(self, validator):
        doc = {
            "status": "complete",
            "artifacts": [{"path": "package.json", "kind": "config"}],
            "audit_entries": ["test entry"],
            "skill_compliance": [
                {"skill": "x", "status": "PASS", "evidence": "ok"}
            ],
            "workspace_state": {
                "project_type": "brownfield",
                "existing_code": True,
                "next_phase": "reverse-engineering",
                "tech_stack": [
                    {"package": "webpack", "version": "5",
                     "ecosystem": "yarn"},
                    {"package": "react", "version": "18",
                     "ecosystem": "pnpm"},
                    {"package": "twig", "version": "3",
                     "ecosystem": "composer"},
                ],
            },
        }
        errors = list(validator.iter_errors(doc))
        assert not errors

    def test_ecosystem_still_allows_npm_pip(self, validator):
        """Original ecosystems must still work."""
        doc = {
            "status": "complete",
            "artifacts": [{"path": "requirements.txt", "kind": "config"}],
            "audit_entries": ["test entry"],
            "skill_compliance": [
                {"skill": "x", "status": "PASS", "evidence": "ok"}
            ],
            "workspace_state": {
                "project_type": "greenfield",
                "existing_code": False,
                "next_phase": "requirements-analysis",
                "tech_stack": [
                    {"package": "requests", "version": "2.31",
                     "ecosystem": "pip"},
                    {"package": "express", "version": "4.18",
                     "ecosystem": "npm"},
                ],
            },
        }
        errors = list(validator.iter_errors(doc))
        assert not errors

    def test_missing_ecosystem_field_fails(self, validator):
        doc = {
            "status": "complete",
            "artifacts": [{"path": "pom.xml", "kind": "config"}],
            "audit_entries": ["test entry"],
            "skill_compliance": [
                {"skill": "x", "status": "PASS", "evidence": "ok"}
            ],
            "workspace_state": {
                "project_type": "greenfield",
                "existing_code": False,
                "next_phase": "requirements-analysis",
                "tech_stack": [
                    {"package": "maven-compiler", "version": "3.11"}
                ],
            },
        }
        errors = list(validator.iter_errors(doc))
        assert any("ecosystem" in e.message for e in errors)
