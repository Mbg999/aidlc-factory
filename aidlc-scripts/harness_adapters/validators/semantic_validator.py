from __future__ import annotations

import re
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from harness_engine import ComplianceReport, SemanticIntent


VALID_COMPONENT_TYPES = {"button", "input", "text", "link", "icon"}
VALID_LAYOUT_TYPES = {"stack", "inline", "box", "grid", "surface"}
REQUIRED_TOKEN_CATEGORIES = {"spacing", "color"}
PREFERRED_TOKEN_CATEGORIES = {"radius", "typography"}
HEX_COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{3,8}$")


class SemanticConstraintValidator:
    """Validates a SemanticIntent at the model level for token compliance,
    valid types, and cross-references. This is the V2 constraint validator
    that operates before code generation."""

    def validate(self, intent: SemanticIntent) -> ComplianceReport:
        deviations: list[dict] = []
        warnings: list[str] = []

        self._validate_token_categories(intent, deviations, warnings)
        self._validate_spacing_tokens(intent, deviations, warnings)
        self._validate_color_tokens(intent, deviations, warnings)
        self._validate_radius_tokens(intent, deviations, warnings)
        self._validate_components(intent, deviations, warnings)
        self._validate_layout(intent.layout, deviations, warnings)
        self._validate_cross_references(intent, deviations, warnings)

        return ComplianceReport(
            passed=len(deviations) == 0,
            total_elements=len(intent.components) + len(intent.layout),
            deviations=deviations,
            warnings=warnings,
        )

    def _validate_token_categories(
        self, intent: SemanticIntent, deviations: list[dict], warnings: list[str]
    ) -> None:
        for cat in REQUIRED_TOKEN_CATEGORIES:
            if cat not in intent.tokens or not intent.tokens[cat]:
                deviations.append({
                    "validator": "SemanticConstraintValidator",
                    "category": "tokens",
                    "subcategory": cat,
                    "type": "missing_category",
                    "detail": f"Required token category '{cat}' is missing or empty",
                })
        for cat in PREFERRED_TOKEN_CATEGORIES:
            if cat not in intent.tokens or not intent.tokens[cat]:
                warnings.append(f"Preferred token category '{cat}' is missing or empty")

    def _validate_spacing_tokens(
        self, intent: SemanticIntent, deviations: list[dict], warnings: list[str]
    ) -> None:
        spacing = intent.tokens.get("spacing", {})
        if not spacing:
            return

        if len(spacing) < 4:
            warnings.append(f"Only {len(spacing)} spacing tokens (recommend >=4)")

        bad_multiples = [k for k, v in spacing.items() if not isinstance(v, int) or v % 4 != 0]
        for k in bad_multiples:
            warnings.append(f"Spacing token '{k}' value {spacing[k]} is not a multiple of 4")

    def _validate_color_tokens(
        self, intent: SemanticIntent, deviations: list[dict], warnings: list[str]
    ) -> None:
        colors = intent.tokens.get("color", {})
        if not colors:
            return

        all_keys = " ".join(colors.keys())
        if not re.search(r"brand|primary", all_keys):
            warnings.append("No brand/primary color token found")
        if not re.search(r"neutral|text|bg|surface|border", all_keys):
            warnings.append("No neutral/background color token found")
        if not re.search(r"danger|success|warning|error|info", all_keys):
            warnings.append("No semantic color token (danger/success/warning/info) found")

        for key, val in colors.items():
            if not isinstance(val, str) or not HEX_COLOR_RE.match(val):
                deviations.append({
                    "validator": "SemanticConstraintValidator",
                    "category": "colors",
                    "subcategory": key,
                    "type": "invalid_color",
                    "detail": f"Color token '{key}' value '{val}' is not a valid hex color",
                })

    def _validate_radius_tokens(
        self, intent: SemanticIntent, deviations: list[dict], warnings: list[str]
    ) -> None:
        radius = intent.tokens.get("radius", {})
        if not radius:
            return

        if len(radius) < 3:
            warnings.append(f"Only {len(radius)} radius tokens (recommend >=3)")

        for key, val in radius.items():
            if not isinstance(val, int) or val < 0:
                deviations.append({
                    "validator": "SemanticConstraintValidator",
                    "category": "radius",
                    "subcategory": key,
                    "type": "invalid_radius",
                    "detail": f"Radius token '{key}' value '{val}' is invalid",
                })

    def _validate_components(
        self, intent: SemanticIntent, deviations: list[dict], warnings: list[str]
    ) -> None:
        if not intent.components:
            warnings.append("No components defined in intent")
            return

        for i, comp in enumerate(intent.components):
            ctype = comp.get("type", "")
            if ctype not in VALID_COMPONENT_TYPES:
                deviations.append({
                    "validator": "SemanticConstraintValidator",
                    "category": "components",
                    "subcategory": f"component[{i}]",
                    "type": "invalid_type",
                    "detail": f"Component at index {i} has invalid type '{ctype}'",
                })

            label = comp.get("label", "")
            if not label:
                warnings.append(f"Component at index {i} has no label")

    def _validate_layout(
        self, layout: list[dict], deviations: list[dict], warnings: list[str]
    ) -> None:
        if not layout:
            return

        for i, node in enumerate(layout):
            ltype = node.get("type", "")
            if ltype not in VALID_LAYOUT_TYPES:
                deviations.append({
                    "validator": "SemanticConstraintValidator",
                    "category": "layout",
                    "subcategory": f"layout[{i}]",
                    "type": "invalid_type",
                    "detail": f"Layout node at index {i} has invalid type '{ltype}'",
                })

            children = node.get("children", [])
            if children:
                self._validate_layout(children, deviations, warnings)

    def _validate_cross_references(
        self, intent: SemanticIntent, deviations: list[dict], warnings: list[str]
    ) -> None:
        spacing = intent.tokens.get("spacing", {})
        radius = intent.tokens.get("radius", {})

        for i, node in enumerate(intent.layout):
            gap = node.get("gap", "")
            if gap and gap not in spacing and gap not in radius:
                warnings.append(
                    f"Layout node at index {i} references gap '{gap}' "
                    f"which is not a known spacing or radius token"
                )

            for child in node.get("children", []):
                if "label" in child:
                    comp_labels = {c.get("label") for c in intent.components}
                    if child["label"] not in comp_labels:
                        warnings.append(
                            f"Layout child '{child['label']}' does not match "
                            f"any component label in the intent"
                        )
