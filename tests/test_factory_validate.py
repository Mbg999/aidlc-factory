from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
VALIDATE_PY = SCRIPTS / "factory_validate.py"


def test_validate_ok(env_setup):
    schema = env_setup / ".aidlc-orchestrator" / "contracts" / "reviewer.output.v1.json"
    doc = env_setup / "test-doc.yaml"
    doc.write_text("status: complete\nreviewer: code-quality\nfindings: []\nfindings_summary:\n  P0_count: 0\n  P1_count: 0\n  P2_count: 0\n  P3_count: 0\naudit_entries:\n  - done\nskill_compliance:\n  - skill: test\n    status: PASS\n    evidence: ok\n  - skill: test2\n    status: PASS\n    evidence: ok\n")
    result = subprocess.run(
        [sys.executable, str(VALIDATE_PY), str(schema), str(doc)],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "OK" in result.stdout


def test_validate_invalid(env_setup):
    schema = env_setup / ".aidlc-orchestrator" / "contracts" / "reviewer.output.v1.json"
    doc = env_setup / "test-bad.yaml"
    doc.write_text("status: invalid_status\nreviewer: unknown\n")
    result = subprocess.run(
        [sys.executable, str(VALIDATE_PY), str(schema), str(doc)],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "INVALID" in result.stderr


def test_validate_strict_empty_artifacts(env_setup):
    schema = env_setup / ".aidlc-orchestrator" / "contracts" / "reviewer.output.v1.json"
    doc = env_setup / "test-strict.yaml"
    doc.write_text("status: complete\nreviewer: code-quality\nfindings: []\nfindings_summary:\n  P0_count: 0\n  P1_count: 0\n  P2_count: 0\n  P3_count: 0\naudit_entries:\n  - done\nskill_compliance:\n  - skill: test\n    status: PASS\n    evidence: ok\n  - skill: test2\n    status: PASS\n    evidence: ok\n")
    result = subprocess.run(
        [sys.executable, str(VALIDATE_PY), str(schema), str(doc), "--strict"],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "STRICT FAIL" in result.stderr
    assert "no artifact with a non-empty" in result.stderr


def test_validate_strict_missing_recommendation(env_setup):
    schema = env_setup / ".aidlc-orchestrator" / "contracts" / "reviewer.output.v1.json"
    doc = env_setup / "test-strict2.yaml"
    doc.write_text("status: complete\nreviewer: code-quality\nfindings:\n  - severity: P0\n    file: src/main.py\n    message: Critical bug\nfindings_summary:\n  P0_count: 1\n  P1_count: 0\n  P2_count: 0\n  P3_count: 0\naudit_entries:\n  - done\nskill_compliance:\n  - skill: test\n    status: PASS\n    evidence: ok\n  - skill: test2\n    status: PASS\n    evidence: ok\n")
    result = subprocess.run(
        [sys.executable, str(VALIDATE_PY), str(schema), str(doc), "--strict"],
        capture_output=True, text=True,
    )
    assert result.returncode == 1
    assert "STRICT FAIL" in result.stderr
    assert "no `recommendation`" in result.stderr


def test_validate_strict_ok(env_setup):
    # Use a custom relaxed schema that allows artifacts for strict testing
    schema_path = env_setup / "test-schema.json"
    schema_path.write_text(json.dumps({
        "type": "object",
        "required": ["status"],
        "properties": {
            "status": {"type": "string", "enum": ["complete", "incomplete"]},
            "artifacts": {
                "type": "array",
                "items": {"type": "object", "properties": {"path": {"type": "string"}}},
            },
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string"},
                        "file": {"type": "string"},
                        "message": {"type": "string"},
                        "recommendation": {"type": "string"},
                    },
                },
            },
            "emitted_knowledge": {
                "type": "array",
                "items": {"type": "object", "properties": {"body": {"type": "string"}}},
            },
        },
        "additionalProperties": True,
    }))
    doc = env_setup / "test-strict3.yaml"
    doc.write_text("status: complete\nartifacts:\n  - path: src/main.py\nfindings:\n  - severity: P0\n    file: src/main.py\n    message: Critical bug\n    recommendation: Fix it\n")
    result = subprocess.run(
        [sys.executable, str(VALIDATE_PY), str(schema_path), str(doc), "--strict"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "OK" in result.stdout
