from __future__ import annotations

import subprocess
from pathlib import Path

from .constants import AGENT_SKILLS_REPO, WORKFLOW_REQUIRED_SKILLS
from .utils import copy_tree, _rmtree_force


def clone_agent_skills(dest: Path, dry_run: bool) -> Path:
    if dry_run:
        print(f"[DRY-RUN] Would clone {AGENT_SKILLS_REPO} into {dest}")
        return dest
    if dest.exists() and (dest / ".git").exists():
        print(f"Agent-skills repo already exists at {dest}, pulling latest...")
        subprocess.run(["git", "-C", str(dest), "pull", "--ff-only"], check=False)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Cloning agent-skills from {AGENT_SKILLS_REPO}...")
    subprocess.run(
        ["git", "clone", "--depth", "1", "--single-branch", "--no-tags", AGENT_SKILLS_REPO, str(dest)],
        check=True,
    )
    return dest


def install_agent_skills(tool: str, skills_repo: Path, target_root: Path, dry_run: bool) -> int:
    skills_dest = target_root / ".agents" / "skills"
    count = 0
    if dry_run:
        print(f"[DRY-RUN] Would install agent-skills to {skills_dest}")
    else:
        skills_dest.mkdir(parents=True, exist_ok=True)
    skills_src = skills_repo / "skills"
    if skills_src.exists():
        for skill_dir in sorted(skills_src.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            target_dir = skills_dest / skill_dir.name
            if dry_run:
                print(f"[DRY-RUN]   {skill_dir.name}/ -> {target_dir}")
            else:
                copy_tree(skill_dir, target_dir, dry_run=False)
            count += 1
    refs_src = skills_repo / "references"
    if refs_src.exists():
        refs_dest = skills_dest / "_references"
        if dry_run:
            print(f"[DRY-RUN]   references/ -> {refs_dest}")
        else:
            copy_tree(refs_src, refs_dest, dry_run=False)
    hooks_src = skills_repo / "hooks"
    if hooks_src.exists():
        hooks_dest = skills_dest.parent / "hooks"
        if dry_run:
            print(f"[DRY-RUN]   hooks/ -> {hooks_dest}")
        else:
            copy_tree(hooks_src, hooks_dest, dry_run=False)
    if not dry_run:
        print(f"Installed {count} agent-skills -> {skills_dest}")
    else:
        print(f"[DRY-RUN] Would install {count} skills to {skills_dest}")
    if not dry_run and skills_dest.exists():
        installed_names = {d.name for d in skills_dest.iterdir() if d.is_dir()}
        found = sorted(set(WORKFLOW_REQUIRED_SKILLS) & installed_names)
        missing = sorted(set(WORKFLOW_REQUIRED_SKILLS) - installed_names)
        print(f"\n  Workflow skills coverage: {len(found)}/{len(WORKFLOW_REQUIRED_SKILLS)}")
        if missing:
            print(f"  WARNING -- Missing skills (workflow will use inline fallbacks): {', '.join(missing)}")
    return count


def _copy_skill_dirs(src_dir: Path, target_root: Path, dry_run: bool) -> int:
    skills_dest = target_root / ".agents" / "skills"
    skills_dest.mkdir(parents=True, exist_ok=True)
    count = 0
    for skill_dir in sorted(src_dir.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue
        target_dir = skills_dest / skill_dir.name
        if dry_run:
            print(f"[DRY-RUN]   {skill_dir.name}/ -> {target_dir}")
        else:
            print(f"  {skill_dir.name}/ -> .agents/skills/{skill_dir.name}/")
            copy_tree(skill_dir, target_dir, dry_run=False)
        count += 1
    if count == 0 and not dry_run:
        print("  (no SKILL.md files found in custom skills path)")
    if count:
        print(f"Installed {count} custom skill(s)")
    return count
