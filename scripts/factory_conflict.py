#!/usr/bin/env python3
"""factory_conflict.py — Conflict Resolver for AIDLC Orchestrator (Phase 5).

Detects and arbitrates conflicts between parallel stage agents:
    - File-glob lock registry (path-based collision detection)
    - Python AST symbol diff (interface drift detection)

Subcommands
-----------
    acquire <run-id> <holder> [--mode write|read] <glob>...
        Try to acquire write or read locks on the given globs.
        Exit codes:
            0  all granted
            1  conflict; conflict record written under runs/<run>/conflicts/

    release <run-id> <holder>
        Release ALL locks held by <holder>. Idempotent.

    list <run-id> [--json]
        Print active locks (sorted by holder).

    snapshot <run-id> <holder> <file>...
        Pre-spawn: capture baseline AST symbol map for each .py file.
        Used as the diff baseline by `check-symbols` post-spawn.

    check-symbols <run-id> <holder> <file>...
        Post-spawn: parse each .py file, diff exported symbols against the
        baseline written by `snapshot`. If drift is detected AND there are
        other active holders, write an `interface_drift` conflict record
        and exit 1. If drift but no other holders, exit 0 with a notice.

    conflicts <run-id> [--json]
        List open conflict records for the run.

Storage
-------
    .aidlc-orchestrator/runs/<run-id>/locks/<holder>.yaml
    .aidlc-orchestrator/runs/<run-id>/symbol-baseline/<holder>.yaml
    .aidlc-orchestrator/runs/<run-id>/conflicts/<id>.yaml

Phase 5 limitations
-------------------
- Auto-merge resolution is NOT implemented. Conflicts always escalate
  (human resolution). The plan §6.2 documents auto-merge as a future feature.
- Glob overlap is heuristic: position-by-position component match with **
  wildcards. False positives (over-detecting overlap) are safe; false
  negatives would be unsafe (missed conflict). The heuristic biases toward
  false positives.
- AST diff covers Python only. TS/JS support comes later if needed.
"""

