"""ProkName Studio application entry point.

Builds the Qt application, installs the appearance (light / dark / auto) and the
language (Chinese / English / auto), constructs the main window, and runs the
event loop. Kept free of business logic — the window owns the views, which call
the public :mod:`prokname` engine API (``generate`` / ``check_name`` / ``route``).

``main()`` is the ``prokname-studio`` console script, so Studio is launched by
its own command rather than as a subcommand of the engine's CLI: the GUI is a
separate deliverable that depends on ``prokname``, not a part of it.
"""
from __future__ import annotations

import argparse
import sys

from prokname import __version__ as engine_version
from prokname import diagnostics
from PySide6.QtWidgets import QApplication

from . import __version__, appearance, i18n, icons
from .main_window import MainWindow
from .state import StudioState


def run(
    lang: str = "auto",
    theme: str = appearance.DEFAULT_PREFERENCE,
    debug: bool = False,
) -> int:
    """Launch ProkName Studio.

    Parameters
    ----------
    lang:
        Initial UI language: ``"auto"`` (follow the system locale), ``"zh"`` or
        ``"en"``. Live switching is available from the toolbar at runtime.
    theme:
        Initial appearance: ``"auto"`` (follow the desktop colour scheme),
        ``"light"`` or ``"dark"``. A ``--theme`` given on the command line is for
        this run only; a choice made in the toolbar is remembered.
    debug:
        Echo the swallowed third-party client output to stderr via
        :mod:`prokname.diagnostics`. It used to say "reserved for future use"
        while doing nothing at all, which is the same defect Studio's online
        checkbox was called out for: a control that looks configurable and is
        inert.

    Returns
    -------
    int
        The ``QApplication`` exit code.
    """
    if debug:
        diagnostics.configure(debug)

    app = QApplication.instance() or QApplication(
        [sys.argv[0] if sys.argv else "prokname-studio"]
    )
    app.setApplicationName(appearance.APPLICATION)
    app.setApplicationVersion(__version__)
    app.setOrganizationName(appearance.ORGANIZATION)
    app.setDesktopFileName("io.github.prokname.studio")

    icons.install(app)
    appearance.install(app, theme)
    i18n.install(app, lang)
    state = StudioState()
    window = MainWindow(state)
    window.show()

    return app.exec()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="prokname-studio",
        description=(
            f"ProkName Studio — the native desktop front-end for the prokname "
            f"nomenclature assistant (engine v{engine_version})."
        ),
    )
    parser.add_argument(
        "--lang",
        choices=("auto", "zh", "en"),
        default="auto",
        help="UI language: auto (follow the system locale), zh, en.",
    )
    parser.add_argument(
        "--theme",
        choices=appearance.PREFERENCES,
        default=appearance.DEFAULT_PREFERENCE,
        help="appearance: auto (follow the desktop), light, dark.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="echo the third-party client output prokname swallows (LPSN "
        "retries, rejected queries) to stderr. Changes no verdict and no exit "
        "code. Also settable via PROKNAME_DEBUG=1.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"prokname-studio {__version__} (prokname {engine_version})",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Entry point of the ``prokname-studio`` command, and of the frozen bundle."""
    args, unknown = _parser().parse_known_args(argv)
    if unknown:
        # A desktop launcher may hand an app arguments nobody typed (historically
        # `-psn_0_…`), and a bundle that refused to start over them would be worse
        # than one that mentions them. A real typo is still visible here instead of
        # being swallowed.
        print(f"prokname-studio: ignoring unrecognised argument(s): {' '.join(unknown)}",
              file=sys.stderr)
    return run(lang=args.lang, theme=args.theme, debug=args.debug)


__all__ = ["main", "run"]
