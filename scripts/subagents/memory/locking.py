"""File-level locking for safe concurrent access.

Uses fcntl.flock on Unix and msvcrt.locking on Windows.
All locks are advisory and scoped to a dedicated _locks/ directory.
"""
from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

_FCNTL = None
_MSVCRT = None
if sys.platform != "win32":
    import fcntl as _FCNTL
else:
    try:
        import msvcrt as _MSVCRT
    except ImportError:
        pass


@contextmanager
def file_lock(lock_path: Path, *, shared: bool = False) -> Generator[None, None, None]:
    """Acquire an advisory file lock.

    Args:
        lock_path: Path to the lock file (will be created if missing).
        shared: If True, acquire a shared (read) lock; otherwise exclusive (write).
    """
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR)
    try:
        if _FCNTL is not None:
            op = _FCNTL.LOCK_SH if shared else _FCNTL.LOCK_EX
            _FCNTL.flock(fd, op)
        elif _MSVCRT is not None:
            # Windows: lock first byte
            _MSVCRT.locking(fd, _MSVCRT.LK_LOCK, 1)

        yield

    finally:
        if _FCNTL is not None:
            _FCNTL.flock(fd, _FCNTL.LOCK_UN)
        elif _MSVCRT is not None:
            try:
                _MSVCRT.locking(fd, _MSVCRT.LK_UNLCK, 1)
            except Exception:
                pass
        os.close(fd)
