from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
TRIAGE_PY = SCRIPTS / "factory_triage.py"


@pytest.mark.parametrize("request_text,expected_tier,expected_score,expected_pipeline", [
    ("add a healthz endpoint", "TINY", 0, "fast"),
    ("fix a typo in README", "TINY", 0, "fast"),
    ("add JWT auth to API gateway", "SMALL", 2, "full"),
    ("refactor auth module to extract AuthService", "SMALL", 2, "full"),
    ("implement payment microservice with Stripe, S3, and Kafka", "SMALL", 3, "full"),
    ("migrate monolith to microservices across the entire codebase", "SMALL", 4, "full"),
])
def test_triage_ac(request_text, expected_tier, expected_score, expected_pipeline):
    result = subprocess.run(
        [sys.executable, str(TRIAGE_PY), request_text],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    assert data["tier"] == expected_tier, f"tier mismatch for {request_text!r}"
    assert data["score"] == expected_score, f"score mismatch for {request_text!r}"
    assert data["recommended_pipeline"] == expected_pipeline


@pytest.mark.parametrize("request_text", [
    "",
    "   ",
    "ñøñ-ÅSCII çħæŕš",
    "a" * 10000,
    "normal request with no keywds",
])
def test_triage_edge_cases(request_text):
    result = subprocess.run(
        [sys.executable, str(TRIAGE_PY), request_text],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    assert isinstance(data["score"], int)
    assert data["tier"] in ("TINY", "SMALL", "MEDIUM", "LARGE")


def test_triage_explain_flag():
    result = subprocess.run(
        [sys.executable, str(TRIAGE_PY), "add healthz", "--explain"],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    assert data["tier"] == "TINY"
    assert "TRIAGE:" in result.stderr


def test_triage_single_factor_architecture():
    """Request mentioning only architecture signal should score 2."""
    result = subprocess.run(
        [sys.executable, str(TRIAGE_PY), "design system architecture for the new service"],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    assert data["score"] == 2, f"expected 2, got {data['score']}: {data['factors']}"
    assert data["factors"]["architecture_signal"] == 2


def test_triage_score_zero_with_non_matching_text():
    result = subprocess.run(
        [sys.executable, str(TRIAGE_PY), "zzz zzz zzz"],
        capture_output=True, text=True,
    )
    data = json.loads(result.stdout)
    assert data["score"] == 0
    assert data["tier"] == "TINY"


def test_triage_exit_code_tiny():
    result = subprocess.run(
        [sys.executable, str(TRIAGE_PY), "add healthz"],
        capture_output=True,
    )
    assert result.returncode == 0


def test_triage_exit_code_small():
    result = subprocess.run(
        [sys.executable, str(TRIAGE_PY), "add JWT auth to API gateway"],
        capture_output=True,
    )
    assert result.returncode == 1


def test_triage_dry_run():
    """--dry-run prints triage summary without JSON output."""
    result = subprocess.run(
        [sys.executable, str(TRIAGE_PY), "add healthz endpoint", "--dry-run"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "TINY" in result.stdout
    assert "FAST_PATH" in result.stdout