from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def aidlc_root() -> Path:
    """Create a temporary AIDLC repo root with minimal fixture data."""
    root = Path(tempfile.mkdtemp(suffix="_aidlc_test"))

    # Minimal default budget
    budgets_dir = root / ".aidlc-orchestrator" / "budgets"
    budgets_dir.mkdir(parents=True)
    _write_yaml(budgets_dir / "default.yaml", {
        "run": {"tokens_max": 5_000_000, "wall_clock_max_min": 240},
        "concurrency": {"max_parallel": 4},
        "per_stage": {
            "workspace-scout": {"tokens": 50_000, "wall_min": 5, "retries": 1, "model": "sonnet"},
            "code-generator": {"tokens": 500_000, "wall_min": 30, "retries": 2, "model": "opus"},
            "requirements-analyst": {"tokens": 800_000, "wall_min": 30, "retries": 2, "model": "opus"},
            "build-test-agent": {"tokens": 300_000, "wall_min": 20, "retries": 3, "model": "sonnet"},
            "reviewer-code": {"tokens": 200_000, "wall_min": 15, "retries": 1, "model": "sonnet"},
        },
        "adaptive_depth": {"threshold_pct_remaining": 30, "downshift_order": []},
        "complexity_tiers": {
            "SMALL": {"tokens_max": 500_000, "wall_clock_max_min": 30},
            "MEDIUM": {"tokens_max": 1_500_000, "wall_clock_max_min": 90},
            "LARGE": {"tokens_max": 5_000_000, "wall_clock_max_min": 240},
        },
    })

    # Minimal VERSION file (orchestrator version-locking)
    scripts_dir = root / "aidlc-scripts"
    scripts_dir.mkdir(parents=True)
    scripts_dir.joinpath("VERSION").write_text("0.2.0\n")

    # Reviewer output schema
    contracts_dir = root / ".aidlc-orchestrator" / "contracts"
    contracts_dir.mkdir(parents=True)
    _write_json(contracts_dir / "reviewer.output.v1.json", {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": "reviewer.output.v1",
        "title": "Reviewer Output Contract v1",
        "type": "object",
        "required": ["status", "reviewer", "findings", "findings_summary", "audit_entries", "skill_compliance"],
        "properties": {
            "status": {"type": "string", "enum": ["complete", "blocked", "failed", "needs_human"]},
            "reviewer": {"type": "string", "enum": ["code-quality", "security", "performance", "simplifier"]},
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["severity", "file", "message"],
                    "properties": {
                        "severity": {"type": "string", "enum": ["P0", "P1", "P2", "P3"]},
                        "file": {"type": "string"},
                        "line": {"type": "integer", "minimum": 1},
                        "axis": {"type": "string"},
                        "cwe": {"type": "string"},
                        "owasp": {"type": "string"},
                        "big_o": {"type": "string"},
                        "expected_impact": {"type": "string"},
                        "simplification_pattern": {"type": "string"},
                        "message": {"type": "string", "minLength": 1},
                        "recommendation": {"type": "string", "minLength": 1},
                    },
                    "additionalProperties": False,
                },
            },
            "findings_summary": {
                "type": "object",
                "required": ["P0_count", "P1_count", "P2_count", "P3_count"],
                "properties": {
                    "P0_count": {"type": "integer", "minimum": 0},
                    "P1_count": {"type": "integer", "minimum": 0},
                    "P2_count": {"type": "integer", "minimum": 0},
                    "P3_count": {"type": "integer", "minimum": 0},
                },
                "additionalProperties": False,
            },
            "audit_entries": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1},
            "skill_compliance": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["skill", "status", "evidence"],
                    "properties": {
                        "skill": {"type": "string"},
                        "status": {"type": "string", "enum": ["PASS", "FAIL", "N/A"]},
                        "evidence": {"type": "string", "minLength": 1},
                    },
                    "additionalProperties": False,
                },
                "minItems": 2,
            },
            "cost": {"type": "object"},
            "emitted_knowledge": {"type": "array", "items": {"type": "object"}},
            "conflicts_detected": {"type": "array"},
            "locks_to_release": {"type": "array", "items": {"type": "string"}},
        },
        "additionalProperties": False,
    })

    return root


@pytest.fixture
def run_id() -> str:
    return "test-run-001"


@pytest.fixture
def env_setup(aidlc_root: Path):
    old = os.environ.get("AIDLC_ROOT")
    os.environ["AIDLC_ROOT"] = str(aidlc_root)
    yield aidlc_root
    if old is None:
        os.environ.pop("AIDLC_ROOT", None)
    else:
        os.environ["AIDLC_ROOT"] = old


def _write_yaml(path: Path, data: dict) -> None:
    import yaml
    path.write_text(yaml.safe_dump(data, default_flow_style=False, sort_keys=False))


def _write_json(path: Path, data: dict) -> None:
    import json
    path.write_text(json.dumps(data, indent=2))