from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("missing dependency: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNS_ROOT = REPO_ROOT / ".aidlc-orchestrator" / "runs"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def run_dir(run_id: str) -> Path:
    p = RUNS_ROOT / run_id
    if not p.exists():
        _die(f"run not found: {p}")
    return p


def patterns_overlap(a: str, b: str) -> bool:
    """Return True if globs `a` and `b` could match any common file.

    Heuristic component-wise match, with `**` matching any depth. Biased
    toward false positives — over-detecting overlap is safe; under-detecting
    would let conflicts through.
    """
    parts_a = a.split("/")
    parts_b = b.split("/")
    n = min(len(parts_a), len(parts_b))
    for i in range(n):
        x, y = parts_a[i], parts_b[i]
        if x == "**" or y == "**":
            return True
        if not (fnmatch.fnmatchcase(x, y) or fnmatch.fnmatchcase(y, x)):
            return False
    if len(parts_a) > n and parts_a[n] == "**":
        return True
    if len(parts_b) > n and parts_b[n] == "**":
        return True
    return len(parts_a) == len(parts_b)


def _list_locks(rd: Path) -> list[dict]:
    locks_dir = rd / "locks"
    if not locks_dir.exists():
        return []
    locks = []
    for f in sorted(locks_dir.glob("*.yaml")):
        locks.append(yaml.safe_load(f.read_text()))
    return locks


def cmd_acquire(args: argparse.Namespace) -> None:
    rd = run_dir(args.run_id)
    locks_dir = rd / "locks"
    locks_dir.mkdir(parents=True, exist_ok=True)

    existing = _list_locks(rd)
    conflicts: list[dict] = []
    for lock in existing:
        if lock["holder"] == args.holder:
            continue
        for new_glob in args.globs:
            for existing_glob in lock["globs"]:
                if not patterns_overlap(new_glob, existing_glob):
                    continue
                if args.mode == "read" and lock.get("mode") == "read":
                    continue
                conflicts.append({
                    "with_holder": lock["holder"],
                    "new_glob": new_glob,
                    "existing_glob": existing_glob,
                    "existing_mode": lock.get("mode", "write"),
                })

    if conflicts:
        conflicts_dir = rd / "conflicts"
        conflicts_dir.mkdir(parents=True, exist_ok=True)
        ts = now_iso().replace(":", "").replace("-", "")
        cid = f"path-{args.holder}-{ts}"
        record = {
            "id": cid,
            "detected_at": now_iso(),
            "kind": "path_collision",
            "requesting_holder": args.holder,
            "requested_mode": args.mode,
            "requested_globs": list(args.globs),
            "conflicts": conflicts,
            "resolution": None,
            "resolved_by": None,
        }
        (conflicts_dir / f"{cid}.yaml").write_text(
            yaml.safe_dump(record, sort_keys=False)
        )
        print(json.dumps({
            "granted": False,
            "conflicts": conflicts,
            "conflict_id": cid,
        }))
        for c in conflicts:
            print(
                f"CONFLICT: {args.holder} wants {c['new_glob']} but "
                f"{c['with_holder']} holds {c['existing_glob']} "
                f"({c['existing_mode']})",
                file=sys.stderr,
            )
        sys.exit(1)

    lock_file = locks_dir / f"{args.holder}.yaml"
    lock_file.write_text(yaml.safe_dump({
        "holder": args.holder,
        "acquired_at": now_iso(),
        "globs": list(args.globs),
        "mode": args.mode,
    }, sort_keys=False))
    print(json.dumps({
        "granted": True,
        "holder": args.holder,
        "globs": list(args.globs),
    }))
    print(
        f"GRANTED: {args.holder} → {len(args.globs)} glob(s) ({args.mode})",
        file=sys.stderr,
    )


def cmd_release(args: argparse.Namespace) -> None:
    rd = run_dir(args.run_id)
    lock_file = rd / "locks" / f"{args.holder}.yaml"
    if lock_file.exists():
        lock_file.unlink()
        print(f"RELEASED: {args.holder}")
    else:
        print(f"no locks held by {args.holder} (idempotent)")


def cmd_list(args: argparse.Namespace) -> None:
    rd = run_dir(args.run_id)
    locks = _list_locks(rd)
    if args.json:
        print(json.dumps(locks, indent=2))
        return
    if not locks:
        print("no active locks")
        return
    for lock in locks:
        print(
            f"{lock['holder']:30s} "
            f"{lock.get('mode','write'):6s} "
            f"{','.join(lock['globs'])}"
        )


def extract_symbols(src: str) -> dict:
    """Extract top-level function and class signatures from Python source."""
    tree = ast.parse(src)
    symbols: dict[str, dict] = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args]
            symbols[node.name] = {
                "kind": "function",
                "args": args,
                "returns": ast.unparse(node.returns) if node.returns else None,
            }
        elif isinstance(node, ast.ClassDef):
            methods: dict[str, dict] = {}
            for sub in ast.iter_child_nodes(node):
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    margs = [a.arg for a in sub.args.args]
                    methods[sub.name] = {
                        "args": margs,
                        "returns": ast.unparse(sub.returns) if sub.returns else None,
                    }
            symbols[node.name] = {"kind": "class", "methods": methods}
    return symbols


def cmd_snapshot(args: argparse.Namespace) -> None:
    rd = run_dir(args.run_id)
    snap_dir = rd / "symbol-baseline"
    snap_dir.mkdir(parents=True, exist_ok=True)
    snapshot: dict[str, dict] = {}
    for f in args.files:
        path = REPO_ROOT / f
        if not path.exists():
            snapshot[f] = {"missing": True}
            continue
        if path.suffix != ".py":
            snapshot[f] = {"non_python": True}
            continue
        try:
            symbols = extract_symbols(path.read_text())
            snapshot[f] = {"symbols": symbols, "captured_at": now_iso()}
        except SyntaxError as e:
            snapshot[f] = {"syntax_error": str(e)}
    (snap_dir / f"{args.holder}.yaml").write_text(
        yaml.safe_dump(snapshot, sort_keys=False)
    )
    py_count = sum(1 for v in snapshot.values() if "symbols" in v)
    print(f"snapshotted {len(snapshot)} file(s) ({py_count} parseable .py) for {args.holder}")


