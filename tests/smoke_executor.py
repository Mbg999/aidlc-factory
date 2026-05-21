import json
import subprocess
import sys
from pathlib import Path


def test_runner_echo():
    repo = Path(__file__).resolve().parents[1]
    runner = repo / "aidlc-scripts" / "executors" / "runner.py"
    payload = {
        "run_folder": str(repo / "runs" / "smoke-exec"),
        "actions": [
            {"action": "run_script", "script": "aidlc-scripts/test_scripts/echo.py", "args": ["hello", "world"]}
        ],
    }
    # Ensure run_folder exists for runner cwd
    (repo / "runs" / "smoke-exec").mkdir(parents=True, exist_ok=True)
    p = subprocess.run([sys.executable, str(runner)], input=json.dumps(payload), text=True, capture_output=True)
    assert p.returncode == 0
    out = json.loads(p.stdout)
    assert "results" in out
    res = out["results"][0]
    assert res.get("ok") is True
    assert "hello world" in (res.get("stdout") or "")
