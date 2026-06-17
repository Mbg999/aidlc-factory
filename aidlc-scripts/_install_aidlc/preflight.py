from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .constants import (
    PREFLIGHT_EXIT_CODE,
    TOOL_DESCRIPTIONS,
    VALID_TOOLS,
)
from .utils import _log, _parse_semver, _probe_version


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Install AI-DLC rules into a project for one or more agent tools",
        epilog="Examples:\n"
               "  pipx run aidlc-factory-installer --tool claude --dest ./my-project\n"
               "  uvx aidlc-factory-installer --tool claude --dest ./my-project\n"
               "  python aidlc-scripts/install_aidlc.py --tool claude",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--tool", required=False,
                   help="Target agent/tool(s) to install rules for. Comma-separated for multiple "
                        "(e.g., --tool claude,opencode). Valid: " + ", ".join(VALID_TOOLS))
    p.add_argument("--yes", action="store_true", help="Assume yes for confirmations")
    p.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    p.add_argument("--source", type=str, default=None,
                   help="Source path for AIDLC files (defaults to the repo clone containing this script; "
                        "used by pipx/uvx bootstrap to point at the downloaded repo)")
    p.add_argument("--dest", type=str, default=None, help="Destination path to install rules into (defaults to current directory)")
    p.add_argument("--with-agent-skills", action="store_true", default=True,
                   help="Always install engineering process skills from github.com/addyosmani/agent-skills (default: install)")
    p.add_argument("--agent-skills-path", type=str, default=None,
                   help="Local path to an existing agent-skills clone (skips git clone)")
    p.add_argument("--custom-skills-path", type=str, default=None,
                   help="Path to custom/project-specific skills. Each subdirectory should contain a SKILL.md. "
                        "Installed to .agents/skills/ and override agent-skills with the same name.")
    p.add_argument("--force", action="store_true",
                   help="Re-install / upgrade over an existing installation. Overwrites all "
                        "orchestrator files (kernel, runtime, scripts, contracts, subagents) "
                        "while preserving run state (runs/, knowledge/). "
                        "Without this flag, already-installed tools are skipped (merge mode).")
    p.add_argument("--no-venv", dest="no_venv", action="store_true",
                   help="Skip creating .venv and pip-installing requirements.txt. "
                        "Default: a virtualenv is created at <dest>/.venv and the "
                        "target's requirements.txt is installed into it.")
    p.add_argument("--no-codegraph", dest="with_codegraph", action="store_false", default=True,
                   help="Skip CodeGraph installation.")
    p.add_argument("--no-engram", dest="with_engram", action="store_false", default=True,
                   help="Skip Engram persistent memory setup.")
    p.add_argument("--with-design-system", action="store_true", default=True,
                   help="Install the design system (tokens, primitives, patterns, skills). "
                        "Copies design-system/ + design-system-composer + ui-constraint-validator skills. "
                        "Default: install (recommended for UI projects).")
    p.add_argument("--no-design-system", dest="with_design_system", action="store_false",
                   help="Skip design system installation.")
    p.add_argument("--no-cookbook", dest="with_cookbook", action="store_false", default=True,
                   help="Skip AI Architecture Cookbook installation.")
    p.add_argument("--skip-preflight", action="store_true",
                   help="Skip the upfront prerequisite check (python/git/node/npm/etc). "
                        "Use only if you know what you're doing — missing prereqs will "
                        "surface as cryptic errors later in the install.")
    return p.parse_args()


