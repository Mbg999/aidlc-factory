"""AIDLC persistent memory system.

Provides cross-session, multi-developer memory with concurrent access safety.
Supports pluggable backends: local file (default) or Engram HTTP API.
"""
from __future__ import annotations

from .store import MemoryStore
from .types import MemoryEntry, MemoryType
from .backend import MemoryBackend

__all__ = ["MemoryStore", "MemoryEntry", "MemoryType", "MemoryBackend"]
