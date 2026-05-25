from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness_engine import ComplianceReport, SemanticIntent


class FrameworkAdapter(ABC):
    """Base class for framework adapters.
    
    Translates a framework-agnostic SemanticIntent into actual source code
    for a specific framework (React, Angular, Flutter, etc.).
    """

    @abstractmethod
    def render(self, intent: SemanticIntent) -> str:
        """Translate SemanticIntent to framework source code."""
        ...

    @abstractmethod
    def validate(self, code: str, intent: SemanticIntent) -> ComplianceReport:
        """Check generated code for token compliance."""
        ...

    def _token_to_tailwind(self, key: str, tokens: dict) -> str | None:
        """Helper: map a semantic token key to a Tailwind utility class if
        the token set matches standard Tailwind spacing values."""
        mapping = {4: "", 8: "", 12: "3", 16: "4", 24: "6", 32: "8"}
        val = None
        for cat in ("spacing", "radius"):
            if cat in tokens and key in tokens[cat]:
                val = tokens[cat][key]
                break
        if val is not None and isinstance(val, int):
            if val in mapping:
                return mapping[val]
            return str(val // 4)
        return None
