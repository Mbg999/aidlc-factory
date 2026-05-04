import json
import runpy
import tempfile
import time
from pathlib import Path

MGR_PATH = Path(__file__).resolve().parents[2] / "scripts" / "subagents" / "manager.py"


def test_opt_in_enforced(tmp_path):
    # No opt-in file -> agent requiring opt-in should be blocked when run_folder provided
    mod = runpy.run_path(str(MGR_PATH))
    run_fn = mod["run"]

    run_folder = tmp_path / "run1"
    run_folder.mkdir()
    res = run_fn("code-reviewer", {"run_folder": str(run_folder)})
    assert isinstance(res, dict)
    assert res.get("error") and "opt-in required" in res.get("error")


def test_audit_log_written_when_opted_in(tmp_path):
    # Create run folder and opt-in state enabling code-reviewer
    mod = runpy.run_path(str(MGR_PATH))
    run_fn = mod["run"]

    run_folder = tmp_path / "run2"
    docs = run_folder / "aidlc-docs"
    docs.mkdir(parents=True)
    state = {"subagents": {"code-reviewer": True}}
    (docs / "aidlc-state.json").write_text(json.dumps(state))

    res = run_fn("code-reviewer", {"run_folder": str(run_folder)})
    assert isinstance(res, dict)
    assert res.get("status") == "ok"

    logs_dir = run_folder / "subagents-logs"
    assert logs_dir.exists() and logs_dir.is_dir()
    files = list(logs_dir.iterdir())
    assert files, "No audit logs written"
    # Basic sanity of log content
    log = json.loads(files[0].read_text(encoding="utf-8"))
    assert log.get("parsed_result") or log.get("returncode") is not None


def test_agent_timeout_respected(tmp_path):
    # Create a slow agent script and a temporary agents.json to point to it
    agent_py = tmp_path / "slow_agent.py"
    agent_py.write_text(
        "import time, json\n"
        "def run(context=None):\n"
        "    time.sleep(2)\n"
        "    return {'agent_id':'slow-test','status':'ok'}\n"
    )

    agents_cfg = tmp_path / "agents.json"
    cfg = {"agents": [{"id": "slow-test", "entrypoint": str(agent_py)}]}
    agents_cfg.write_text(json.dumps(cfg))

    mod = runpy.run_path(str(MGR_PATH))
    run_fn = mod["run"]

    # Call with small timeout (1s) and the temp agents.json as conf_path
    res = run_fn("slow-test", {}, conf_path=str(agents_cfg), timeout=1)
    assert isinstance(res, dict)
    # Should return an audit dict with error due to timeout, or contain 'timeout' text
    err = res.get("error") or res.get("result", {}).get("error")
    assert err and ("timeout" in str(err).lower())