def cmd_check_symbols(args: argparse.Namespace) -> None:
    rd = run_dir(args.run_id)
    snap_file = rd / "symbol-baseline" / f"{args.holder}.yaml"
    if not snap_file.exists():
        _die(
            f"no baseline snapshot for {args.holder}; call `snapshot` first",
            code=2,
        )
    baseline = yaml.safe_load(snap_file.read_text()) or {}

    drifts: list[dict] = []
    for f in args.files:
        if f not in baseline or "symbols" not in baseline[f]:
            continue
        path = REPO_ROOT / f
        if not path.exists() or path.suffix != ".py":
            continue
        try:
            current = extract_symbols(path.read_text())
        except SyntaxError as e:
            drifts.append({"file": f, "kind": "syntax_error", "detail": str(e)})
            continue
        old = baseline[f]["symbols"]
        for name, sig in old.items():
            if name not in current:
                drifts.append({"file": f, "symbol": name, "kind": "removed", "old": sig})
            elif sig != current[name]:
                drifts.append({
                    "file": f,
                    "symbol": name,
                    "kind": "changed",
                    "old": sig,
                    "new": current[name],
                })
        for name in current:
            if name not in old:
                drifts.append({"file": f, "symbol": name, "kind": "added", "new": current[name]})

    if not drifts:
        print(json.dumps({"drift": False}))
        return

    others = [l for l in _list_locks(rd) if l["holder"] != args.holder]
    if not others:
        print(json.dumps({"drift": True, "conflict": False, "drifts": drifts}))
        print(
            f"DRIFT detected ({len(drifts)} item(s)) but no other active "
            f"holders — not a conflict",
            file=sys.stderr,
        )
        return

    conflicts_dir = rd / "conflicts"
    conflicts_dir.mkdir(parents=True, exist_ok=True)
    ts = now_iso().replace(":", "").replace("-", "")
    cid = f"drift-{args.holder}-{ts}"
    record = {
        "id": cid,
        "detected_at": now_iso(),
        "kind": "interface_drift",
        "holder": args.holder,
        "drifts": drifts,
        "active_other_holders": [l["holder"] for l in others],
        "resolution": None,
        "resolved_by": None,
    }
    (conflicts_dir / f"{cid}.yaml").write_text(yaml.safe_dump(record, sort_keys=False))
    print(json.dumps({
        "drift": True,
        "conflict": True,
        "conflict_id": cid,
        "drifts": drifts,
    }))
    print(
        f"CONFLICT (interface drift): {args.holder} changed {len(drifts)} "
        f"symbol(s); other active holders: {[l['holder'] for l in others]}",
        file=sys.stderr,
    )
    sys.exit(1)


def cmd_conflicts(args: argparse.Namespace) -> None:
    rd = run_dir(args.run_id)
    conflicts_dir = rd / "conflicts"
    if not conflicts_dir.exists():
        if args.json:
            print("[]")
        else:
            print("no conflicts")
        return
    records = []
    for f in sorted(conflicts_dir.glob("*.yaml")):
        records.append(yaml.safe_load(f.read_text()))
    if args.json:
        print(json.dumps(records, indent=2))
        return
    if not records:
        print("no conflicts")
        return
    for r in records:
        status = r.get("resolution") or "OPEN"
        print(f"{r['id']:50s} {r['kind']:18s} {status}")


def main() -> None:
    p = argparse.ArgumentParser(description="AIDLC Orchestrator Conflict Resolver")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_acq = sub.add_parser("acquire", help="acquire write or read locks")
    p_acq.add_argument("run_id")
    p_acq.add_argument("holder")
    p_acq.add_argument("--mode", choices=["write", "read"], default="write")
    p_acq.add_argument("globs", nargs="+")
    p_acq.set_defaults(func=cmd_acquire)

    p_rel = sub.add_parser("release", help="release all locks held by holder")
    p_rel.add_argument("run_id")
    p_rel.add_argument("holder")
    p_rel.set_defaults(func=cmd_release)

    p_list = sub.add_parser("list", help="list active locks")
    p_list.add_argument("run_id")
    p_list.add_argument("--json", action="store_true")
    p_list.set_defaults(func=cmd_list)

    p_snap = sub.add_parser("snapshot", help="capture baseline AST symbol map")
    p_snap.add_argument("run_id")
    p_snap.add_argument("holder")
    p_snap.add_argument("files", nargs="+")
    p_snap.set_defaults(func=cmd_snapshot)

    p_chk = sub.add_parser("check-symbols", help="diff against baseline; flag drift")
    p_chk.add_argument("run_id")
    p_chk.add_argument("holder")
    p_chk.add_argument("files", nargs="+")
    p_chk.set_defaults(func=cmd_check_symbols)

    p_cf = sub.add_parser("conflicts", help="list open conflict records")
    p_cf.add_argument("run_id")
    p_cf.add_argument("--json", action="store_true")
    p_cf.set_defaults(func=cmd_conflicts)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
