from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "aidlc-scripts"

sys.path.insert(0, str(SCRIPTS))
import factory_complexity as mod


class TestComprehensiveRouting:
    def test_routing_is_large(self):
        assert mod.COMPREHENSIVE_ROUTING["complexity_tier"] == "LARGE"

    def test_no_skipped_stages(self):
        assert mod.COMPREHENSIVE_ROUTING["skip_stages"] == []

    def test_full_reviewer_pool(self):
        assert len(mod.COMPREHENSIVE_ROUTING["reviewer_pool"]) == 4
        assert "reviewer-code" in mod.COMPREHENSIVE_ROUTING["reviewer_pool"]
        assert "reviewer-security" in mod.COMPREHENSIVE_ROUTING["reviewer_pool"]
        assert "reviewer-performance" in mod.COMPREHENSIVE_ROUTING["reviewer_pool"]
        assert "reviewer-simplifier" in mod.COMPREHENSIVE_ROUTING["reviewer_pool"]

    def test_not_fast_path(self):
        assert mod.COMPREHENSIVE_ROUTING["fast_path"] is False

    def test_no_merge_codegen_gate(self):
        assert mod.COMPREHENSIVE_ROUTING["merge_codegen_gate"] is False

    def test_large_token_budget(self):
        assert mod.COMPREHENSIVE_ROUTING["tokens_max"] >= 1_000_000
