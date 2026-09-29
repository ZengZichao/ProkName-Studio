"""``python -m prokname_studio`` — the same command line as ``prokname-studio``."""
from __future__ import annotations

import sys

from .app import main

if __name__ == "__main__":
    sys.exit(main())
