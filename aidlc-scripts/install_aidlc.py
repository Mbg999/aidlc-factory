#!/usr/bin/env python3
"""
install_aidlc.py

Simple installer to copy AI-DLC rule files into the chosen agent integration
location (Cursor, Claude Code, GitHub Copilot, OpenCode, Other).

Optionally fetches and installs engineering process skills from
https://github.com/addyosmani/agent-skills.

Usage examples:
  python aidlc-scripts/install_aidlc.py --tool cursor
  python aidlc-scripts/install_aidlc.py --tool copilot --yes
  python aidlc-scripts/install_aidlc.py --tool claude --dry-run
  python aidlc-scripts/install_aidlc.py --tool copilot --with-agent-skills
"""
from __future__ import annotations

import sys
from pathlib import Path

_scripts_dir = Path(__file__).resolve().parent
if str(_scripts_dir) not in sys.path:
    sys.path.insert(0, str(_scripts_dir))

# Import every name that `import install_aidlc` or `python install_aidlc.py` needs.
# This is the full public API re-exported from the internal _install_aidlc package.
# ruff: noqa: F401, F403
from _install_aidlc import *

if __name__ == "__main__":
    raise SystemExit(main())
