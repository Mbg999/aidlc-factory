from __future__ import annotations

from pathlib import Path

from .constants import DESIGN_SYSTEM_SRCS
from .utils import copy_tree, _rmtree_force


def install_design_system(repo_root: Path, target_root: Path, dry_run: bool) -> None:
    print("\n--- Installing Design System ---")
    for src_name in sorted(DESIGN_SYSTEM_SRCS):
        src = repo_root / src_name
        dst = target_root / src_name
        if not src.exists():
            print(f"  SKIP {src_name} -- not found in repo")
            continue
        if dry_run:
            print(f"[DRY-RUN] Would copy {src_name}/ -> {dst.parent}/")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            _rmtree_force(dst)
            copy_tree(src, dst, dry_run=False)
            print(f"  {src_name}/ -> {dst}")
    print("  Design system installed.")
