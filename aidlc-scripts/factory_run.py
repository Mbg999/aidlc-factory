#!/usr/bin/env python3
"""factory_run.py — Run Manager for AIDLC Orchestrator (Phase 6).

Owns the per-run manifest.yaml (state machine source of truth) and the
timeline.jsonl (append-only event log). Provides resume/replay/legacy-adopt
flows so a crashed orchestration run can be picked up at the last completed
stage.

Subcommands
-----------
    init <run-id> --user-request <text> [--project-slug <slug>] [--force]
        Initialize manifest.yaml and timeline.jsonl for a new run.

    set <run-id> [--field key=value]...
        Set arbitrary top-level manifest fields. JSON-decoded if possible.

    complete-stage <run-id> <stage> [--next-stage <next>]
        Mark a stage complete in manifest.completed_stages[]; update
        last_checkpoint_at; emit a `stage_complete` event. Idempotent.

    fail-stage <run-id> <stage> [--reason <text>]
        Mark a stage failed. Useful for crash recovery records.

    emit <run-id> --evt <name> [--stage <s>] [--field key=value]...
        Append a single event to timeline.jsonl. Used by the orchestrator
        to record arbitrary lifecycle events (spawn_start, spawn_end,
        cost_govern_skip, etc.).

    status <run-id> [--json]
        Print the current manifest.

    resume <run-id>
        Compute the next stage to spawn from manifest.completed_stages[].
        Print a JSON object with: completed_count, current_stage,
        next_stage_suggestion, partial_outputs (any stale handoff files).
        Emit a `resume_requested` event.

    replay <run-id> --from <stage>
        Roll the manifest back: truncate completed_stages[] before <stage>;
        archive output handoffs for rolled-back stages with a .replay-<ts>
        suffix; set current_stage = <stage>. Emit a `replay_requested` event.

    adopt-legacy [--repo-slug <slug>]
        Scan aidlc-docs/aidlc-state.md for `[x]` Stage Progress markers and
        synthesize a manifest with completed_stages adopted as-is. Run id is
        `legacy-<repo-slug>-<ts>`.

    tail <run-id> [--follow] [--json]
        Print timeline events. With --follow, polls every 0.5s like `tail -f`.

Atomicity
---------
manifest.yaml writes use write-tmp-then-rename for atomic updates.
timeline.jsonl is append-only with a single line written per call (atomic
for line-sized writes on POSIX local filesystems).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("missing dependency: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(os.environ.get("AIDLC_ROOT", Path(__file__).resolve().parents[1]))
RUNS_ROOT = REPO_ROOT / ".aidlc-orchestrator" / "runs"
AIDLC_DOCS = REPO_ROOT / "aidlc-docs"
SCRIPTS_VERSION = REPO_ROOT / "aidlc-scripts" / "VERSION"

PHASE_ORDER = [
    "workspace-scout",
    "reverse-engineer",
    "requirements-analyst",
    "story-writer",
    "workflow-planner",
    "unit-decomposer",
    "code-generator",
    "build-test-agent",
    "reviewer-code",
    "reviewer-security",
    "reviewer-performance",
    "reviewer-simplifier",
    "ship-agent",
]


_RUN_ID_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


def validate_run_id(run_id: str) -> None:
    if not _RUN_ID_RE.match(run_id):
        _die(f"invalid run_id: {run_id!r}")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def run_dir(run_id: str, must_exist: bool = True) -> Path:
    validate_run_id(run_id)
    p = RUNS_ROOT / run_id
    if must_exist and not p.exists():
        _die(f"run not found: {p}")
    return p


def manifest_path(run_id: str) -> Path:
    validate_run_id(run_id)
    return RUNS_ROOT / run_id / "manifest.yaml"


def timeline_path(run_id: str) -> Path:
    validate_run_id(run_id)
    return RUNS_ROOT / run_id / "timeline.jsonl"


def load_manifest(run_id: str) -> dict:
    p = manifest_path(run_id)
    if not p.exists():
        _die(f"manifest not found: {p}")
    return yaml.safe_load(p.read_text())


def save_manifest_atomic(run_id: str, data: dict) -> None:
    p = manifest_path(run_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.safe_dump(data, default_flow_style=False, sort_keys=False))
    tmp.replace(p)


def append_event(run_id: str, event: dict) -> None:
    p = timeline_path(run_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as f:
        f.write(json.dumps(event) + "\n")


def _parse_field(kv: str):
    k, _, v = kv.partition("=")
    if not k:
        _die(f"invalid --field: {kv}")
    try:
        return k, json.loads(v)
    except json.JSONDecodeError:
        return k, v


def _set_dotted(obj: dict, dotted_key: str, value) -> None:
    """Set obj[a][b][c] = value given dotted_key 'a.b.c'.

    Intermediate keys missing or non-dict are replaced with empty dicts.
    Single-key (no dot) sets obj[key] = value as before.
    """
    parts = dotted_key.split(".")
    cur = obj
    for p in parts[:-1]:
        if not isinstance(cur.get(p), dict):
            cur[p] = {}
        cur = cur[p]
    cur[parts[-1]] = value


def cmd_init(args: argparse.Namespace) -> None:
    rd = run_dir(args.run_id, must_exist=False)
    rd.mkdir(parents=True, exist_ok=True)
    (rd / "handoffs").mkdir(exist_ok=True)
    if manifest_path(args.run_id).exists() and not args.force:
        _die(f"manifest already exists at {manifest_path(args.run_id)}; use --force")

    orch_version = "unknown"
    if SCRIPTS_VERSION.exists():
        orch_version = SCRIPTS_VERSION.read_text().strip()
    manifest = {
        "run_id": args.run_id,
        "started_at": now_iso(),
        "last_checkpoint_at": now_iso(),
        "user_request": args.user_request,
        "project_slug": args.project_slug or REPO_ROOT.name.lower().replace(" ", "-"),
        "current_stage": "workspace-scout",
        "completed_stages": [],
        "skipped_stages": [],
        "failed_stages": [],
        "orchestrator_version": orch_version,
        "project_profile": {"ui": False, "api": False, "has_legacy": False},
        "units": [],
        "skill_paths": {},
    }
    save_manifest_atomic(args.run_id, manifest)
    append_event(args.run_id, {
        "ts": now_iso(),
        "evt": "run_init",
        "run_id": args.run_id,
        "user_request": args.user_request,
    })
    print(f"initialized run {args.run_id} at {rd}")


def cmd_set(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.run_id)
    for kv in args.field or []:
        k, v = _parse_field(kv)
        _set_dotted(manifest, k, v)
    manifest["last_checkpoint_at"] = now_iso()
    save_manifest_atomic(args.run_id, manifest)
    print(f"updated {len(args.field or [])} field(s)")


def _reconcile_state(run_id: str) -> dict:
    """Check for drift between manifest, timeline, and budget.

    Returns a dict with drift info:
      completed_not_in_timeline: stages in manifest but no timeline event
      budget_calls_not_in_timeline: budget deducts with no matching event
      last_action: last known action from manifest
    """
    drift: dict = {"drift": False, "details": []}
    manifest_p = manifest_path(run_id)
    if not manifest_p.exists():
        return drift
    manifest = yaml.safe_load(manifest_p.read_text()) or {}

    timeline_p = timeline_path(run_id)
    timeline_stages: set[str] = set()
    if timeline_p.exists():
        for line in timeline_p.read_text().splitlines():
            try:
                e = json.loads(line)
                if e.get("evt") == "stage_complete" and e.get("stage"):
                    timeline_stages.add(e["stage"])
            except json.JSONDecodeError:
                continue

    completed = set(manifest.get("completed_stages", []))
    missing = completed - timeline_stages
    if missing:
        drift["drift"] = True
        drift["details"].append({
            "kind": "completed_not_in_timeline",
            "stages": sorted(missing),
        })

    budget_p = run_budget_path(run_id) if False else None
    if budget_p and budget_p.exists():
        try:
            budget = yaml.safe_load(budget_p.read_text()) or {}
            events = budget.get("events", [])
            for evt in events:
                if evt.get("action") == "deduct":
                    stage = evt.get("stage")
                    if stage and stage not in timeline_stages and stage not in completed:
                        drift["drift"] = True
                        drift["details"].append({
                            "kind": "budget_deduct_no_complete",
                            "stage": stage,
                            "ts": evt.get("ts"),
                        })
        except (ValueError, TypeError):
            pass

    last_action = manifest.get("last_action_reason")
    if last_action:
        drift["last_action"] = last_action

    return drift


def cmd_complete_stage(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.run_id)
    if args.stage in manifest["completed_stages"]:
        print(f"stage {args.stage} already complete (idempotent)")
        return
    manifest["completed_stages"].append(args.stage)
    manifest["last_checkpoint_at"] = now_iso()
    if args.reason:
        manifest["last_action_reason"] = args.reason
    if args.next_stage:
        manifest["current_stage"] = args.next_stage
    save_manifest_atomic(args.run_id, manifest)
    append_event(args.run_id, {
        "ts": now_iso(),
        "evt": "stage_complete",
        "run_id": args.run_id,
        "stage": args.stage,
        "next_stage": args.next_stage,
        "reason": args.reason,
    })
    print(f"marked {args.stage} complete")


def cmd_fail_stage(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.run_id)
    failures = manifest.setdefault("failed_stages", [])
    failures.append({"stage": args.stage, "reason": args.reason or "unspecified", "at": now_iso()})
    manifest["last_checkpoint_at"] = now_iso()
    save_manifest_atomic(args.run_id, manifest)
    append_event(args.run_id, {
        "ts": now_iso(),
        "evt": "stage_failed",
        "run_id": args.run_id,
        "stage": args.stage,
        "reason": args.reason,
    })
    print(f"marked {args.stage} failed: {args.reason or 'unspecified'}")


def cmd_emit(args: argparse.Namespace) -> None:
    fields = {}
    for kv in args.field or []:
        k, v = _parse_field(kv)
        fields[k] = v
    event = {"ts": now_iso(), "evt": args.evt, "run_id": args.run_id, **fields}
    if args.stage:
        event["stage"] = args.stage
    append_event(args.run_id, event)
    print(json.dumps(event))


def _print_latency(run_id: str, manifest: dict) -> None:
    timeline_p = timeline_path(run_id)
    if not timeline_p.exists():
        print("no timeline available")
        return
    events: list[dict] = []
    for line in timeline_p.read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    ne, sp, sd = None, None, None
    for e in events:
        if e.get("evt") == "needs_human":
            ne = e.get("ts")
        elif e.get("evt") == "spawn_end":
            sp = e.get("ts")
        elif e.get("evt") == "user_decision":
            sd = e.get("ts")

    lines = [f"Approval Gate Latency: {run_id}", "─" * 60]
    if ne and sd:
        try:
            from datetime import datetime as dt
            dur = (dt.fromisoformat(sd) - dt.fromisoformat(ne)).total_seconds() / 60.0
            lines.append(f"  needs_human → user_decision:  {dur:.1f}m")
        except (ValueError, TypeError):
            lines.append("  needs_human → user_decision:  parse error")
    elif ne:
        lines.append("  needs_human → user_decision:  pending (no decision yet)")
    if sp and sd:
        try:
            from datetime import datetime as dt
            total = (dt.fromisoformat(sd) - dt.fromisoformat(sp)).total_seconds() / 60.0
            lines.append(f"  spawn_end → user_decision:   {total:.1f}m")
        except (ValueError, TypeError):
            lines.append("  spawn_end → user_decision:    parse error")

    # Per-stage latency from timeline
    stage_events: dict[str, dict] = {}
    for e in events:
        stage = e.get("stage")
        if not stage:
            continue
        if stage not in stage_events:
            stage_events[stage] = {}
        if e["evt"] in ("spawn_start", "stage_start"):
            stage_events[stage]["start"] = e["ts"]
        elif e["evt"] in ("spawn_end", "stage_complete"):
            stage_events[stage]["end"] = e["ts"]
        elif e["evt"] in ("needs_human",):
            stage_events[stage]["needs_human"] = e["ts"]
        elif e["evt"] in ("user_decision",):
            stage_events[stage]["decision"] = e["ts"]

    for stage, ts in sorted(stage_events.items()):
        if ts.get("start") and ts.get("end"):
            try:
                from datetime import datetime as dt
                dur = (dt.fromisoformat(ts["end"]) - dt.fromisoformat(ts["start"])).total_seconds() / 60.0
                lines.append(f"  {stage:30s}  {dur:.1f}m")
            except (ValueError, TypeError):
                pass
        if ts.get("needs_human") and ts.get("decision"):
            try:
                from datetime import datetime as dt
                gate = (dt.fromisoformat(ts["decision"]) - dt.fromisoformat(ts["needs_human"])).total_seconds() / 60.0
                lines.append(f"  {stage:30s}  └─ approval gate: {gate:.1f}m")
            except (ValueError, TypeError):
                pass

    lines.append("─" * 60)
    print("\n".join(lines))


def cmd_status(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.run_id)
    if args.latency:
        _print_latency(args.run_id, manifest)
        return
    if args.json:
        print(json.dumps(manifest, indent=2))
    else:
        print(yaml.safe_dump(manifest, default_flow_style=False, sort_keys=False), end="")


def _next_stage(manifest: dict) -> str | None:
    """Compute the next stage to spawn.

    Trust the manifest's current_stage field (set by the orchestrator via
    complete-stage --next-stage), since only the orchestrator knows the
    conditional flow (e.g. whether to skip reverse-engineer in greenfield).
    Fall back to PHASE_ORDER scan only if current_stage is missing or already
    completed. Stages in `skipped_stages[]` are passed over during the scan.
    """
    completed = set(manifest.get("completed_stages", []))
    skipped = set(manifest.get("skipped_stages", []))
    current = manifest.get("current_stage")
    if current and current not in completed and current not in skipped:
        if current in PHASE_ORDER:
            return current
    # Compute start index: after current_stage if in PHASE_ORDER,
    # otherwise after the last completed stage (handles synthetic markers)
    if current and current in PHASE_ORDER:
        start_idx = PHASE_ORDER.index(current) + 1
    else:
        last_idx = max(
            (PHASE_ORDER.index(s) for s in manifest.get("completed_stages", [])
             if s in PHASE_ORDER),
            default=-1
        )
        start_idx = last_idx + 1
    for stage in PHASE_ORDER[start_idx:]:
        if stage not in completed and stage not in skipped:
            return stage
    return None


def cmd_resume(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.run_id)
    completed = manifest["completed_stages"]
    nxt = _next_stage(manifest)

    result: dict = {
        "run_id": args.run_id,
        "completed_count": len(completed),
        "completed_stages": completed,
        "current_stage": manifest.get("current_stage"),
        "next_stage_suggestion": nxt,
        "last_checkpoint_at": manifest.get("last_checkpoint_at"),
    }

    handoffs = run_dir(args.run_id) / "handoffs"
    if handoffs.exists() and nxt:
        partial = sorted(handoffs.glob(f"{nxt}*.output.yaml"))
        if partial:
            result["partial_outputs"] = [str(p.relative_to(REPO_ROOT)) for p in partial]

    # Reconcile state drift
    result["reconcile"] = _reconcile_state(args.run_id)

    # Version compatibility check
    if SCRIPTS_VERSION.exists():
        current_ver = SCRIPTS_VERSION.read_text().strip()
        manifest_ver = manifest.get("orchestrator_version", "0.0.0")
        if manifest_ver != current_ver:
            result["version_warning"] = (
                f"manifest built with orchestrator v{manifest_ver}, "
                f"current scripts are v{current_ver}"
            )

    print(json.dumps(result, indent=2))
    append_event(args.run_id, {
        "ts": now_iso(),
        "evt": "resume_requested",
        "run_id": args.run_id,
        "next_stage": nxt,
    })


def cmd_replay(args: argparse.Namespace) -> None:
    manifest = load_manifest(args.run_id)
    target = args.from_stage
    if target not in manifest["completed_stages"]:
        _die(f"cannot replay from {target}: not in completed_stages {manifest['completed_stages']}")

    idx = manifest["completed_stages"].index(target)
    rolled_back = manifest["completed_stages"][idx:]
    manifest["completed_stages"] = manifest["completed_stages"][:idx]
    manifest["current_stage"] = target
    manifest["last_checkpoint_at"] = now_iso()

    archived: list[str] = []
    handoffs = run_dir(args.run_id) / "handoffs"
    if handoffs.exists():
        ts = int(time.time())
        for stage in rolled_back:
            for f in handoffs.glob(f"{stage}*.output.yaml"):
                archived_path = f.with_name(f"{f.stem}.replay-{ts}.yaml")
                f.rename(archived_path)
                archived.append(str(archived_path.relative_to(REPO_ROOT)))

    save_manifest_atomic(args.run_id, manifest)
    append_event(args.run_id, {
        "ts": now_iso(),
        "evt": "replay_requested",
        "run_id": args.run_id,
        "from_stage": target,
        "rolled_back": rolled_back,
        "archived": archived,
    })
    print(json.dumps({
        "replayed_from": target,
        "rolled_back": rolled_back,
        "archived_outputs": archived,
    }, indent=2))


_LEGACY_STATE_RE = re.compile(r"^\s*-?\s*\[x\]\s*(.+)$", re.IGNORECASE)
_LEGACY_SKIPPED_RE = re.compile(r"^\s*-?\s*\[-\]\s*(.+)$", re.IGNORECASE)
_LEGACY_CURRENT_RE = re.compile(r"^\s*##\s*Current\s+Stage\s*$", re.IGNORECASE)

# Conditional stages — present in PHASE_ORDER but skipped by legacy AIDLC
# unless the run actually executed them. If adopt-legacy can't prove these
# ran (no [x] marker), and the legacy current_stage is past them, mark as
# skipped so resume doesn't suggest re-doing them.
_CONDITIONAL_STAGES = {"reverse-engineer", "story-writer", "unit-decomposer"}
_REVIEW_STAGES = {"reviewer-security", "reviewer-performance", "reviewer-simplifier"}

# Legacy AIDLC uses stage names like "Workspace Detection"; orchestrator uses
# "workspace-scout". Map legacy phrases (lowercased, normalized) to current stage_id.
LEGACY_TO_PHASE: dict[str, str] = {
    "workspace detection": "workspace-scout",
    "workspace-detection": "workspace-scout",
    "reverse engineering": "reverse-engineer",
    "reverse-engineering": "reverse-engineer",
    "requirements analysis": "requirements-analyst",
    "requirements-analysis": "requirements-analyst",
    "user stories": "story-writer",
    "user-stories": "story-writer",
    "workflow planning": "workflow-planner",
    "workflow-planning": "workflow-planner",
    "units generation": "unit-decomposer",
    "units-generation": "unit-decomposer",
    "code generation": "code-generator",
    "code-generation": "code-generator",
    "build and test": "build-test-agent",
    "build & test": "build-test-agent",
    "build-and-test": "build-test-agent",
    "review": "reviewer-code",  # ambiguous; treat as "review pass complete"
    "ship": "ship-agent",
}


def _legacy_current_stage(state_text: str) -> str | None:
    """Parse the `## Current Stage` section and return the mapped stage_id.

    The legacy aidlc-state.md format puts the current stage on the line(s)
    after `## Current Stage`. Phrases may include phase prefixes like
    "INCEPTION - Workflow Planning" — strip them before matching.
    Returns None if no current stage is found or it can't be mapped.
    """
    lines = state_text.splitlines()
    for i, line in enumerate(lines):
        if not _LEGACY_CURRENT_RE.match(line):
            continue
        # Read forward until the next non-blank, non-header line.
        for body in lines[i + 1:]:
            stripped = body.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                break
            # Strip "INCEPTION - " / "CONSTRUCTION - " / "OPERATIONS - " prefixes
            phrase = stripped
            for prefix in ("INCEPTION - ", "CONSTRUCTION - ", "OPERATIONS - "):
                if phrase.upper().startswith(prefix):
                    phrase = phrase[len(prefix):]
                    break
            normalized = phrase.lower().strip()
            for sep in (" — ", " - ", " (", "—"):
                if sep in normalized:
                    normalized = normalized.split(sep, 1)[0].strip()
            if normalized in LEGACY_TO_PHASE:
                return LEGACY_TO_PHASE[normalized]
            # Substring fallback against PHASE_ORDER
            normalized_dash = normalized.replace(" ", "-")
            for stage in PHASE_ORDER:
                if stage == normalized_dash or stage in normalized_dash:
                    return stage
            return None
    return None


def _stages_from_legacy(state_text: str) -> list[str]:
    completed: list[str] = []
    # Only scan "### Current Iteration" section (Bug 8 fix)
    scan_text = state_text
    for heading in ("### Current Iteration", "## Stage Progress"):
        if heading in scan_text:
            parts = scan_text.split(heading, 1)
            if len(parts) > 1 and parts[1].strip():
                scan_text = parts[1]
                break

    for line in scan_text.splitlines():
        line_stripped = line.strip()
        # Skip lines that start with ## (sub-headers within section)
        if line_stripped.startswith("##"):
            continue

        m = _LEGACY_STATE_RE.match(line)
        if not m:
            continue
        # Strip trailing "— date" etc. before matching
        raw = m.group(1).strip().lower()
        # Normalize: drop everything after "—" or " - " or " (" (timestamps, parens)
        for sep in (" — ", " - ", " (", "—"):
            if sep in raw:
                raw = raw.split(sep, 1)[0].strip()
        # Try alias map first (handles spaces and hyphens)
        if raw in LEGACY_TO_PHASE:
            stage = LEGACY_TO_PHASE[raw]
            if stage not in completed:
                completed.append(stage)
            continue
        # Fall back: substring match against current PHASE_ORDER ids
        normalized = raw.replace(" ", "-")
        for stage in PHASE_ORDER:
            if stage == normalized or stage in normalized:
                if stage not in completed:
                    completed.append(stage)
                break
    return completed


def cmd_adopt_legacy(args: argparse.Namespace) -> None:
    if not AIDLC_DOCS.exists():
        _die(f"no aidlc-docs/ directory at {AIDLC_DOCS}")
    state_file = AIDLC_DOCS / "aidlc-state.md"
    if not state_file.exists():
        _die(f"no aidlc-state.md found at {state_file}")

    state_text = state_file.read_text()
    completed = _stages_from_legacy(state_text)
    legacy_current = _legacy_current_stage(state_text)

    # Detect [-] skipped markers from current iteration (Bug 8 fix)
    for heading in ("### Current Iteration", "## Stage Progress"):
        if heading in state_text:
            parts = state_text.split(heading, 1)
            if len(parts) > 1:
                for line in parts[1].splitlines():
                    if line.strip().startswith("##"):
                        break
                    m = _LEGACY_SKIPPED_RE.match(line)
                    if not m:
                        continue
                    raw = m.group(1).strip().lower()
                    for sep in (" — ", " - ", " (", "—"):
                        if sep in raw:
                            raw = raw.split(sep, 1)[0].strip()
                    if raw in LEGACY_TO_PHASE:
                        stage = LEGACY_TO_PHASE[raw]
                        completed = [s for s in completed if s != stage]
                break

    # Legacy Review → all 4 reviewers (Bug 3 fix)
    if "reviewer-code" in completed:
        for r in _REVIEW_STAGES:
            if r not in completed:
                completed.append(r)

    # Decide manifest.current_stage and skipped_stages[]:
    #   - If legacy_current is parseable AND ahead of last completed in
    #     PHASE_ORDER, honor it (the user was clearly heading there next).
    #     Mark conditional stages between last-completed and legacy_current
    #     as skipped — legacy AIDLC doesn't run them unless explicitly chosen.
    #   - Otherwise fall back to "current = last completed".
    skipped: list[str] = []
    current_stage = completed[-1] if completed else "workspace-scout"
    if legacy_current and legacy_current in PHASE_ORDER:
        last_completed_idx = (
            PHASE_ORDER.index(completed[-1]) if completed else -1
        )
        legacy_idx = PHASE_ORDER.index(legacy_current)
        if legacy_idx > last_completed_idx:
            current_stage = legacy_current
            for stage in PHASE_ORDER[last_completed_idx + 1:legacy_idx]:
                if stage in _CONDITIONAL_STAGES:
                    skipped.append(stage)

    repo_slug = args.repo_slug or REPO_ROOT.name.lower().replace(" ", "-")
    ts = now_iso().replace(":", "").replace("-", "").replace("+0000", "")
    run_id = f"legacy-{repo_slug}-{ts}"
    rd = run_dir(run_id, must_exist=False)
    rd.mkdir(parents=True, exist_ok=True)
    (rd / "handoffs").mkdir(exist_ok=True)

    manifest = {
        "run_id": run_id,
        "started_at": now_iso(),
        "last_checkpoint_at": now_iso(),
        "user_request": "(adopted from legacy aidlc-docs/)",
        "project_slug": repo_slug,
        "current_stage": current_stage,
        "completed_stages": completed,
        "skipped_stages": skipped,
        "failed_stages": [],
        "adoption_status": "complete (adopted)",
        "adoption_source": str(state_file.relative_to(REPO_ROOT)),
        "project_profile": {"ui": False, "api": False, "has_legacy": True},
        "units": [],
        "skill_paths": {},
    }
    save_manifest_atomic(run_id, manifest)
    append_event(run_id, {
        "ts": now_iso(),
        "evt": "legacy_adopted",
        "run_id": run_id,
        "from": str(state_file.relative_to(REPO_ROOT)),
        "stages_adopted": completed,
        "stages_skipped": skipped,
        "current_stage": current_stage,
    })
    print(json.dumps({
        "run_id": run_id,
        "adopted_stages": completed,
        "skipped_stages": skipped,
        "current_stage": current_stage,
        "completed_count": len(completed),
        "manifest_path": str(manifest_path(run_id).relative_to(REPO_ROOT)),
    }, indent=2))


def _print_event(line: str, as_json: bool) -> None:
    if not line:
        return
    if as_json:
        print(line)
        return
    try:
        e = json.loads(line)
        ts = e.get("ts", "")
        evt = e.get("evt", "?")
        stage = e.get("stage", "")
        reserved = {"ts", "evt", "stage", "run_id"}
        details = ", ".join(f"{k}={v}" for k, v in e.items() if k not in reserved)
        print(f"{ts}  {evt:20s} {stage:30s} {details}")
    except json.JSONDecodeError:
        print(f"!malformed: {line}")


def cmd_graph(args: argparse.Namespace) -> None:
    """Print a visual timeline bar chart of a completed run."""
    manifest = load_manifest(args.run_id)
    timeline_p = timeline_path(args.run_id)
    if not timeline_p.exists():
        _die(f"no timeline at {timeline_p}")

    # Parse events
    events: list[dict] = []
    for line in timeline_p.read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    # Build per-stage stats
    stage_stats: dict[str, dict] = {}
    stage_order: list[str] = []
    for evt in events:
        stage = evt.get("stage") or evt.get("evt", "")
        if stage not in stage_stats:
            stage_stats[stage] = {"start": None, "end": None, "evt": evt.get("evt")}
            stage_order.append(stage)
        if evt["evt"] in ("spawn_start", "run_init", "stage_start"):
            stage_stats[stage]["start"] = evt["ts"]
        elif evt["evt"] in ("stage_complete", "spawn_end"):
            stage_stats[stage]["end"] = evt["ts"]
            stage_stats[stage]["status"] = "done"
        elif evt["evt"] == "stage_failed":
            stage_stats[stage]["status"] = "failed"
        elif evt["evt"] == "cost_govern_skip":
            stage_stats[stage]["status"] = "skipped"

    completed = set(manifest.get("completed_stages", []))
    skipped = set(manifest.get("skipped_stages", []))
    failed = set(s.get("stage") for s in manifest.get("failed_stages", []))

    budget_p = RUNS_ROOT / args.run_id / "budget.yaml"
    token_max = 5_000_000
    wall_max = 240
    token_used = 0
    wall_used = 0.0
    if budget_p and budget_p.exists():
        try:
            budget_data = yaml.safe_load(budget_p.read_text()) or {}
            token_used = int(budget_data.get("used", {}).get("tokens", 0))
            wall_used = float(budget_data.get("used", {}).get("wall_clock_min", 0.0))
            token_max = int(budget_data.get("budget", {}).get("tokens_max", token_max))
            wall_max = float(budget_data.get("budget", {}).get("wall_clock_max_min", wall_max))
        except (ValueError, TypeError):
            pass

    # Only show PHASE_ORDER stages
    bar_width = 12
    lines = [f"", f"Timeline: {manifest.get('run_id', args.run_id)}", "─" * 60]
    for stage in PHASE_ORDER:
        stats = stage_stats.get(stage, {})
        status = "  "
        prefix = "  "
        if stage in completed:
            status = "✅"
        elif stage in failed:
            status = "❌"
        elif stage in skipped:
            status = "⚠️"
        elif manifest.get("current_stage") == stage:
            status = "▶️ "

        duration_str = ""
        if stats.get("start") and stats.get("end"):
            try:
                from datetime import datetime as dt
                s = dt.fromisoformat(stats["start"])
                e = dt.fromisoformat(stats["end"])
                dur = (e - s).total_seconds() / 60.0
                duration_str = f"{dur:.1f}m"
                fill = min(int(dur / 5), bar_width)
                bar = "█" * fill + "░" * (bar_width - fill)
            except (ValueError, TypeError):
                bar = "░" * bar_width
        else:
            bar = "░" * bar_width

        lines.append(f"  {stage:30s} {bar} {duration_str:8s} {status}")

    token_pct = round((token_used / token_max) * 100, 1) if token_max > 0 else 0
    wall_pct = round((wall_used / wall_max) * 100, 1) if wall_max > 0 else 0
    lines.append("─" * 60)
    lines.append(
        f"Budget: {token_used:,} / {token_max:,} tokens ({token_pct}%)  "
        f"{wall_used} / {wall_max} min ({wall_pct}%)"
    )
    lines.append("")
    print("\n".join(lines))


def cmd_tail(args: argparse.Namespace) -> None:
    p = timeline_path(args.run_id)
    if not p.exists():
        _die(f"no timeline at {p}")

    if not args.follow:
        for line in p.read_text().splitlines():
            _print_event(line, args.json)
        return

    with p.open() as f:
        for line in f:
            _print_event(line.rstrip("\n"), args.json)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.5)
                continue
            _print_event(line.rstrip("\n"), args.json)


def main() -> None:
    p = argparse.ArgumentParser(description="AIDLC Orchestrator Run Manager")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("run_id")
    p_init.add_argument("--user-request", required=True)
    p_init.add_argument("--project-slug")
    p_init.add_argument("--force", action="store_true")
    p_init.set_defaults(func=cmd_init)

    p_set = sub.add_parser("set")
    p_set.add_argument("run_id")
    p_set.add_argument("--field", action="append")
    p_set.set_defaults(func=cmd_set)

    p_cs = sub.add_parser("complete-stage")
    p_cs.add_argument("run_id")
    p_cs.add_argument("stage")
    p_cs.add_argument("--next-stage")
    p_cs.add_argument("--reason", help="reason for completion (crash resilience marker)")
    p_cs.set_defaults(func=cmd_complete_stage)

    p_fs = sub.add_parser("fail-stage")
    p_fs.add_argument("run_id")
    p_fs.add_argument("stage")
    p_fs.add_argument("--reason")
    p_fs.set_defaults(func=cmd_fail_stage)

    p_emit = sub.add_parser("emit")
    p_emit.add_argument("run_id")
    p_emit.add_argument("--evt", required=True)
    p_emit.add_argument("--stage")
    p_emit.add_argument("--field", action="append")
    p_emit.set_defaults(func=cmd_emit)

    p_status = sub.add_parser("status")
    p_status.add_argument("run_id")
    p_status.add_argument("--json", action="store_true")
    p_status.add_argument("--latency", action="store_true",
                          help="print approval gate latency breakdown")
    p_status.set_defaults(func=cmd_status)

    p_resume = sub.add_parser("resume")
    p_resume.add_argument("run_id")
    p_resume.set_defaults(func=cmd_resume)

    p_replay = sub.add_parser("replay")
    p_replay.add_argument("run_id")
    p_replay.add_argument("--from", dest="from_stage", required=True)
    p_replay.set_defaults(func=cmd_replay)

    p_adopt = sub.add_parser("adopt-legacy")
    p_adopt.add_argument("--repo-slug")
    p_adopt.set_defaults(func=cmd_adopt_legacy)

    p_graph = sub.add_parser("graph", help="visual timeline of a run")
    p_graph.add_argument("run_id")
    p_graph.set_defaults(func=cmd_graph)

    p_tail = sub.add_parser("tail")
    p_tail.add_argument("run_id")
    p_tail.add_argument("--follow", "-f", action="store_true")
    p_tail.add_argument("--json", action="store_true")
    p_tail.set_defaults(func=cmd_tail)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
