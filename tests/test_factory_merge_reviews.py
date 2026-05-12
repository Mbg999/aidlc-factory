from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
MERGE_PY = SCRIPTS / "factory_merge_reviews.py"


def _run(args, env_setup, text=True):
    return subprocess.run(
        [sys.executable, str(MERGE_PY)] + args,
        capture_output=True, text=text, env={**__import__("os").environ},
    )


def test_merge_single_reviewer(env_setup, run_id):
    """Merge with one valid reviewer output."""
    subprocess.run(
        [sys.executable, str(SCRIPTS / "factory_run.py"), "init", run_id,
         "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )

    # Create reviewer output
    aidlc_root = Path(__import__("os").environ["AIDLC_ROOT"])
    handoffs = aidlc_root / ".aidlc-orchestrator" / "runs" / run_id / "handoffs"
    handoffs.mkdir(parents=True, exist_ok=True)

    import yaml
    output = {
        "status": "complete",
        "reviewer": "code-quality",
        "findings": [
            {"severity": "P1", "file": "src/auth.py", "line": 42,
             "message": "Hardcoded secret detected", "recommendation": "Use env var",
             "axis": "security"},
        ],
        "findings_summary": {"P0_count": 0, "P1_count": 1, "P2_count": 0, "P3_count": 0},
        "audit_entries": ["Reviewed all auth code"],
        "skill_compliance": [
            {"skill": "security-review", "status": "PASS", "evidence": "No OWASP top 10 violations"},
            {"skill": "code-standards", "status": "PASS", "evidence": "Follows project conventions"},
        ],
    }
    (handoffs / "reviewer-code.output.yaml").write_text(yaml.safe_dump(output))

    r = _run([run_id, "--output", str(aidlc_root / "test-report.md")], env_setup)
    assert r.returncode == 0
    assert "wrote" in r.stdout


def test_merge_no_outputs(env_setup, run_id):
    """Merge with no reviewer outputs should exit 1."""
    subprocess.run(
        [sys.executable, str(SCRIPTS / "factory_run.py"), "init", run_id,
         "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )

    r = _run([run_id], env_setup)
    assert r.returncode == 1


def test_merge_missing_reviewer(env_setup, run_id):
    """Merge should warn about missing reviewer but still succeed."""
    subprocess.run(
        [sys.executable, str(SCRIPTS / "factory_run.py"), "init", run_id,
         "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )

    aidlc_root = Path(__import__("os").environ["AIDLC_ROOT"])
    handoffs = aidlc_root / ".aidlc-orchestrator" / "runs" / run_id / "handoffs"
    handoffs.mkdir(parents=True, exist_ok=True)

    import yaml
    output = {
        "status": "complete",
        "reviewer": "code-quality",
        "findings": [],
        "findings_summary": {"P0_count": 0, "P1_count": 0, "P2_count": 0, "P3_count": 0},
        "audit_entries": ["Check complete"],
        "skill_compliance": [
            {"skill": "security-review", "status": "PASS", "evidence": "OK"},
            {"skill": "code-standards", "status": "PASS", "evidence": "OK"},
        ],
    }
    (handoffs / "reviewer-code.output.yaml").write_text(yaml.safe_dump(output))

    r = _run([run_id, "--output", str(aidlc_root / "test-report.md"),
              "--reviewers", "code-quality", "security"], env_setup)
    assert r.returncode == 0
    assert "missing" in r.stderr


def test_merge_all_four(env_setup, run_id):
    """Merge with all 4 reviewers should produce a complete report."""
    subprocess.run(
        [sys.executable, str(SCRIPTS / "factory_run.py"), "init", run_id,
         "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )

    aidlc_root = Path(__import__("os").environ["AIDLC_ROOT"])
    handoffs = aidlc_root / ".aidlc-orchestrator" / "runs" / run_id / "handoffs"
    handoffs.mkdir(parents=True, exist_ok=True)

    import yaml
    reviewers = {
        "code-quality": "reviewer-code",
        "security": "reviewer-security",
        "performance": "reviewer-performance",
        "simplifier": "reviewer-simplifier",
    }
    base_output = {
        "status": "complete",
        "findings": [],
        "findings_summary": {"P0_count": 0, "P1_count": 0, "P2_count": 0, "P3_count": 0},
        "audit_entries": ["Check complete"],
        "skill_compliance": [
            {"skill": "security-review", "status": "PASS", "evidence": "OK"},
            {"skill": "code-standards", "status": "PASS", "evidence": "OK"},
        ],
    }

    for rev_name, stage in reviewers.items():
        output = {**base_output, "reviewer": rev_name}
        (handoffs / f"{stage}.output.yaml").write_text(yaml.safe_dump(output))

    r = _run([run_id, "--output", str(aidlc_root / "test-report.md")], env_setup)
    assert r.returncode == 0
    assert "wrote" in r.stdout
