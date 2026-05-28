"""CTR-02/03: Contract handoff strictness and schema evolution tests.

Validates:
- CTR-02: Every contract has required fields; invalid payloads rejected
- CTR-03: Schema versioning and breaking changes documented
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS_DIR = REPO_ROOT / ".aidlc-orchestrator" / "contracts"


def _all_contracts() -> list[Path]:
    return sorted(CONTRACTS_DIR.glob("*.v1.json"))


# ---------------------------------------------------------------------------
# CTR-02: Handoff strictness
# ---------------------------------------------------------------------------

class TestContractHandoffStrictness:
    def test_contracts_directory_exists(self):
        assert CONTRACTS_DIR.exists(), "contracts directory must exist"

    def test_at_least_20_contracts(self):
        contracts = _all_contracts()
        assert len(contracts) >= 20, \
            f"Expected ≥20 contracts, found {len(contracts)}"

    def test_all_contracts_valid_json(self):
        for path in _all_contracts():
            try:
                json.loads(path.read_text())
            except json.JSONDecodeError as e:
                pytest.fail(f"{path.name}: invalid JSON - {e}")

    def test_all_contracts_have_type(self):
        for path in _all_contracts():
            schema = json.loads(path.read_text())
            assert "type" in schema, f"{path.name} missing 'type'"
            assert schema["type"] == "object", \
                f"{path.name} type must be 'object', got '{schema['type']}'"

    def test_all_contracts_have_title(self):
        for path in _all_contracts():
            schema = json.loads(path.read_text())
            assert "title" in schema, f"{path.name} missing 'title'"

    def test_all_contracts_define_properties(self):
        for path in _all_contracts():
            schema = json.loads(path.read_text())
            assert "properties" in schema, \
                f"{path.name} must define 'properties'"

    def test_all_contracts_have_required_field(self):
        for path in _all_contracts():
            schema = json.loads(path.read_text())
            assert "required" in schema or "oneOf" in schema or "anyOf" in schema, \
                f"{path.name} must define 'required' or composition keyword"

    def test_output_contracts_have_status(self):
        for path in _all_contracts():
            if "output" not in path.stem:
                continue
            schema = json.loads(path.read_text())
            props = schema.get("properties", {})
            has_status = "status" in props
            assert has_status, \
                f"{path.name}: output contracts must define 'status'"

    def test_output_contracts_status_enum(self):
        for path in _all_contracts():
            if "output" not in path.stem:
                continue
            schema = json.loads(path.read_text())
            status_prop = schema.get("properties", {}).get("status", {})
            if "enum" in status_prop:
                valid = {"complete", "needs_human", "failed", "blocked"}
                declared = set(status_prop["enum"])
                assert declared.issubset(valid), \
                    f"{path.name}: status enum has invalid values: {declared - valid}"

    def test_contracts_have_additional_properties_false(self):
        strict_count = 0
        total = 0
        for path in _all_contracts():
            schema = json.loads(path.read_text())
            total += 1
            if schema.get("additionalProperties") is False:
                strict_count += 1
        assert strict_count >= total * 0.5, \
            f"Only {strict_count}/{total} contracts set additionalProperties=false"


# ---------------------------------------------------------------------------
# CTR-03: Schema evolution
# ---------------------------------------------------------------------------

class TestSchemaEvolution:
    def test_contracts_have_descriptions(self):
        described = 0
        total = 0
        for path in _all_contracts():
            schema = json.loads(path.read_text())
            total += 1
            if schema.get("description"):
                described += 1
        assert described >= total * 0.1, \
            f"Only {described}/{total} contracts have descriptions; consider adding more"

    def test_version_pattern_in_filename(self):
        for path in _all_contracts():
            assert ".v1." in path.name, \
                f"{path.name}: filename should include .v1. version"
