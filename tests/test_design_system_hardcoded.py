"""DS-03: Hardcoded-value detection in design system skills.

Validates that design-system-composer and ui-constraint-validator
skills correctly document their hardcoded-value detection protocol.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

UI_CONSTRAINT_SKILL = (
    REPO_ROOT / ".agents" / "custom-skills" / "ui-constraint-validator" / "SKILL.md"
)
DS_COMPOSER_SKILL = (
    REPO_ROOT / ".agents" / "custom-skills" / "design-system-composer" / "SKILL.md"
)


class TestHardcodedValueDetection:
    def test_ui_constraint_skill_exists(self):
        assert UI_CONSTRAINT_SKILL.exists(), \
            "ui-constraint-validator SKILL.md must exist"

    def test_ds_composer_skill_exists(self):
        assert DS_COMPOSER_SKILL.exists(), \
            "design-system-composer SKILL.md must exist"

    def test_ui_constraint_validates_hardcoded_values(self):
        text = UI_CONSTRAINT_SKILL.read_text().lower()
        assert "hardcoded" in text or "var()" in text or "token" in text, \
            "ui-constraint-validator must detect hardcoded values"

    def test_ui_constraint_references_tokens_css(self):
        text = UI_CONSTRAINT_SKILL.read_text()
        assert "tokens.css" in text, \
            "ui-constraint-validator must reference tokens.css"

    def test_ds_composer_mentions_constraint_skill(self):
        text = DS_COMPOSER_SKILL.read_text()
        assert "ui-constraint-validator" in text, \
            "design-system-composer must reference ui-constraint-validator"

    def test_ds_composer_composes_from_primitives(self):
        text = DS_COMPOSER_SKILL.read_text().lower()
        assert "primitive" in text, \
            "design-system-composer must compose from primitives"

    def test_ui_constraint_can_block(self):
        text = UI_CONSTRAINT_SKILL.read_text().lower()
        assert "block" in text or "fail" in text, \
            "ui-constraint-validator must be able to block on violations"

    def test_ds_composer_has_token_audit(self):
        text = DS_COMPOSER_SKILL.read_text().lower()
        assert "audit" in text, \
            "design-system-composer must have a token audit step"

    def test_ui_constraint_spacing_radius_typography(self):
        text = UI_CONSTRAINT_SKILL.read_text().lower()
        keywords = ["spacing", "radius", "typography", "color", "shadow"]
        found = [k for k in keywords if k in text]
        assert len(found) >= 3, \
            f"Should check ≥3 visual properties, found {found}"

    def test_ds_composer_mentions_design_system_path(self):
        text = DS_COMPOSER_SKILL.read_text()
        assert "design-system" in text or "tokens" in text, \
            "design-system-composer must reference design-system path"
