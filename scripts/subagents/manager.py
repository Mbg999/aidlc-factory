#!/usr/bin/env python3
"""Simple subagent manager/dispatcher used by AIDLC example tests.

Responsibilities:
- Load `agents.yaml` from aws-aidlc-rule-details/extensions/subagents
- Execute the configured entrypoint (script) and call `run(context)` in it
"""
from __future__ import annotations

import json
import runpy
import subprocess
import tempfile
import os
import shutil
import hashlib
from datetime import datetime, timezone
try:
    import resource
except Exception:
    resource = None
from pathlib import Path
import sys
try:
    import yaml  # type: ignore
except Exception:
    yaml = None

REPO_ROOT = Path(__file__).resolve().parents[2]

# Import skill + MCP bridge helpers (best-effort so manager works without them)
try:
    from mcp_bridge import load_skills_for_agent, build_mcp_bridge  # type: ignore
except ImportError:
    def load_skills_for_agent(cfg, skills_root=None):  # type: ignore
        return {}
    def build_mcp_bridge(cfg, run_folder=None):  # type: ignore
        return None

# Candidate agent config paths (new default name first, fallback to legacy name)
AGENTS_CONF_CANDIDATES = [
    REPO_ROOT / ".aidlc-rule-details" / "extensions" / "subagents" / "agents.yaml",
    REPO_ROOT / "aidlc-rules" / "aidlc-rule-details" / "extensions" / "subagents" / "agents.yaml",
    REPO_ROOT / "aidlc-rules" / "aws-aidlc-rule-details" / "extensions" / "subagents" / "agents.yaml",
]


def load_agents(conf_path: str | Path | None = None) -> list:
    # Resolve configuration path precedence:
    # 1) explicit conf_path argument
    # 2) first existing candidate in AGENTS_CONF_CANDIDATES (prefers new name)
    # 3) default to the first candidate (new name) even if missing
    if conf_path:
        path = Path(conf_path)
    else:
        path = next((p for p in AGENTS_CONF_CANDIDATES if p.exists()), AGENTS_CONF_CANDIDATES[0])

    # Try YAML first (PyYAML), otherwise fallback to JSON file with same base name
    if yaml is not None and path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("agents", [])

    # YAML not available or yaml load failed; try JSON fallback
    json_path = path.with_suffix(".json")
    if json_path.exists():
        import json as _json

        with open(json_path, "r", encoding="utf-8") as f:
            data = _json.load(f) or {}
        return data.get("agents", [])

    return []


def find_agent(agent_id: str, conf_path: str | Path | None = None) -> dict | None:
    agents = load_agents(conf_path)
    return next((a for a in agents if a.get("id") == agent_id), None)


def _compute_file_hash(path: Path) -> str | None:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def _read_opt_in_state(run_folder: str | Path) -> dict:
    """Read opt-in state from run_folder/aidlc-docs/aidlc-state.yaml or .json.

    Returns a dict (possibly empty) or {} on error.
    """
    try:
        rf = Path(run_folder) if run_folder else None
        if not rf:
            return {}
        p_yaml = rf / "aidlc-docs" / "aidlc-state.yaml"
        p_json = rf / "aidlc-docs" / "aidlc-state.json"
        if p_yaml.exists():
            try:
                import yaml as _yaml  # type: ignore
                with open(p_yaml, encoding="utf-8") as f:
                    return _yaml.safe_load(f) or {}
            except Exception:
                try:
                    with open(p_yaml, encoding="utf-8") as f:
                        return json.loads(f.read() or "{}")
                except Exception:
                    return {}
        if p_json.exists():
            try:
                with open(p_json, encoding="utf-8") as f:
                    return json.load(f) or {}
            except Exception:
                return {}
        return {}
    except Exception:
        return {}


