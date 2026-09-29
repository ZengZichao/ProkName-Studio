#!/usr/bin/env python3
"""PyInstaller entry point for ProkName Studio.

This script is the frozen-app bootstrap: it calls :func:`prokname_studio.app.main`,
the same entry point the ``prokname-studio`` console script uses. Pointing
PyInstaller at ``main`` rather than at ``run`` matters for two reasons:

* the bundle honours ``--version`` / ``--lang`` / ``--theme`` / ``--help``, so a
  terminal (and CI's smoke step) can ask the frozen app what it is without
  opening a window;
* ``main`` parses ``sys.argv`` through argparse, which tolerates the arguments a
  desktop launcher may hand an app — a double-clicked bundle that ignored its
  flags entirely could not be tested, and one that choked on an unknown argument
  would not open at all.
"""
from __future__ import annotations

import sys


def main() -> int:
    from prokname_studio.app import main as _main

    return _main()


if __name__ == "__main__":
    sys.exit(main())
