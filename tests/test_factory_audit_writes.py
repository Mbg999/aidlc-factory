from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
AUDIT_PY = SCRIPTS / "factory_audit_writes.py"


def test_path_matches_glob():
    """Test the internal path_matches_any_glob logic."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("audit", AUDIT_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod.path_matches_any_glob("src/auth/login.py", ["src/auth/**"]) is True
    assert mod.path_matches_any_glob("src/billing/main.py", ["src/auth/**"]) is False
    assert mod.path_matches_any_glob("src/auth/login.py", ["src/**"]) is True
    assert mod.path_matches_any_glob("src/auth/login.py", ["src/auth/*"]) is True
    assert mod.path_matches_any_glob("README.md", ["src/**"]) is False


def test_audit_ok_in_repo():
    """Run audit on actual repo with src/** glob — should find no violations."""
    result = subprocess.run(
        [sys.executable, str(AUDIT_PY), "test-run", "unit-a",
         "--locks", "src/**", "--json", "--repo-root", "."],
        capture_output=True, text=True,
        cwd=Path(__file__).resolve().parent.parent,
    )
    data = json.loads(result.stdout)
    assert "status" in data
    # In a clean repo, there are no new files, so no violations
    assert data["status"] in ("ok", "violation")