def _run_agent_subprocess(agent_id: str, entrypoint: Path, context: dict | None = None, timeout: int = 120, limits: dict | None = None) -> dict:
    """Run the agent entrypoint in a separate Python subprocess.

    - Executes a small wrapper that `runpy.run_path()` the agent file, calls
      its `run(context)` function and prints JSON to stdout.
    - Uses a temporary working directory and a minimal sanitized environment
      so the agent starts with a clean context. PATH/HOME/LANG are preserved
      so tools like `npx` can still be discovered if needed.
    - If `limits` contains `cpu_seconds` or `memory_mb` and the `resource`
      module is available, RLIMITs will be applied to the child process.
    - Audit logs are written to <run_folder>/subagents-logs if `run_folder`
      is provided in the context.
    """
    ctx = context or {}

    py_code = (
        "import sys, json, runpy, pathlib\n"
        "script = sys.argv[1]\n"
        "try:\n"
        "    ctx = json.loads(sys.stdin.read() or '{}')\n"
        "except Exception:\n"
        "    ctx = {}\n"
        "# Ensure the script directory is first on sys.path so local imports work\n"
        "sys.path.insert(0, str(pathlib.Path(script).resolve().parent))\n"
        "globals_ = runpy.run_path(script)\n"
        "fn = globals_.get('run')\n"
        "if not callable(fn):\n"
        "    print(json.dumps({'error': 'agent has no run(context)'}))\n"
        "    sys.exit(2)\n"
        "res = fn(ctx)\n"
        "print(json.dumps(res, ensure_ascii=False))\n"
    )

    cmd = [sys.executable, "-c", py_code, str(entrypoint)]

    # Minimal, sanitized environment: keep PATH/HOME/LANG but avoid leaking
    # project-specific PYTHONPATH or other ambient variables.
    env = {}
    for k in ("PATH", "HOME", "LANG"):
        if k in os.environ:
            env[k] = os.environ[k]
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUNBUFFERED"] = "1"

    sanitized = _sanitize_context(ctx)
    run_folder = sanitized.get("run_folder")
    agent_hash = _compute_file_hash(entrypoint)

    # Run in an empty temporary directory so the agent starts with a clean cwd
    cwd = tempfile.mkdtemp()

    # Prepare resource limits preexec_fn if requested and supported
    preexec_fn = None
    if limits and resource is not None:
        def _apply_limits():
            try:
                if "cpu_seconds" in limits:
                    sec = int(limits.get("cpu_seconds") or 0)
                    if sec > 0:
                        resource.setrlimit(resource.RLIMIT_CPU, (sec, sec))
                if "memory_mb" in limits:
                    mb = int(limits.get("memory_mb") or 0)
                    if mb > 0:
                        resource.setrlimit(resource.RLIMIT_AS, (mb * 1024 * 1024, mb * 1024 * 1024))
            except Exception:
                return
        preexec_fn = _apply_limits

    start_ts = datetime.now(timezone.utc)
    try:
        proc = subprocess.run(
            cmd,
            input=json.dumps(sanitized, ensure_ascii=False),
            text=True,
            capture_output=True,
            env=env,
            cwd=cwd,
            timeout=timeout,
            preexec_fn=preexec_fn,
        )
    except subprocess.TimeoutExpired as e:  # pragma: no cover - best-effort
        end_ts = datetime.now(timezone.utc)
        audit = {
            "agent_id": agent_id,
            "entrypoint": str(entrypoint),
            "agent_hash": agent_hash,
            "started_at": start_ts.isoformat(),
            "finished_at": end_ts.isoformat(),
            "duration_seconds": (end_ts - start_ts).total_seconds(),
            "error": f"timeout after {timeout}s",
            "stdout": (e.stdout or "")[:10000],
            "stderr": (e.stderr or "")[:10000],
            "context": sanitized,
            "limits": limits,
        }
        _write_audit_log(sanitized, entrypoint.name, audit)
        return audit

    end_ts = datetime.now(timezone.utc)

    # Try to parse JSON result
    parsed = None
    if proc.stdout:
        try:
            parsed = json.loads(proc.stdout)
        except Exception:
            s = proc.stdout.strip()
            start = s.find("{")
            end = s.rfind("}") + 1
            if start != -1 and end != -1 and end > start:
                try:
                    parsed = json.loads(s[start:end])
                except Exception:
                    parsed = None

    audit = {
        "agent_id": agent_id,
        "entrypoint": str(entrypoint),
        "agent_hash": agent_hash,
        "started_at": start_ts.isoformat(),
        "finished_at": end_ts.isoformat(),
        "duration_seconds": (end_ts - start_ts).total_seconds(),
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "")[:10000],
        "stderr": (proc.stderr or "")[:10000],
        "parsed_result": parsed,
        "context": sanitized,
        "limits": limits,
    }

    # Persist audit log (best-effort)
    _write_audit_log(sanitized, entrypoint.name, audit)

    if proc.returncode != 0:
        if parsed is not None:
            return parsed
        return {"error": f"agent exit code {proc.returncode}", "stdout": proc.stdout, "stderr": proc.stderr}

    if parsed is not None:
        return parsed
    return {"error": "failed to parse agent output as JSON", "stdout": proc.stdout, "stderr": proc.stderr}


