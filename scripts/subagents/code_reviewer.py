#!/usr/bin/env python3
"""Code Reviewer subagent.

Runs fast, non-destructive code quality and security checks:
- Linters: ruff (preferred) > flake8 > pylint for Python; eslint for JS/TS
- Security patterns: hardcoded secrets, unsafe calls, OWASP-aligned heuristics
- Structured report written to aidlc-docs/reporting/code-review-<timestamp>.md

Returns a structured dict compatible with manager.py output schema:
  {"agent_id": ..., "status": "ok"|"warning"|"error",
   "blocking": bool, "findings": [...], "report_path": ...}
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

AGENT_ID = "code-reviewer"

# ---------------------------------------------------------------------------
# Security heuristics (OWASP Top 10 aligned)
# ---------------------------------------------------------------------------
_SECRET_PATTERNS: list[tuple[str, str]] = [
    (r"(?i)(password|passwd|pwd)\s*=\s*['\"][^'\"]{4,}", "A02 - Hardcoded password"),
    (r"(?i)(api[_-]?key|apikey)\s*=\s*['\"][A-Za-z0-9/+_\-]{8,}", "A02 - Hardcoded API key"),
    (r"(?i)(secret|token)\s*=\s*['\"][A-Za-z0-9/+_\-]{8,}", "A02 - Hardcoded secret/token"),
    (r"(?i)aws_secret_access_key\s*=\s*['\"][^'\"]+", "A02 - AWS secret key hardcoded"),
    (r"(?i)-----BEGIN (RSA|EC|OPENSSH) PRIVATE KEY-----", "A02 - Private key in source"),
]

_UNSAFE_PATTERNS: list[tuple[str, str]] = [
    (r"\beval\s*\(", "A03 - eval() usage (code injection risk)"),
    (r"\bexec\s*\(", "A03 - exec() usage (code injection risk)"),
    (r"\bpickle\.loads?\s*\(", "A08 - pickle deserialization (unsafe)"),
    (r"\bos\.system\s*\(", "A01 - os.system() (prefer subprocess with args list)"),
    (r"\bsubprocess\.call\s*\(.*shell\s*=\s*True", "A01 - shell=True in subprocess"),
    (r"\bsubprocess\.run\s*\(.*shell\s*=\s*True", "A01 - shell=True in subprocess"),
    (r"(?i)sql\s*=\s*['\"].*\+\s*\w", "A03 - Possible SQL concatenation (injection risk)"),
    (r"\bMD5\b|\bmd5\b", "A02 - MD5 is cryptographically broken"),
    (r"\bSHA1\b|\bsha1\b", "A02 - SHA1 is cryptographically broken"),
    (r"random\.random\(\)|random\.randint\(", "A02 - Weak RNG (use secrets module for security)"),
]

_TODO_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX)\b", re.I)


def _gather_source_files(base: Path, exts: tuple[str, ...] = (".py", ".js", ".ts")) -> list[Path]:
    skip_dirs = {"node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build", ".tox"}
    out: list[Path] = []
    for p in base.rglob("*"):
        if any(part in skip_dirs for part in p.parts):
            continue
        if p.is_file() and p.suffix in exts:
            out.append(p)
    return sorted(out)


def _run_cmd(cmd: list[str], cwd: Path, timeout: int = 60) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout
        )
        return {
            "exit_code": proc.returncode,
            "stdout": proc.stdout[:10_000],
            "stderr": proc.stderr[:2_000],
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "error": f"timeout after {timeout}s"}
    except Exception as exc:
        return {"exit_code": -1, "error": str(exc)}


def _scan_security(files: list[Path]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    all_patterns = [
        (re.compile(pat), label, "blocking")
        for pat, label in _SECRET_PATTERNS
    ] + [
        (re.compile(pat), label, "warning")
        for pat, label in _UNSAFE_PATTERNS
    ]

    for f in files:
        try:
            lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines, 1):
            for compiled, label, severity in all_patterns:
                if compiled.search(line):
                    findings.append({
                        "file": str(f),
                        "line": i,
                        "label": label,
                        "severity": severity,
                        "snippet": line.strip()[:120],
                    })
    return findings


def _scan_todos(files: list[Path]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for f in files:
        try:
            lines = f.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            continue
        for i, line in enumerate(lines, 1):
            if _TODO_RE.search(line):
                findings.append({"file": str(f), "line": i, "snippet": line.strip()[:120]})
    return findings


def _run_linters(workspace: Path) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}

    # Python linters: ruff > flake8
    if shutil.which("ruff"):
        results["ruff"] = _run_cmd(
            ["ruff", "check", "--output-format", "concise", str(workspace)], workspace
        )
    elif shutil.which("flake8"):
        results["flake8"] = _run_cmd(["flake8", str(workspace)], workspace)

    # JS/TS linter
    if shutil.which("eslint"):
        results["eslint"] = _run_cmd(
            ["eslint", "--format", "compact", str(workspace)], workspace
        )

    return results


def _write_report(out_path: Path, workspace: Path, security: list, todos: list, linters: dict, skills: dict) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    blocking = [f for f in security if f.get("severity") == "blocking"]
    warnings = [f for f in security if f.get("severity") == "warning"]

    lines: list[str] = [
        f"# Code Review Report\n\n",
        f"Generated: {ts}  \nWorkspace: `{workspace}`\n\n",
        f"**Status:** {'❌ BLOCKING' if blocking else ('⚠️ WARNINGS' if (warnings or todos) else '✅ CLEAN')}\n\n",
    ]

    lines.append("## Security Findings\n\n")
    if blocking:
        lines.append(f"### Blocking ({len(blocking)})\n\n")
        for f in blocking:
            lines.append(f"- **{f['label']}** — `{f['file']}:{f['line']}`\n")
            lines.append(f"  ```\n  {f['snippet']}\n  ```\n")
    if warnings:
        lines.append(f"\n### Warnings ({len(warnings)})\n\n")
        for f in warnings:
            lines.append(f"- {f['label']} — `{f['file']}:{f['line']}`\n")
    if not security:
        lines.append("No security issues found.\n")

    lines.append("\n## TODOs / FIXMEs\n\n")
    if todos:
        for t in todos[:50]:  # cap at 50
            lines.append(f"- `{t['file']}:{t['line']}` — {t['snippet']}\n")
        if len(todos) > 50:
            lines.append(f"- … and {len(todos) - 50} more\n")
    else:
        lines.append("None found.\n")

    if linters:
        lines.append("\n## Linter Output\n\n")
        for name, res in linters.items():
            lines.append(f"### {name} (exit {res.get('exit_code')})\n\n")
            if res.get("error"):
                lines.append(f"Error: {res['error']}\n")
            else:
                out = (res.get("stdout") or "").strip()
                lines.append(f"```\n{out[:3000]}\n```\n\n" if out else "No output.\n\n")

    if skills:
        lines.append("\n## Skills Applied\n\n")
        for name in skills:
            lines.append(f"- `{name}`\n")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(lines), encoding="utf-8")


def run(context: dict | None = None) -> dict:
    ctx = context or {}
    workspace = Path(ctx.get("workspace") or ctx.get("path") or ctx.get("run_folder") or ".")
    if not workspace.is_absolute():
        workspace = (Path(__file__).resolve().parents[2] / workspace).resolve()

    docs = Path(ctx.get("aidlc_docs") or workspace.parent / "aidlc-docs")
    reporting = docs / "reporting"
    ts_slug = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    report_path = reporting / f"code-review-{ts_slug}.md"

    files = _gather_source_files(workspace)
    security_findings = _scan_security(files)
    todo_findings = _scan_todos(files)
    linter_results = _run_linters(workspace)
    skills: dict = ctx.get("skills") or {}

    _write_report(report_path, workspace, security_findings, todo_findings, linter_results, skills)

    blocking = [f for f in security_findings if f.get("severity") == "blocking"]
    is_blocking = len(blocking) > 0

    # --- Memory: emit learnings for write-back by the manager ---
    memory_observations: list[dict] = []
    if security_findings:
        labels = list({f.get("label", "") for f in security_findings if f.get("label")})
        memory_observations.append({
            "content": (
                f"Code review found {len(blocking)} blocking and "
                f"{len(security_findings)-len(blocking)} warning security issues in {workspace.name}. "
                f"Patterns: {', '.join(labels[:5])}"
            ),
            "tags": ["security", "code-review", workspace.name],
            "memory_type": "episodic",
        })
    if todo_findings:
        memory_observations.append({
            "content": f"Found {len(todo_findings)} TODO/FIXME markers in {workspace.name}",
            "tags": ["todos", "code-review", workspace.name],
            "memory_type": "episodic",
        })
    if linter_results:
        clean = [t for t, r in linter_results.items() if r.get("exit_code") == 0]
        memory_observations.append({
            "content": f"Linters run in {workspace.name}: {list(linter_results.keys())}. Clean: {clean}",
            "tags": ["linting", "code-review", workspace.name],
            "memory_type": "semantic",
        })

    return {
        "agent_id": AGENT_ID,
        "status": "error" if is_blocking else ("warning" if security_findings or todo_findings else "ok"),
        "blocking": is_blocking,
        "findings": {
            "security_blocking": len(blocking),
            "security_warnings": len([f for f in security_findings if f.get("severity") == "warning"]),
            "todos": len(todo_findings),
            "linters_run": list(linter_results.keys()),
        },
        "report_path": str(report_path),
        "memory_observations": memory_observations,
    }


if __name__ == "__main__":
    import sys

    ctx: dict = {}
    if len(sys.argv) > 1:
        try:
            ctx = json.loads(sys.argv[1])
        except Exception:
            ctx = {"path": sys.argv[1]}
    print(json.dumps(run(ctx), ensure_ascii=False, indent=2))
