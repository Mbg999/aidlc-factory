"""Memory entry types and data structures."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class MemoryType(str, Enum):
    """Classification of memory entries."""

    EPISODIC = "episodic"       # What happened (events, actions, outcomes)
    SEMANTIC = "semantic"       # Facts, decisions, knowledge
    PROCEDURAL = "procedural"   # How-to, patterns, workflows


class Scope(str, Enum):
    """Visibility scope of a memory entry."""

    PRIVATE = "private"   # Only visible to the owning developer
    SHARED = "shared"     # Visible to all developers in the project


@dataclass
class MemoryEntry:
    """Single unit of stored memory."""

    content: str
    memory_type: MemoryType = MemoryType.SEMANTIC
    scope: Scope = Scope.PRIVATE
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Auto-populated
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    developer_id: str = ""
    session_id: str = ""
    ttl_hours: float | None = None  # None = no expiry

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["memory_type"] = self.memory_type.value
        d["scope"] = self.scope.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MemoryEntry:
        d = dict(d)
        if "memory_type" in d:
            d["memory_type"] = MemoryType(d["memory_type"])
        if "scope" in d:
            d["scope"] = Scope(d["scope"])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

    def is_expired(self) -> bool:
        if self.ttl_hours is None:
            return False
        created = datetime.fromisoformat(self.created_at)
        age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600
        return age_hours > self.ttl_hours
