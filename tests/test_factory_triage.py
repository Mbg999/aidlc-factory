from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
TRIAGE_PY = SCRIPTS / "factory_triage.py"


def run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(TRIAGE_PY), *args],
        capture_output=True, text=True,
    )


class TestPrefilter:
    """factory_triage.py prefilter — quick TINY check for trivial work."""

    @pytest.mark.parametrize("request_text", [
        "fix typo in README",
        "fix a typo in README",
        "update README",
        "fix comment",
        "add license file",
        "fix docs",
    ])
    def test_trivial_returns_tiny(self, request_text):
        result = run("prefilter", request_text)
        data = json.loads(result.stdout)
        assert data["tier"] == "TINY"
        assert result.returncode == 0

    @pytest.mark.parametrize("request_text", [
        "add a healthz endpoint",
        "zzz zzz zzz",
        "",
    ])
    def test_non_trivial_returns_unknown(self, request_text):
        result = run("prefilter", request_text)
        data = json.loads(result.stdout)
        assert data["tier"] == "UNKNOWN"
        assert result.returncode == 10

    def test_empty_whitespace(self):
        result = run("prefilter", "   ")
        assert result.returncode == 10

    def test_non_ascii(self):
        result = run("prefilter", "ñøñ-ÅSCII çħæŕš")
        assert result.returncode == 10


class TestPrompt:
    """factory_triage.py prompt — prints LLM classification prompt."""

    def test_prompt_contains_request(self):
        result = run("prompt", "build a pokedex")
        assert result.returncode == 0
        assert "build a pokedex" in result.stdout
        assert "complexity triage" in result.stdout.lower()
        assert "single_file" in result.stdout
        assert "security_relevance" in result.stdout

    def test_prompt_handles_special_chars(self):
        result = run("prompt", "añadir login con google")
        assert result.returncode == 0
        assert "añadir login con google" in result.stdout


class TestApply:
    """factory_triage.py apply — maps LLM classification to tier."""

    def _apply(self, data: dict) -> subprocess.CompletedProcess:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            result = run("apply", f.name)
        Path(f.name).unlink()
        return result

    def test_trivial_classification_small(self):
        """Low risk, single file, no deps -> SMALL."""
        data = {
            "intent": "modify",
            "scope": "single_file",
            "risk": "low",
            "architecture_impact": "none",
            "security_relevance": "none",
            "external_dependencies": [],
            "data_layer_impact": "none",
            "coordination_required": False,
            "ambiguity": "low",
            "estimated_affected_components": "1-2",
        }
        result = self._apply(data)
        assert json.loads(result.stdout)["tier"] == "SMALL"
        assert result.returncode == 1

    def test_medium_request(self):
        """Multiple modules, moderate risk -> MEDIUM."""
        data = {
            "intent": "create",
            "scope": "multi_module",
            "risk": "medium",
            "architecture_impact": "medium",
            "security_relevance": "none",
            "external_dependencies": ["stripe"],
            "data_layer_impact": "medium",
            "coordination_required": True,
            "ambiguity": "medium",
            "estimated_affected_components": "3-5",
        }
        result = self._apply(data)
        assert json.loads(result.stdout)["tier"] == "MEDIUM"
        assert result.returncode == 2

    def test_large_request(self):
        """System-wide, high risk, many components -> LARGE."""
        data = {
            "intent": "migrate",
            "scope": "system_wide",
            "risk": "high",
            "architecture_impact": "high",
            "security_relevance": "high",
            "external_dependencies": ["aws", "stripe", "kafka"],
            "data_layer_impact": "high",
            "coordination_required": True,
            "ambiguity": "high",
            "estimated_affected_components": "10+",
        }
        result = self._apply(data)
        assert json.loads(result.stdout)["tier"] == "LARGE"
        assert result.returncode == 3

    def test_apply_from_stdin(self):
        """- reads from stdin."""
        data = {"scope": "single_file", "risk": "low", "architecture_impact": "none",
                "security_relevance": "none", "data_layer_impact": "none",
                "coordination_required": False, "ambiguity": "low",
                "estimated_affected_components": "1-2", "intent": "modify"}
        result = subprocess.run(
            [sys.executable, str(TRIAGE_PY), "apply", "-"],
            input=json.dumps(data), capture_output=True, text=True,
        )
        assert json.loads(result.stdout)["tier"] == "SMALL"

    def test_pokedex_request(self):
        """Full-stack pokedex app -> MEDIUM (multi_module, coordination)."""
        data = {
            "intent": "create",
            "scope": "multi_module",
            "risk": "medium",
            "architecture_impact": "medium",
            "security_relevance": "low",
            "external_dependencies": ["pokeapi"],
            "data_layer_impact": "low",
            "coordination_required": True,
            "ambiguity": "medium",
            "estimated_affected_components": "3-5",
            "notes": "react frontend, express backend, external api integration",
        }
        result = self._apply(data)
        tier = json.loads(result.stdout)["tier"]
        assert tier in ("MEDIUM", "LARGE")
        assert result.returncode in (2, 3)