def _context_path_for_key(ctx: dict, key: str) -> Path | None:
    # Support keys like 'aidlc-docs' -> context['aidlc_docs']
    if key in ctx and ctx.get(key):
        return Path(ctx.get(key))
    alt = key.replace("-", "_")
    if alt in ctx and ctx.get(alt):
        return Path(ctx.get(alt))
    return None
def _resolve_permission_paths(cfg: dict, context: dict) -> tuple[list[Path], list[Path]]:
    """Resolve permission patterns from agent cfg into concrete host paths.

    Returns (read_paths, write_paths). Patterns referencing known context
    keys (e.g. 'workspace/**' or 'aidlc-docs/**') are resolved to the
    corresponding context path if present. Unresolvable patterns are
    ignored (no enforcement).
    """
    perms = cfg.get("permissions") or {}
    read = perms.get("read", []) or []
    write = perms.get("write", []) or []

    def _resolve_list(items: list) -> list[Path]:
        res: list[Path] = []
        for it in items:
            if not isinstance(it, str):
                continue
            if it.endswith("/**"):
                key = it[:-3]
                p = _context_path_for_key(context, key)
                if p:
                    res.append(p)
                else:
                    # Try direct path relative to repo
                    cand = REPO_ROOT / key
                    if cand.exists():
                        res.append(cand)
            else:
                # Try context key, absolute path, or repo-relative
                p = _context_path_for_key(context, it)
                if p:
                    res.append(p)
                else:
                    pp = Path(it)
                    if pp.is_absolute() and pp.exists():
                        res.append(pp)
                    else:
                        cand = REPO_ROOT / it
                        if cand.exists():
                            res.append(cand)
        # Deduplicate
        seen = set()
        out: list[Path] = []
        for p in res:
            rp = p.resolve()
            if rp not in seen:
                seen.add(rp)
                out.append(rp)
        return out

    return _resolve_list(read), _resolve_list(write)


def _is_path_allowed(path: Path, allowed_bases: list[Path]) -> bool:
    try:
        rp = path.resolve()
    except Exception:
        return False
    for base in allowed_bases:
        try:
            if rp == base.resolve() or rp.is_relative_to(base.resolve()):
                return True
        except Exception:
            # Fallback for older python versions
            try:
                if str(rp).startswith(str(base.resolve())):
                    return True
            except Exception:
                pass
    return False


def _validate_agent_output(agent_id: str, cfg: dict, output: object) -> dict | None:
    """Basic validation of agent output. Returns dict with 'error' if invalid."""
    if not isinstance(output, dict):
        return {"error": "output is not an object (expected JSON object)"}
    # Basic contract expectations
    if "agent_id" in output:
        try:
            if str(output.get("agent_id")) != str(agent_id):
                return {"error": "agent_id mismatch in output"}
        except Exception:
            return {"error": "invalid agent_id in output"}
    else:
        return {"error": "missing 'agent_id' in output"}

    if "status" not in output:
        return {"error": "missing 'status' in output"}

    return None


def _sensitive_key(name: str) -> bool:
    if not isinstance(name, str):
        return False
    ks = name.lower()
    for kw in ("secret", "token", "password", "aws", "access", "credentials", "key", "private"):
        if kw in ks:
            return True
    return False


