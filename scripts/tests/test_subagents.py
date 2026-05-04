from pathlib import Path
import runpy


REPO_ROOT = Path(__file__).resolve().parents[2]
MGR_PATH = REPO_ROOT / "scripts" / "subagents" / "manager.py"


def test_load_agents():
    mod = runpy.run_path(str(MGR_PATH))
    load_agents = mod["load_agents"]
    agents = load_agents()
    assert isinstance(agents, list)
    assert any(a.get("id") == "code-reviewer" for a in agents)


def test_run_code_reviewer():
    mod = runpy.run_path(str(MGR_PATH))
    run_fn = mod["run"]
    res = run_fn("code-reviewer", {"sample": "x"})
    assert res.get("status") == "ok"
    assert res.get("agent_id") == "code-reviewer"
    assert any("Lint" in n for n in res.get("notes", []))
