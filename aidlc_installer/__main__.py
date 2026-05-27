"""Allow ``python -m aidlc_installer`` to work."""
from .cli import main
import sys

sys.exit(main())
