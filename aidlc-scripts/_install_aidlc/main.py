from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .codegraph import _auto_init_codegraph, install_codegraph
from .cookbook import _install_cookbook
from .design_system import install_design_system
from .engram import install_engram
from .orchestrator import install_orchestrator
from .preflight import (
    _prompt_destination,
    interactive_choose_tools,
    parse_args,
    preflight_check,
)
from .skills import _copy_skill_dirs, clone_agent_skills, install_agent_skills
from .utils import (
    _rmtree_force,
    create_venv_and_install_requirements,
    ensure_target_requirements,
    parse_tools_string,
)


def _handle_agent_skills(args, tools: list[str], target_root: Path) -> int | None:
    skills_dir = target_root / ".agents" / "skills"
    skills_already = skills_dir.exists() and any(skills_dir.iterdir()) if skills_dir.exists() else False
    if args.with_agent_skills and skills_already and not args.force:
        print(f"\nAgent skills already installed at {skills_dir.relative_to(target_root)} -- skipping (use --force to re-install).")
        return None
    if not args.with_agent_skills:
        return None

    print("\n--- Installing Agent Skills (addyosmani/agent-skills) ---")
    if args.agent_skills_path:
        skills_repo = Path(args.agent_skills_path).expanduser().resolve()
        if not skills_repo.exists():
            print(f"ERROR: Provided agent-skills path does not exist: {skills_repo}")
            return 5
    else:
        skills_repo = target_root / ".agent-skills-repo"
        try:
            clone_agent_skills(skills_repo, args.dry_run)
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"ERROR: Failed to clone agent-skills repo: {e}")
            print("  Ensure 'git' is installed, or use --agent-skills-path to provide a local clone.")
            return 5

    try:
        for tool in tools:
            install_agent_skills(tool, skills_repo, target_root, args.dry_run)
    except Exception as e:
        print(f"ERROR installing agent-skills: {e}")
        return 5

    if not args.agent_skills_path and skills_repo.exists() and not args.dry_run:
        print(f"Cleaning up temporary clone: {skills_repo}")
        _rmtree_force(skills_repo)
    elif args.dry_run and not args.agent_skills_path:
        print(f"[DRY-RUN] Would remove temporary clone: {skills_repo}")
    return None


def _handle_custom_skills(args, repo_root: Path, target_root: Path) -> int | None:
    if args.custom_skills_path:
        custom_src = Path(args.custom_skills_path).expanduser().resolve()
        if not custom_src.exists():
            print(f"ERROR: Custom skills path not found: {custom_src}")
            return 5
        print(f"\n--- Installing Custom Skills ---")
        return _copy_skill_dirs(custom_src, target_root, args.dry_run)

    bundled_custom = repo_root / ".agents" / "custom-skills"
    if bundled_custom.exists():
        print(f"\n--- Installing Bundled Custom Skills ---")
        count = _copy_skill_dirs(bundled_custom, target_root, args.dry_run)
        if count:
            print(f"Installed {count} bundled custom skill(s)")
    return None


def _handle_orchestrator(tools: list[str], repo_root: Path, target_root: Path, args) -> int | None:
    try:
        install_orchestrator(tools, repo_root, target_root, args.dry_run, force=args.force, args=args)
    except Exception as e:
        print(f"ERROR installing orchestrator: {e}")
        return 6
    return None


def _handle_codegraph(tools: list[str], target_root: Path, args) -> None:
    if not args.with_codegraph:
        return
    try:
        install_codegraph(tools, target_root, args.dry_run)
    except Exception as e:
        print(f"ERROR installing CodeGraph: {e}")
        print("  CodeGraph is optional -- AIDLC will degrade gracefully without it.")


def _handle_engram(tools: list[str], target_root: Path, args) -> None:
    if args.with_engram:
        install_engram(tools, target_root, args.dry_run)


def _handle_design_system(repo_root: Path, target_root: Path, args) -> None:
    if not args.with_design_system:
        return
    try:
        install_design_system(repo_root, target_root, args.dry_run)
    except Exception as e:
        print(f"ERROR installing design system: {e}")
        print("  Design system is optional -- AIDLC will degrade gracefully without it.")


def _handle_cookbook(repo_root: Path, target_root: Path, tools: list[str], args) -> None:
    if not args.with_cookbook:
        return
    try:
        _install_cookbook(repo_root, target_root, args.dry_run, tools=tools)
    except Exception as e:
        print(f"ERROR installing Cookbook: {e}")
        print("  Cookbook MCP runs via npx (@ai-architecture-cookbook/mcp-server) -- Node.js is required at runtime.")
        print("  YAML fallback data may be incomplete if the source was unavailable.")


def _handle_venv(repo_root: Path, target_root: Path, args) -> None:
    if args.no_venv:
        print("\nSkipped Python venv setup (--no-venv).")
        return
    req_path = ensure_target_requirements(repo_root, target_root, args.dry_run)
    if req_path is None:
        print("\nNo requirements.txt found in target or source -- skipping venv setup.")
        return
    print("\n--- Setting up Python venv + dependencies ---")
    try:
        create_venv_and_install_requirements(target_root, req_path, args.dry_run)
    except EnvironmentError as e:
        print(f"WARNING: Could not create venv: {e}")
        print("  You can install deps manually:  pip install -r requirements.txt")
    except RuntimeError as e:
        print(f"WARNING: {e}")
        _pip_venv = ".venv/bin/pip" if sys.platform != "win32" else ".venv\\Scripts\\pip"
        print(f"  You can retry manually:  {_pip_venv} install -r requirements.txt")


def main() -> int:
    args = parse_args()

    rc = preflight_check(args, tools=None, label="core")
    if rc != 0:
        return rc

    if args.dest:
        target_root = Path(args.dest).expanduser().resolve()
    else:
        target_root = _prompt_destination()

    if args.source:
        src = Path(args.source).expanduser().resolve()
        if not src.exists():
            print(f"ERROR: --source path does not exist: {src}")
            return 3
        repo_root = src
    else:
        repo_root = Path(__file__).resolve().parent.parent.parent

    if args.tool:
        try:
            tools = parse_tools_string(args.tool)
        except ValueError as e:
            print(f"ERROR: {e}")
            return 2
    else:
        tools = interactive_choose_tools()

    if not args.tool:
        rc = preflight_check(args, tools=tools, label="tool-specific")
        if rc != 0:
            return rc

    rc = _handle_agent_skills(args, tools, target_root)
    if rc is not None:
        return rc

    rc = _handle_custom_skills(args, repo_root, target_root)
    if rc is not None:
        return rc

    rc = _handle_orchestrator(tools, repo_root, target_root, args)
    if rc is not None:
        return rc

    _handle_codegraph(tools, target_root, args)
    _handle_engram(tools, target_root, args)
    _handle_design_system(repo_root, target_root, args)
    _handle_cookbook(repo_root, target_root, tools, args)
    _handle_venv(repo_root, target_root, args)

    if args.with_codegraph:
        _auto_init_codegraph(target_root, args.dry_run)

    print("Done.")
    return 0
