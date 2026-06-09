import sys
from pathlib import Path


def main() -> None:
    _scripts_dir = Path(__file__).resolve().parent.parent / "aidlc-scripts"
    sys.path.insert(0, str(_scripts_dir))
    import install_aidlc  # type: ignore[import-untyped]

    sys.exit(install_aidlc.main())
