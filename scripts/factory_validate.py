#!/usr/bin/env python3
"""Validate a YAML or JSON document against a JSON Schema.

Usage:
    python3 scripts/factory_validate.py <schema.json> <doc.yaml|doc.json>

Exit codes:
    0  document is valid
    1  document is invalid (details on stderr)
    2  usage error or missing dependency
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def main() -> None:
    if len(sys.argv) != 3:
        _die(__doc__.strip())

    schema_path = Path(sys.argv[1])
    doc_path = Path(sys.argv[2])

    if not schema_path.exists():
        _die(f"schema not found: {schema_path}")
    if not doc_path.exists():
        _die(f"document not found: {doc_path}")

    try:
        from jsonschema import Draft7Validator
    except ImportError:
        _die("missing dependency: pip install jsonschema")

    schema = json.loads(schema_path.read_text())

    suffix = doc_path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except ImportError:
            _die("missing dependency: pip install pyyaml")
        doc = yaml.safe_load(doc_path.read_text())
    elif suffix == ".json":
        doc = json.loads(doc_path.read_text())
    else:
        _die(f"unsupported document extension: {suffix} (expected .yaml/.yml/.json)")

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.absolute_path))

    if not errors:
        print(f"OK {doc_path} matches {schema_path.name}")
        sys.exit(0)

    print(f"INVALID {doc_path} ({len(errors)} error(s)):", file=sys.stderr)
    for err in errors:
        loc = ".".join(str(p) for p in err.absolute_path) or "<root>"
        print(f"  - {loc}: {err.message}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