def _preflight_specs(args: argparse.Namespace, tools: list[str] | None = None) -> list[tuple]:
    tools = tools or []
    with_engram = bool(getattr(args, "with_engram", True))
    with_codegraph = bool(getattr(args, "with_codegraph", True))
    using_agent_skills = bool(getattr(args, "with_agent_skills", True)) and not getattr(args, "agent_skills_path", None)

    specs = [
        (
            "Python", [sys.executable, "--version"], (3, 10, 0),
            lambda: True,
            "https://www.python.org/downloads/",
            ["Python 3.10+ is required to run the installer and AIDLC factory scripts.",
             "macOS:          brew install python@3.12  (or: pyenv install 3.12)",
             "Linux (Debian): sudo apt-get install python3 python3-venv python3-pip",
             "Linux (RHEL):   sudo dnf install python3 python3-pip",
             "Windows:        winget install Python.Python.3.12",
             "All platforms:  https://www.python.org/downloads/"],
            None,
        ),
        (
            "Git", ["git", "--version"], None,
            lambda: using_agent_skills,
            "https://git-scm.com/downloads",
            ["macOS:          xcode-select --install",
             "Linux (Debian): sudo apt-get install git",
             "Linux (RHEL):   sudo dnf install git",
             "Windows:        winget install Git.Git",
             "All platforms:  https://git-scm.com/downloads"],
            "not needed (agent skills disabled or local path provided)",
        ),
        (
            "Node.js", ["node", "--version"], (22, 6, 0),
            lambda: True,
            "https://nodejs.org/en/download",
            ["macOS via brew:      brew install node@22",
             "macOS/Linux via nvm:",
             "  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash",
             "  nvm install 22 && nvm use 22",
             "Linux (Debian):      sudo apt-get install -y nodejs npm",
             "Linux (RHEL):        sudo dnf install nodejs npm",
             "Windows via winget:  winget install OpenJS.NodeJS.LTS",
             "Windows via nvm-win: https://github.com/coreybutler/nvm-windows",
             "All platforms:       https://nodejs.org/en/download",
             "Required for autoskills — Node < 22.6 means lockfile-aware skills will not be installed."],
            None,
        ),
        (
            "npm", ["npm", "--version"], None,
            lambda: True,
            "https://nodejs.org/en/download",
            ["npm ships with Node.js — install Node 22+ and npm comes with it."],
            None,
        ),
    ]

    if tools:
        specs += [
            (
                "Claude Code CLI", ["claude", "--version"], None,
                lambda: with_engram and "claude" in tools,
                "https://docs.claude.com/claude-code",
                ["macOS via brew: brew install anthropic/claude/claude",
                 "Or follow the official install at https://docs.claude.com/claude-code",
                 "Not needed if you use --no-engram or a different tool."],
                "not required (engram on Claude uses the claude CLI — no standalone binary needed)",
            ),
            (
                "Engram CLI", ["engram", "--version"], None,
                lambda: with_engram and "opencode" in tools,
                "https://github.com/Gentleman-Programming/engram",
                ["Follow the install instructions at https://github.com/Gentleman-Programming/engram",
                 "Not needed if you use --no-engram or a different tool."],
                "not required (only for engram on OpenCode — for Claude the claude plugin is used instead)",
            ),
        ]

    return specs


