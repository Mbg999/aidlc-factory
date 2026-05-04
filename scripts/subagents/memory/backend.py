"""Abstract backend interface for the memory system.

Backends implement storage and retrieval. The MemoryStore delegates to
whichever backend is configured (local file, Engram HTTP, etc.).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .types import MemoryEntry, MemoryType, Scope


class MemoryBackend(ABC):
    """Contract that every memory backend must satisfy."""

    @abstractmethod
    def save(
        self,
        developer_id: str,
        entry: MemoryEntry,
    ) -> MemoryEntry:
        """Persist a memory entry. Returns the entry (possibly enriched with backend IDs)."""

    @abstractmethod
    def search(
        self,
        developer_id: str,
        *,
        tags: list[str] | None = None,
        memory_type: MemoryType | None = None,
        query: str | None = None,
        limit: int = 50,
        include_shared: bool = True,
        include_expired: bool = False,
    ) -> list[MemoryEntry]:
        """Retrieve entries matching filters."""

    @abstractmethod
    def delete(self, developer_id: str, entry_id: str) -> bool:
        """Remove a specific entry. Returns True if found and deleted."""

    @abstractmethod
    def get_profile(self, developer_id: str) -> dict[str, Any]:
        """Read developer profile metadata."""

    @abstractmethod
    def update_profile(self, developer_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Merge updates into developer profile. Returns the full profile."""

    @abstractmethod
    def list_developers(self) -> list[str]:
        """List all known developer IDs."""

    @abstractmethod
    def compact(self, developer_id: str) -> int:
        """Remove expired entries. Returns count removed."""

    @abstractmethod
    def share(self, developer_id: str, entry_id: str) -> bool:
        """Promote a private entry to shared scope."""
