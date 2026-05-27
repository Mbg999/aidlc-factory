"""aidlc-factory-installer CLI — bootstraps from PyPI, runs the real installer from GitHub source.

When installed via pip/pipx/uvx, this tiny package downloads the latest AIDLC source
from GitHub, then delegates to the actual ``install_aidlc.py`` inside it.

This keeps the PyPI package small (~5 KB) while the full source (agents, contracts,
scripts, skills) stays on GitHub.

Usage:
    pipx run aidlc-factory-installer --tool claude
    uvx aidlc-factory-installer --tool claude
    python -m aidlc_installer --tool claude

    # Or via pip (for repeat use):
    pip install aidlc-factory-installer
    aidlc-factory-installer --tool claude
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

REPO_ZIP = "https://github.com/Mbg999/aidlc-factory/archive/refs/heads/main.zip"
MIN_PYTHON = (3, 10)


def _check_python() -> None:
    if sys.version_info < MIN_PYTHON:
        print(
            f"ERROR: Python {'.'.join(str(v) for v in MIN_PYTHON)}+ required "
            f"(detected {sys.version})",
            file=sys.stderr,
        )
        sys.exit(9)


def _download_repo() -> Path:
    """Download the repo zip from GitHub, extract to a temp dir, return root path."""
    tmp = Path(tempfile.mkdtemp(prefix="aidlc-"))
    zip_path = tmp / "source.zip"
    print("Downloading AIDLC installer from GitHub...", file=sys.stderr)
    try:
        urllib.request.urlretrieve(REPO_ZIP, zip_path)
    except Exception as exc:
        shutil.rmtree(tmp, ignore_errors=True)
        print(f"ERROR: Failed to download AIDLC source: {exc}", file=sys.stderr)
        print(f"  URL: {REPO_ZIP}", file=sys.stderr)
        print("  Check your internet connection or download manually from the repo.", file=sys.stderr)
        sys.exit(9)

    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(tmp)
    zip_path.unlink()

    # GitHub zipball: single root directory named <repo>-<branch>
    entries = sorted(tmp.iterdir())
    if not entries:
        shutil.rmtree(tmp, ignore_errors=True)
        print("ERROR: Downloaded archive is empty.", file=sys.stderr)
        sys.exit(9)
    return tmp / entries[0]


def main() -> int:
    _check_python()

    repo_root = _download_repo()

    # Rebuild argv so the downstream installer sees:
    #   install_aidlc.py --source <repo_root> [original args]
    orig = sys.argv[1:]  # everything after the entry-point command
    # Strip any --source already provided by the user (we override it)
    filtered: list[str] = []
    skip = False
    for a in orig:
        if skip:
            skip = False
            continue
        if a == "--source":
            skip = True
            continue
        if a.startswith("--source="):
            continue
        filtered.append(a)
    sys.argv = [
        str(repo_root / "aidlc-scripts" / "install_aidlc.py"),
        "--source", str(repo_root),
        *filtered,
    ]
    # Load aidlc-scripts/install_aidlc.py via importlib (dash is invalid in Python module names)
    installer_path = repo_root / "aidlc-scripts" / "install_aidlc.py"
    spec = importlib.util.spec_from_file_location("install_aidlc", str(installer_path))
    if spec is None or spec.loader is None:
        print(f"ERROR: Could not load installer from {installer_path}", file=sys.stderr)
        return 3
    mod = importlib.util.module_from_spec(spec)
    sys.modules["install_aidlc"] = mod
    sys.path.insert(0, str(repo_root))

    try:
        spec.loader.exec_module(mod)
        return mod.main()
    except KeyboardInterrupt:
        print("\nAborted by user.")
        return 1
    finally:
        shutil.rmtree(repo_root.parent, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