def preflight_check(args: argparse.Namespace, tools: list[str] | None = None, label: str = "") -> int:
    if getattr(args, "skip_preflight", False):
        print(f"--- Preflight check skipped (--skip-preflight){' -- ' + label if label else ''} ---")
        return 0

    header = "--- Preflight check (prerequisites)"
    if label:
        header += f" -- {label}"
    header += " ---"
    print(f"\n{header}")
    specs = _preflight_specs(args, tools)
    failures: list[tuple] = []
    for spec in specs:
        name, cmd, min_v, required_when, url, hints = spec[:6]
        skip_reason = spec[6] if len(spec) > 6 else None
        if not required_when():
            reason = skip_reason or "not required for this install"
            print(f"  {name:18s} [SKIP]  {reason}")
            continue
        ok, raw = _probe_version(cmd)
        if not ok:
            failures.append((name, "missing", min_v, url, hints, raw))
            print(f"  {name:18s} [FAIL] {raw}")
            continue
        if min_v is None:
            print(f"  {name:18s} [OK] {raw}")
            continue
        parsed = _parse_semver(raw)
        if parsed is None or parsed < min_v:
            failures.append((name, "version_too_old", min_v, url, hints, raw))
            min_v_str = ".".join(str(p) for p in min_v)
            print(f"  {name:18s} [FAIL] {raw} (need >= {min_v_str})")
        else:
            min_v_str = ".".join(str(p) for p in min_v)
            print(f"  {name:18s} [OK] {raw} (>= {min_v_str})")

    if not failures:
        print("  All prerequisites satisfied.\n")
        return 0

    if args.dry_run:
        print(f"\n[DRY-RUN] {len(failures)} prerequisite(s) would block this install -- continuing dry-run.\n")
        return 0

    print()
    print("=" * 70)
    print(f"[FAIL] Cannot proceed -- {len(failures)} prerequisite(s) missing.")
    print("=" * 70)
    for name, kind, min_v, url, hints, raw in failures:
        print()
        if kind == "missing":
            print(f"  Missing: {name}")
        else:
            min_v_str = ".".join(str(p) for p in min_v)
            print(f"  Outdated: {name} -- detected {raw}, need >= {min_v_str}")
        print(f"  Docs:    {url}")
        for h in hints:
            print(f"    {h}")
    print()
    print("Fix the failures above, then re-run this installer.")
    print("(To bypass at your own risk, re-run with --skip-preflight.)")
    print()
    return PREFLIGHT_EXIT_CODE


def interactive_choose_tools() -> list[str]:
    choices = list(VALID_TOOLS)
    print()
    print("Which agentic coding tool(s) do you use?")
    print("AIDLC will install the integration files for each tool you select.")
    print()
    for i, c in enumerate(choices, 1):
        desc = TOOL_DESCRIPTIONS.get(c, "")
        print(f"  {i}) {c:9s} {desc}")
    print()
    print("Pick one number, or comma-separated for multiple.")
    print("Examples:")
    print("  '2'    -> Claude Code only")
    print("  '2,4'  -> Claude Code + OpenCode")
    while True:
        try:
            v = input("Your choice: ").strip()
        except KeyboardInterrupt:
            print("\nAborted by user")
            sys.exit(1)
        if not v:
            print("  Please enter a number from 1 to {}. Example: '2'.".format(len(choices)))
            continue
        try:
            indices = [int(x.strip()) - 1 for x in v.split(",") if x.strip()]
        except ValueError:
            print(f"  That doesn't look right -- enter numbers only (you entered: {v!r}).")
            print(f"  Example: '2' or '2,4'.")
            continue
        if not indices:
            print(f"  No numbers found in {v!r}. Example: '2' or '2,4'.")
            continue
        out_of_range = [i + 1 for i in indices if i < 0 or i >= len(choices)]
        if out_of_range:
            print(f"  Out of range: {out_of_range}. Valid: 1-{len(choices)}.")
            continue
        seen: set[str] = set()
        out: list[str] = []
        for idx in indices:
            name = choices[idx]
            if name not in seen:
                seen.add(name)
                out.append(name)
        return out


def _prompt_destination() -> Path:
    cwd = Path.cwd()
    print()
    print("Where should AIDLC be installed?")
    print("This is the root of the project you want to add AIDLC to.")
    print()
    print("Examples:")
    print("  .                           current directory")
    print("  ~/projects/my-app           absolute path with home expansion")
    print(f"  {cwd}   full absolute path")
    print()
    while True:
        try:
            resp = input(f"Destination [default: {cwd}]: ").strip().strip("'\"")
        except KeyboardInterrupt:
            print("\nAborted by user")
            sys.exit(1)
        if not resp:
            return cwd
        try:
            return Path(resp).expanduser().resolve()
        except (OSError, RuntimeError) as e:
            print(f"  Could not resolve {resp!r}: {e}. Try again.")