def _sanitize_value(v, depth: int = 3):
    if depth <= 0:
        return None
    if v is None:
        return None
    if isinstance(v, (str, int, float, bool)):
        if isinstance(v, str) and len(v) > 2000:
            return v[:2000] + "..."
        return v
    if isinstance(v, dict):
        out = {}
        for k, val in v.items():
            if _sensitive_key(k):
                out[k] = "<<REDACTED>>"
            else:
                out[k] = _sanitize_value(val, depth - 1)
        return out
    if isinstance(v, (list, tuple)):
        lst = list(v)
        return [_sanitize_value(x, depth - 1) for x in lst[:100]]
    # Fallback to string representation
    try:
        s = str(v)
        if len(s) > 2000:
            return s[:2000] + "..."
        return s
    except Exception:
        return None


def _sanitize_context(ctx: dict | None) -> dict:
    ctx = ctx or {}
    res: dict = {}
    for k, v in ctx.items():
        if _sensitive_key(k):
            res[k] = "<<REDACTED>>"
            continue
        res[k] = _sanitize_value(v)
    return res


def _write_audit_log(sanitized_ctx: dict, entrypoint_name: str, audit: dict) -> None:
    """Write audit log JSON into run_folder/subagents-logs or repo-level folder."""
    try:
        run_folder = sanitized_ctx.get("run_folder") if isinstance(sanitized_ctx, dict) else None
        if run_folder:
            log_dir = Path(run_folder) / "subagents-logs"
        else:
            log_dir = REPO_ROOT / "subagents-logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        fname = f"{ts}-{entrypoint_name}.json"
        tmp = tempfile.NamedTemporaryFile(mode="w", delete=False, dir=str(log_dir), encoding="utf-8")
        try:
            json.dump(audit, tmp, ensure_ascii=False, indent=2)
            tmp.close()
            os.replace(tmp.name, str(log_dir / fname))
        finally:
            try:
                if os.path.exists(tmp.name):
                    os.remove(tmp.name)
            except Exception:
                pass
    except Exception:
        # Best-effort: do not raise from audit logging
        return


def _check_context_permissions(ctx: dict, perm_paths: tuple[list[Path], list[Path]]) -> bool:
    """Best-effort enforcement: ensure paths in `ctx` are within allowed bases.

    Raises PermissionError on violation.
    """
    read_bases, write_bases = perm_paths
    bases = list(read_bases or []) + list(write_bases or [])
    if not bases:
        # No declared permissions -> nothing to enforce
        return True

    # run_folder is the manager-controlled sandbox; always permit it and its children
    run_folder_val = ctx.get("run_folder")
    if run_folder_val:
        try:
            bases.append(Path(run_folder_val))
        except Exception:
            pass

    # Collect candidate paths from context values that look like paths
    candidates: list[Path] = []
    for k, v in ctx.items():
        if not isinstance(v, str):
            continue
        if v.startswith("/") or v.startswith(".") or "/" in v:
            try:
                candidates.append(Path(v))
            except Exception:
                continue

    for p in candidates:
        allowed = False
        for base in bases:
            try:
                if p.resolve() == base.resolve() or p.resolve().is_relative_to(base.resolve()):
                    allowed = True
                    break
            except Exception:
                try:
                    if str(p.resolve()).startswith(str(base.resolve())):
                        allowed = True
                        break
                except Exception:
                    pass
        if not allowed:
            raise PermissionError(f"context path not allowed by agent permissions: {p}")
    return True


def _docker_available() -> bool:
    return shutil.which("docker") is not None


