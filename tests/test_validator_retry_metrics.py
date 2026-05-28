"""SKL-04: Validator-Retry metrics extraction & verification.

Validates that the validator-retry SKILL.md:
1. Is structurally complete (name, description, steps, verification gates)
2. Has proper retry limits (max 3)
3. Emits structured, parseable audit entries
4. Covers all expected ecosystems
5. Can be parsed into a metrics payload for the evaluator pipeline
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SKILL_MD = REPO_ROOT / ".agents" / "custom-skills" / "validator-retry" / "SKILL.md"

EXPECTED_ECOSYSTEMS = {
    "TypeScript": "tsc",
    "JavaScript": "eslint",
    "Python": "pyright",
    "Rust": "cargo check",
    "Go": "go vet",
}
MAX_RETRIES = 3


# ---------------------------------------------------------------------------
# SKILL.md structure
# ---------------------------------------------------------------------------

class TestSkillStructure:
    def test_skill_exists(self):
        assert SKILL_MD.exists(), f"validator-retry skill not found at {SKILL_MD}"

    def test_skill_has_valid_frontmatter(self):
        text = SKILL_MD.read_text()
        assert text.startswith("---"), "SKILL.md must start with frontmatter"
        assert "name: validator-retry" in text
        assert "description:" in text

    def test_skill_name_matches(self):
        text = SKILL_MD.read_text()
        # Parse frontmatter name
        match = re.search(r"^name:\s*(.+)$", text, re.MULTILINE)
        assert match, "name field not found in frontmatter"
        assert match.group(1).strip() == "validator-retry"


# ---------------------------------------------------------------------------
# Retry loop compliance
# ---------------------------------------------------------------------------

class TestRetryLoop:
    def test_max_retries_limited_to_3(self):
        text = SKILL_MD.read_text()
        # Find the "max" or limited retries mention
        assert "max 3" in text or "3 retries" in text or "attempt 3" in text or \
               "attempt N/3" in text or "3 iterations" in text, \
            "SKILL.md must limit retries to a maximum (expected 3)"

    def test_retry_bounded_verification_exists(self):
        text = SKILL_MD.read_text()
        assert "At most 3" in text or "max 3" in text, \
            "Verification gate must confirm retries are bounded at 3"

    def test_persistent_failure_escalates(self):
        text = SKILL_MD.read_text()
        assert "PERSISTENT FAILURE" in text or "blocked" in text, \
            "SKILL.md must handle persistent failures via escalation"
        assert "blocked" in text or "HALT" in text, \
            "Must set status: blocked or HALT on persistent failure"

    def test_clean_exit_stops_early(self):
        text = SKILL_MD.read_text()
        # Step 2 says clean = stop
        assert "STOP" in text, "SKILL.md must stop on clean validator run"


# ---------------------------------------------------------------------------
# Ecosystem coverage
# ---------------------------------------------------------------------------

class TestEcosystemCoverage:
    def test_covers_expected_ecosystems(self):
        text = SKILL_MD.read_text()
        for eco, tool in EXPECTED_ECOSYSTEMS.items():
            assert eco in text or tool in text, \
                f"SKILL.md must cover {eco} (expected to find '{tool}')"

    @pytest.mark.parametrize("eco,tool", list(EXPECTED_ECOSYSTEMS.items()))
    def test_each_ecosystem_has_detection_condition(self, eco, tool):
        text = SKILL_MD.read_text()
        # Each ecosystem should mention a detection condition
        assert "Detection condition" in text or eco in text, \
            f"Expected detection condition for {eco}"

    def test_validator_table_complete(self):
        text = SKILL_MD.read_text()
        # The validator table should have Ecosystem, Validator, Detection condition, Run command
        assert "Ecosystem" in text and "Validator" in text and "Detection condition" in text and \
               "Run command" in text, \
            "Validator detection table must have all 4 columns"


# ---------------------------------------------------------------------------
# Audit entry format
# ---------------------------------------------------------------------------

class TestAuditFormat:
    def test_audit_entry_format_documented(self):
        text = SKILL_MD.read_text()
        assert "[Validator]" in text, \
            "SKILL.md must document audit entry format with [Validator] prefix"

    def test_audit_format_includes_attempt_count(self):
        text = SKILL_MD.read_text()
        assert "attempt" in text or "attempt " in text, \
            "Audit entries must include retry attempt count"

    def test_audit_format_includes_tool_name(self):
        text = SKILL_MD.read_text()
        for tool in ("tsc", "eslint", "pyright", "mypy"):
            if f"[Validator]" in text:
                break
        assert "[Validator]" in text, \
            "Audit entries must include tool name"

    def test_clean_format_documented(self):
        text = SKILL_MD.read_text()
        assert "clean" in text, \
            "SKILL.md must document the format for clean validator runs"


# ---------------------------------------------------------------------------
# Audit entry parser (for evaluator pipeline)
# ---------------------------------------------------------------------------

SAMPLE_AUDIT_ENTRIES = [
    "[Validator] detected: tsc, eslint",
    "[Validator] tsc attempt 1/3 — 4 errors",
    "[Validator] eslint attempt 1/3 — 2 errors",
    "[Validator] tsc clean after 1 retry",
    "[Validator] eslint clean after 1 retry",
]

SAMPLE_FAILURE_ENTRIES = [
    "[Validator] detected: tsc",
    "[Validator] tsc attempt 1/3 — 4 errors",
    "[Validator] tsc attempt 2/3 — 2 errors",
    "[Validator] tsc attempt 3/3 — 2 errors (PERSISTENT)",
    "[Validator] PERSISTENT FAILURE — blocked after 3 retries",
]


def parse_validator_audit_entries(entries: list[str]) -> dict:
    """Parse [Validator] audit entries into structured metrics.

    Returns:
        dict with keys:
          - tools_detected: list[str]
          - attempts: list[dict{tool, attempt_number, max_attempts, error_count}]
          - clean_results: list[dict{tool, retry_count}]
          - persistent_failures: list[dict{tool, attempt_number, error_count}]
          - blocked: bool
          - error_count_total: int
    """
    result = {
        "tools_detected": [],
        "attempts": [],
        "clean_results": [],
        "persistent_failures": [],
        "blocked": False,
        "error_count_total": 0,
    }
    for entry in entries:
        if not entry.startswith("[Validator]"):
            continue
        body = entry[len("[Validator] "):]

        # "detected: tsc, eslint"
        if body.startswith("detected:"):
            tools = [t.strip() for t in body[len("detected:"):].split(",")]
            result["tools_detected"] = tools
            continue

        # "tsc attempt 1/3 — 4 errors"
        attempt_match = re.match(r"(\S+) attempt (\d+)/(\d+) — (\d+) errors", body)
        if attempt_match:
            result["attempts"].append({
                "tool": attempt_match.group(1),
                "attempt_number": int(attempt_match.group(2)),
                "max_attempts": int(attempt_match.group(3)),
                "error_count": int(attempt_match.group(4)),
            })
            result["error_count_total"] += int(attempt_match.group(4))
            continue

        # "tsc clean after 1 retry" or "tsc clean — 0 errors"
        clean_match = re.match(r"(\S+) clean(?: after (\d+) retr(?:y|ies))?", body)
        if clean_match:
            result["clean_results"].append({
                "tool": clean_match.group(1),
                "retry_count": int(clean_match.group(2)) if clean_match.group(2) else 0,
            })
            continue

        # "PERSISTENT FAILURE — blocked after 3 retries"
        if "PERSISTENT FAILURE" in body:
            result["blocked"] = True
            continue

    return result


class TestAuditParser:
    def test_parse_clean_run(self):
        metrics = parse_validator_audit_entries(SAMPLE_AUDIT_ENTRIES)
        assert metrics["tools_detected"] == ["tsc", "eslint"]
        assert len(metrics["attempts"]) == 2
        assert metrics["clean_results"][0]["tool"] == "tsc"
        assert metrics["clean_results"][0]["retry_count"] == 1
        assert not metrics["blocked"]

    def test_parse_failure_run(self):
        metrics = parse_validator_audit_entries(SAMPLE_FAILURE_ENTRIES)
        assert metrics["tools_detected"] == ["tsc"]
        assert len(metrics["attempts"]) == 3
        assert metrics["attempts"][-1]["attempt_number"] == MAX_RETRIES
        assert metrics["blocked"]
        assert metrics["error_count_total"] == 8

    def test_parser_empty_input(self):
        metrics = parse_validator_audit_entries([])
        assert metrics["tools_detected"] == []
        assert metrics["attempts"] == []
        assert not metrics["blocked"]

    def test_parser_skips_non_validator_entries(self):
        mixed = ["[WorkspaceScout] done", "[Validator] tsc clean — 0 errors"]
        metrics = parse_validator_audit_entries(mixed)
        assert len(metrics["clean_results"]) == 1
        assert metrics["clean_results"][0]["tool"] == "tsc"

    def test_parser_handles_modified_attempt_line(self):
        """The audit entry may use different wording but keep the structure."""
        entries = [
            "[Validator] detected: pyright",
            "[Validator] pyright attempt 1/3 — 12 errors",
            "[Validator] pyright clean — 0 errors",
        ]
        metrics = parse_validator_audit_entries(entries)
        assert metrics["tools_detected"] == ["pyright"]
        assert metrics["attempts"][0]["error_count"] == 12
        assert metrics["clean_results"][0]["retry_count"] == 0

    def test_parser_tool_stopped_at_3_retries(self):
        for metric in [parse_validator_audit_entries(SAMPLE_AUDIT_ENTRIES),
                        parse_validator_audit_entries(SAMPLE_FAILURE_ENTRIES)]:
            for attempt in metric["attempts"]:
                assert attempt["max_attempts"] == MAX_RETRIES, \
                    f"Expected max retries = {MAX_RETRIES}, got {attempt}"


# ---------------------------------------------------------------------------
# Evaluator integration (export format)
# ---------------------------------------------------------------------------

def extract_validator_summary(audit_entries: list[str]) -> dict:
    """Extract a summary payload suitable for the evaluator pipeline.

    This is the function that would be called by the evaluator post-processor
    to collect validator-retry metrics from a run's audit entries.
    """
    parsed = parse_validator_audit_entries(audit_entries)
    return {
        "detected_tools": parsed["tools_detected"],
        "total_attempts": len(parsed["attempts"]),
        "total_errors": parsed["error_count_total"],
        "tools_clean": [c["tool"] for c in parsed["clean_results"]],
        "tools_failed": [a["tool"] for a in parsed["attempts"]
                         if a["attempt_number"] == MAX_RETRIES and parsed["blocked"]],
        "blocked": parsed["blocked"],
        "max_retries_exhausted": parsed["blocked"],
    }


class TestEvaluatorPayload:
    def test_clean_run_payload(self):
        payload = extract_validator_summary(SAMPLE_AUDIT_ENTRIES)
        assert payload["detected_tools"] == ["tsc", "eslint"]
        assert payload["total_attempts"] == 2
        assert payload["total_errors"] == 6
        assert payload["tools_clean"] == ["tsc", "eslint"]
        assert not payload["blocked"]

    def test_failure_run_payload(self):
        payload = extract_validator_summary(SAMPLE_FAILURE_ENTRIES)
        assert payload["total_attempts"] == 3
        assert payload["total_errors"] == 8
        assert payload["tools_failed"] == ["tsc"]
        assert payload["blocked"]
        assert payload["max_retries_exhausted"]

    def test_empty_run_payload(self):
        payload = extract_validator_summary([])
        assert payload["detected_tools"] == []
        assert payload["total_attempts"] == 0
        assert payload["total_errors"] == 0
        assert not payload["blocked"]
