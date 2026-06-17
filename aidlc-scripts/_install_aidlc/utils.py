from __future__ import annotations

import os
import platform as _platform
import re
import shutil
import stat as _stat
import subprocess
import sys
import time
from pathlib import Path

from .constants import VALID_TOOLS


def _log(level: str, msg: str, **kwargs) -> None:
    stream = sys.stderr if level in ("ERROR", "WARNING") else sys.stdout
    print(f"[{level}] {msg}", file=stream)


def copy_tree(src: Path, dst: Path, dry_run: bool, exclude: set[str] | None = None) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")
    excl = set(exclude) if exclude else set()
    if dry_run:
        if excl:
            print(f"[DRY-RUN] Would copy {src} -> {dst} (excluding: {', '.join(sorted(excl))})")
        else:
            print(f"[DRY-RUN] Would copy {src} -> {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        if excl:
            ignore = shutil.ignore_patterns(*sorted(excl))
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore)
        else:
            shutil.copytree(src, dst, dirs_exist_ok=True)
        _rewrite_python3_win_tree(dst)
    except TypeError:
        if not dst.exists():
            if excl:
                ignore = shutil.ignore_patterns(*sorted(excl))
                shutil.copytree(src, dst, ignore=ignore)
            else:
                shutil.copytree(src, dst)
            _rewrite_python3_win_tree(dst)
        else:
            for p in src.rglob("*"):
                if p.name in excl:
                    continue
                rel = p.relative_to(src)
                target = dst / rel
                if p.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, target)
                    _rewrite_python3_win(target)


def _rmtree_force(path: Path) -> None:
    if not path.exists():
        return
    def _onerror(func, pth, exc_info):
        try:
            os.chmod(pth, _stat.S_IWRITE)
            func(pth)
        except PermissionError:
            time.sleep(0.5)
            try:
                os.chmod(pth, _stat.S_IWRITE)
                func(pth)
            except Exception:
                pass
    for p in path.rglob("*"):
        if p.is_file():
            try:
                os.chmod(p, _stat.S_IWRITE)
            except OSError:
                pass
    kwargs = {"onerror": _onerror} if sys.version_info < (3, 12) else {"onexc": _onerror}
    shutil.rmtree(path, ignore_errors=False, **kwargs)


def _retry_op(func, path: Path, max_retries: int = 3) -> None:
    for attempt in range(max_retries):
        try:
            func(path)
            return
        except OSError as e:
            if attempt == max_retries - 1:
                raise
            print(f"  (retrying {path.name}: {e})", file=sys.stderr)
            time.sleep(0.5)


def _rewrite_python3_win(file_path: Path) -> None:
    if not _is_windows():
        return
    if file_path.suffix.lower() not in (".md", ".mdx"):
        return
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    updated = re.sub(r'python3(?![.\w])', 'python', content)
    if updated != content:
        file_path.write_text(updated, encoding="utf-8")


def _rewrite_python3_win_tree(tree_root: Path) -> None:
    if not _is_windows():
        return
    for p in tree_root.rglob("*"):
        if p.is_file() and p.suffix.lower() in (".md", ".mdx"):
            _rewrite_python3_win(p)


def copy_file(src: Path, dst: Path, dry_run: bool) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")
    if dry_run:
        print(f"[DRY-RUN] Would copy file {src} -> {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    _retry_op(lambda p: p.chmod(0o755), dst)
    _rewrite_python3_win(dst)


def _is_windows() -> bool:
    return (
        sys.platform == "win32"
        or _platform.system() == "Windows"
        or _platform.system().upper().startswith(("MSYS", "MINGW", "CYGWIN"))
    )


def _venv_python(venv_path: Path) -> Path | None:
    for candidate in (
        venv_path / "bin" / "python",
        venv_path / "bin" / "python3",
        venv_path / "Scripts" / "python.exe",
        venv_path / "Scripts" / "python3.exe",
    ):
        if candidate.exists():
            return candidate
    return None


def ensure_target_requirements(repo_root: Path, target_root: Path, dry_run: bool) -> Path | None:
    target_req = target_root / "requirements.txt"
    if target_req.exists():
        return target_req
    src_req = repo_root / "requirements.txt"
    if not src_req.exists():
        return None
    if dry_run:
        print(f"[DRY-RUN] Would seed {target_req} from {src_req}")
        return target_req
    target_req.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_req, target_req)
    print(f"  base deps -> {target_req.relative_to(target_root)}")
    return target_req


def create_venv_and_install_requirements(target_root: Path, requirements_path: Path, dry_run: bool) -> None:
    venv_path = target_root / ".venv"
    if dry_run:
        print(f"[DRY-RUN] Would create venv at {venv_path}")
        print(f"[DRY-RUN] Would install requirements from {requirements_path}")
        return
    python_cmds = (["py", "python3", "python"] if _is_windows()
                   else ["python3", "python"])
    created = False
    last_err: Exception | None = None
    for cmd in python_cmds:
        try:
            print(f"Creating virtual environment using '{cmd}' at .venv/...")
            subprocess.run([cmd, "-m", "venv", str(venv_path)], check=True)
            created = True
            break
        except FileNotFoundError as e:
            last_err = e
            continue
        except subprocess.CalledProcessError as e:
            last_err = e
            continue
    if not created:
        raise EnvironmentError(
            f"Could not create virtual environment: no suitable Python found "
            f"(tried: {', '.join(python_cmds)}). Last error: {last_err}"
        )
    venv_python = _venv_python(venv_path)
    if venv_python is None:
        raise EnvironmentError(
            f"Could not find python executable in virtualenv at {venv_path}. "
            "Expected bin/python (macOS/Linux) or Scripts/python.exe (Windows)."
        )
    try:
        print("Upgrading pip in virtualenv...")
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
        )
    except subprocess.CalledProcessError:
        _log("WARNING", "Failed to upgrade pip in the virtualenv; continuing.")
    try:
        rel = requirements_path.relative_to(target_root) if target_root in requirements_path.parents else requirements_path
        print(f"Installing requirements from {rel} into virtualenv...")
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-r", str(requirements_path)],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to install requirements: {e}")


def parse_tools_string(s: str) -> list[str]:
    tools = [t.strip().lower() for t in s.split(",") if t.strip()]
    if not tools:
        raise ValueError("No tools specified")
    invalid = [t for t in tools if t not in VALID_TOOLS]
    if invalid:
        raise ValueError(
            f"Unknown tool(s): {', '.join(invalid)}. "
            f"Valid: {', '.join(VALID_TOOLS)}"
        )
    seen: set[str] = set()
    out: list[str] = []
    for t in tools:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


def _parse_semver(raw: str) -> tuple[int, ...] | None:
    import re
    m = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", raw)
    if not m:
        return None
    return tuple(int(x) if x else 0 for x in m.groups())


def _probe_version(cmd: list[str]) -> tuple[bool, str]:
    attempts: list[list[str]] = [cmd]
    if _is_windows():
        cmd_cmd = ["cmd", "/c"] + cmd
        pwsh_cmd = ["powershell", "-NoProfile", "-Command", " ".join(cmd)]
        attempts = [cmd_cmd, pwsh_cmd, cmd]
    for candidate in attempts:
        try:
            result = subprocess.run(candidate, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                out = (result.stdout or result.stderr or "").strip().splitlines()
                return (True, out[0]) if out else (True, "")
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
    return False, "not found"