def _run_agent_in_docker(entrypoint: Path, context: dict | None = None, read_paths: list[Path] | None = None, write_paths: list[Path] | None = None, timeout: int = 120) -> dict:
    """Run the agent inside a Docker container with restricted mounts.

    This is optional and only used when explicitly enabled via agent cfg or
    the env var `SUBAGENTS_USE_DOCKER`.
    """
    ctx = context or {}
    read_paths = read_paths or []
    write_paths = write_paths or []

    if not _docker_available():
        return {"error": "docker not available on host"}

    # Prepare python wrapper code (same as subprocess wrapper)
    py_code = (
        "import sys, json, runpy, pathlib\n"
        "script = sys.argv[1]\n"
        "try:\n"
        "    ctx = json.loads(sys.stdin.read() or '{}')\n"
        "except Exception:\n"
        "    ctx = {}\n"
        "sys.path.insert(0, str(pathlib.Path(script).resolve().parent))\n"
        "globals_ = runpy.run_path(script)\n"
        "fn = globals_.get('run')\n"
        "if not callable(fn):\n"
        "    print(json.dumps({'error': 'agent has no run(context)'}))\n"
        "    sys.exit(2)\n"
        "res = fn(ctx)\n"
        "print(json.dumps(res, ensure_ascii=False))\n"
    )

    # Build docker command
    cmd = ["docker", "run", "--rm", "-i", "-w", "/tmp"]

    mounts: list[tuple[str, str, str]] = []  # (host_path, container_path, mode)

    # Mount the entrypoint parent so the script is available at the same path
    ep_parent = str(entrypoint.resolve().parent)
    mounts.append((ep_parent, ep_parent, "ro"))

    for p in read_paths:
        mounts.append((str(p), str(p), "ro"))
    for p in write_paths:
        mounts.append((str(p), str(p), "rw"))

    # Deduplicate mounts preserving order
    seen_mounts = set()
    for host, cont, mode in mounts:
        if host not in seen_mounts:
            seen_mounts.add(host)
            cmd += ["-v", f"{host}:{cont}:{mode}"]

    # Minimal environment
    for k in ("PATH", "HOME", "LANG"):
        if k in os.environ:
            cmd += ["-e", f"{k}={os.environ[k]}"]
    cmd += ["-e", "PYTHONIOENCODING=utf-8"]

    # Use a small Python image
    image = os.environ.get("SUBAGENTS_DOCKER_IMAGE", "python:3.11-slim")
    cmd.append(image)

    # Pass the wrapper code and the absolute entrypoint path inside the container
    cmd += ["python", "-c", py_code, str(entrypoint.resolve())]

    try:
        proc = subprocess.run(
            cmd,
            input=json.dumps(ctx, ensure_ascii=False),
            text=True,
            capture_output=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        return {"error": f"docker timeout after {timeout}s", "stdout": e.stdout, "stderr": e.stderr}

    if proc.returncode != 0:
        try:
            return json.loads(proc.stdout)
        except Exception:
            return {"error": f"docker agent exit code {proc.returncode}", "stdout": proc.stdout, "stderr": proc.stderr}

    try:
        return json.loads(proc.stdout)
    except Exception:
        return {"error": "failed to parse agent output as JSON (docker)", "stdout": proc.stdout, "stderr": proc.stderr}


def run(agent_id: str, context: dict | None = None, conf_path: str | Path | None = None, timeout: int = 120) -> dict:
    """Run an agent by id, executing it in an isolated subprocess.

    This keeps the manager process protected from untrusted top-level code and
    ensures each agent starts with a clean environment and working directory.
    """
    cfg = find_agent(agent_id, conf_path)
    if not cfg:
        raise KeyError(f"Agent not found: {agent_id}")

    entrypoint = Path(cfg.get("entrypoint"))
    if not entrypoint.is_absolute():
        entrypoint = REPO_ROOT / entrypoint

    if not entrypoint.exists():
        raise FileNotFoundError(f"Agent entrypoint not found: {entrypoint}")

    ctx = context or {}

    # Enforce opt-in when agent requires it and a run_folder is available
    if cfg.get("opt_in"):
        run_folder = None
        if isinstance(ctx, dict):
            run_folder = ctx.get("run_folder") or ctx.get("workspace")
        if run_folder:
            state = _read_opt_in_state(run_folder)
            subagents_state = state.get("subagents", {}) if isinstance(state, dict) else {}
            if not subagents_state.get(agent_id):
                return {"error": "opt-in required", "opt_in": cfg.get("opt_in")}

    # Resolve permissions declared by the agent (best-effort)
    perm_paths = _resolve_permission_paths(cfg, ctx)

    # Decide whether to run in Docker: explicit agent cfg over environment
    use_docker = bool(cfg.get("use_docker")) if isinstance(cfg, dict) else False
    if not use_docker:
        env_flag = os.environ.get("SUBAGENTS_USE_DOCKER")
        if env_flag and env_flag.lower() in ("1", "true", "yes"):
            use_docker = True

    # If not using Docker, perform a static permission check (best-effort)
    if not use_docker:
        try:
            _check_context_permissions(ctx, perm_paths)
        except PermissionError as e:
            return {"error": f"permission check failed: {e}"}

    # Execute agent (docker or subprocess)
    # Determine timeouts/limits from agent cfg
    agent_timeout = cfg.get("timeout") or timeout
    limits = cfg.get("limits")

    # Transmit a minimal context to the child process so agents start with an
    # effectively empty context (reduces accidental data leakage). Only include
    # `autoskills` when the agent explicitly opts in via `allow_autoskills` in
    # its config. Keep `run_folder` and `aidlc_docs` minimally so audit logs and
    # output files can still be written into the run folder.
    tx_ctx: dict = {}
    if isinstance(ctx, dict):
        if ctx.get("run_folder"):
            tx_ctx["run_folder"] = ctx.get("run_folder")
        if ctx.get("aidlc_docs"):
            tx_ctx["aidlc_docs"] = ctx.get("aidlc_docs")
        # If agent allows AutoSkills, include a minimally-sanitized autoskills
        # mapping and attempt to resolve any relative `autoskills_dir` to an
        # absolute path using the run_folder or repository root.
        if cfg.get("allow_autoskills") and ctx.get("autoskills"):
            autos = dict(ctx.get("autoskills") or {})
            ad = autos.get("autoskills_dir")
            try:
                if ad:
                    p = Path(ad)
                    if not p.is_absolute():
                        # Prefer run_folder if available
                        rf = ctx.get("run_folder")
                        if rf:
                            cand = Path(rf) / ad
                            if cand.exists():
                                autos["autoskills_dir"] = str(cand.resolve())
                        # Fall back to repo root relative path
                        if autos.get("autoskills_dir") is None:
                            cand2 = REPO_ROOT / ad
                            if cand2.exists():
                                autos["autoskills_dir"] = str(cand2.resolve())
            except Exception:
                # Best-effort: leave as-is if resolution fails
                pass
            tx_ctx["autoskills"] = autos

    # --- Skill injection: load SKILL.md content for each skill in agent cfg ---
    # Skills are read from ~/.agents/skills/<name>/SKILL.md and injected as
    # context['skills'][name] = <markdown content>.  Agents can use these as
    # in-context instructions without requiring any external network call.
    skills_content = load_skills_for_agent(cfg)
    if skills_content:
        tx_ctx["skills"] = skills_content

    # --- MCP bridge: inject available tool list into context ---
    # Agents express intent by returning {"mcp_calls": [{"tool": ..., "args": ...}]}
    # in their output.  The manager handles approval and actual invocation below.
    bridge = build_mcp_bridge(cfg, run_folder=tx_ctx.get("run_folder"))
    if bridge is not None:
        tx_ctx["mcp"] = bridge.to_context_dict()

    # --- Developer memory injection (best-effort) ---
    # If a developer_id is present in the context, retrieve relevant memory
    # entries and inject them as tx_ctx["developer_memory"] so the agent starts
    # with cross-session knowledge about the developer's project context.
    #
    # Token-saving optimisations:
    # 1) Tag-scoped: each agent role only gets memory entries relevant to it.
    # 2) Pipeline-aware: if a previous stage already injected memory (marker
    #    key "_memory_injected" in ctx), skip re-injection for later stages.
    # 3) Compact format: recall_context now emits a single-line-per-entry
    #    format instead of markdown headers.
    ROLE_MEMORY_TAGS: dict[str, list[str]] = {
        "planner": ["plan", "arch", "dependencies", "manifests"],
        "builder": ["build", "commands", "dependencies", "manifests"],
        "reviewer": ["security", "linting", "code-review", "quality", "review"],
    }
    developer_id = ctx.get("developer_id") if isinstance(ctx, dict) else None
    if developer_id and not ctx.get("_memory_injected"):
        try:
            _mem_root = REPO_ROOT / ".aidlc-memory"
            if _mem_root.exists():
                from memory import MemoryStore as _MemStore
                _mstore = _MemStore(str(_mem_root))
                role_tags = ROLE_MEMORY_TAGS.get(cfg.get("role", ""))
                tx_ctx["developer_memory"] = _mstore.recall_context(
                    developer_id, tags=role_tags, limit=10
                )
                # Mark that memory has been injected so later pipeline stages
                # skip re-injection (saves ~1K tokens per skipped agent).
                if isinstance(ctx, dict):
                    ctx["_memory_injected"] = True
        except Exception:
            pass  # Best-effort: memory is optional

    if use_docker:
        # Run inside Docker container with mounts derived from permissions
        # If docker missing, return error
        if not _docker_available():
            return {"error": "docker requested but not available"}
        out = _run_agent_in_docker(entrypoint, tx_ctx, perm_paths.get("read", []), perm_paths.get("write", []), timeout=agent_timeout)
    else:
        out = _run_agent_subprocess(agent_id, entrypoint, context=tx_ctx, timeout=agent_timeout, limits=limits)

    # Validate output against minimal schema (or agent-provided schema).
    # Skip validation for manager-level errors (timeout, subprocess failure, etc.) —
    # these are not agent output and will not satisfy the agent_id/status contract.
    if isinstance(out, dict) and out.get("error"):
        return out
    validation = _validate_agent_output(agent_id, cfg, out if isinstance(out, dict) else {})
    if validation:
        return {"error": f"output validation failed: {validation.get('error')}", "raw_output": out}

    # --- MCP call approval loop ---
    # Agents may return {"mcp_calls": [{"tool": "...", "args": {...}}]} to
    # request MCP tool invocations.  Each call is presented to the human for
    # approval and the result is recorded back into `out["mcp_results"]`.
    # This keeps the actual MCP invocation in the host agentic tool (Copilot,
    # Cursor, etc.) while AIDLC orchestrates the intent + audit trail.
    if isinstance(out, dict) and out.get("mcp_calls") and bridge is not None:
        mcp_results: list[dict] = []
        for call_req in (out.get("mcp_calls") or []):
            tool_name = call_req.get("tool", "")
            tool_args = call_req.get("args") or {}
            try:
                call_desc = bridge.describe_call(tool_name, tool_args)
            except ValueError as e:
                mcp_results.append({"tool": tool_name, "status": "denied", "reason": str(e)})
                continue

            # Emit approval request to stdout for human operator / host tool.
            # The format matches what VS Code Copilot expects for tool-call approvals.
            approval_notice = {
                "event": "mcp_call_approval_required",
                "call_id": call_desc["call_id"],
                "tool": tool_name,
                "args": tool_args,
                "description": call_desc["description"],
                "agent_id": agent_id,
            }
            _write_audit_log(tx_ctx, "mcp_approval", approval_notice)
            # Record as pending (actual result injected by host; here we mark pending)
            result_record = bridge.record_result(call_desc["call_id"], result=None, approved=False)
            result_record["note"] = (
                "Host agentic tool must execute this call and inject result. "
                "See mcp_call_approval_required audit log."
            )
            mcp_results.append(result_record)

        out["mcp_results"] = mcp_results

    # If agent produced executable actions, delegate to the secure executor
    try:
        if isinstance(out, dict) and out.get("actions"):
            runner = REPO_ROOT / "scripts" / "executors" / "runner.py"
            if runner.exists():
                payload = {
                    "run_folder": tx_ctx.get("run_folder"),
                    "aidlc_docs": tx_ctx.get("aidlc_docs"),
                    "actions": out.get("actions"),
                }
                try:
                    proc = subprocess.run([
                        sys.executable,
                        str(runner),
                    ], input=json.dumps(payload, ensure_ascii=False), text=True, capture_output=True, timeout=cfg.get("executor_timeout") or 300)
                except subprocess.TimeoutExpired as e:
                    _write_audit_log(tx_ctx, "executor", {"agent_id": agent_id, "error": f"executor timeout after {e.timeout}s", "stdout": e.stdout, "stderr": e.stderr})
                    return {"error": "executor timeout", "raw_output": out}

                exec_res = None
                if proc.returncode != 0:
                    # Try to parse stdout even on non-zero
                    try:
                        exec_res = json.loads(proc.stdout or "{}")
                    except Exception:
                        exec_res = {"error": "executor failed", "stdout": proc.stdout, "stderr": proc.stderr}
                else:
                    try:
                        exec_res = json.loads(proc.stdout or "{}")
                    except Exception:
                        exec_res = {"error": "failed to parse executor output", "stdout": proc.stdout, "stderr": proc.stderr}

                # Audit the executor invocation
                _write_audit_log(tx_ctx, "executor", {"agent_id": agent_id, "actions": out.get("actions"), "executor_result": exec_res})

                # Attach executor results to agent output for caller inspection
                out["executor_results"] = exec_res
            else:
                # Executor missing: record audit and return error
                _write_audit_log(tx_ctx, "executor", {"agent_id": agent_id, "error": "executor not found", "expected_path": str(runner)})
                return {"error": "executor not available on host", "raw_output": out}
    except Exception as e:
        return {"error": f"executor invocation error: {e}", "raw_output": out}

    # --- Memory write-back (best-effort) ---
    # Agents may return memory_observations: [{content, tags, memory_type}]
    # The manager writes them to the developer's MemoryStore so knowledge
    # persists across sessions without agents needing to import MemoryStore.
    #
    # Token-saving: episodic entries get a 72h TTL so they auto-expire,
    # and after writes we trigger compaction to prune stale entries.
    if developer_id and isinstance(out, dict):
        observations = out.get("memory_observations") or []
        if observations:
            try:
                from memory import MemoryStore as _MemStore
                from memory.types import MemoryType as _MT
                _mem_root = REPO_ROOT / ".aidlc-memory"
                _mstore = _MemStore(str(_mem_root))
                _type_map = {
                    "episodic": _MT.EPISODIC,
                    "semantic": _MT.SEMANTIC,
                    "procedural": _MT.PROCEDURAL,
                }
                for obs in observations:
                    if not isinstance(obs, dict) or not obs.get("content"):
                        continue
                    mem_type = _type_map.get(obs.get("memory_type", ""), _MT.EPISODIC)
                    # Episodic observations (linter counts, TODO counts) go stale
                    # quickly; default them to 72h TTL unless explicitly overridden.
                    ttl = obs.get("ttl_hours")
                    if ttl is None and mem_type == _MT.EPISODIC:
                        ttl = 72.0
                    _mstore.remember(
                        developer_id,
                        obs["content"],
                        memory_type=mem_type,
                        tags=obs.get("tags") or [],
                        metadata={"agent_id": agent_id, "run_folder": tx_ctx.get("run_folder", "")},
                        session_id=tx_ctx.get("run_folder", ""),
                        ttl_hours=ttl,
                    )
                # Auto-compact: prune expired entries so recall stays lean
                try:
                    _mstore.compact(developer_id)
                except Exception:
                    pass
            except Exception:
                pass  # Best-effort: never fail the run for a memory write error

    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: manager.py <agent_id> [json_context]")
        sys.exit(2)
    agent = sys.argv[1]
    ctx = {}
    if len(sys.argv) > 2:
        try:
            import json

            ctx = json.loads(sys.argv[2])
        except Exception:
            ctx = {"raw": sys.argv[2]}
    out = run(agent, ctx)
    try:
        print(json.dumps(out, ensure_ascii=False))
    except Exception:
        # Fallback to repr if output cannot be serialized
        print(out)
