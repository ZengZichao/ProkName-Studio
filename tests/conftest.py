"""Shared helpers for the Studio view tests.

There is no PySide6 gate anywhere in this suite on purpose. Studio declares Qt as
a runtime dependency, so a run that cannot import it has an install to fix, not a
result to report as green; the skip-based gating this file used to explain was a
property of the engine repository, where the GUI was an optional extra.

Everything with a home outside the repository is redirected into a temporary
directory for the whole run: a test suite that reads and writes the developer's
own stored preferences reports a different result depending on whose machine it
runs on, and can overwrite what the app they are testing would have stored.
"""

from __future__ import annotations

import pytest

from prokname_studio import appearance


@pytest.fixture(scope="session", autouse=True)
def _hermetic_settings(tmp_path_factory):
    """Send Studio's stored preferences to a throwaway ini file for the whole run.

    ``QSettings(organization, application)`` is a native store — a plist under
    ``~/Library/Preferences`` on macOS, the registry on Windows — so without this
    a test that switches the theme edits the developer's own machine, and a green
    run says nothing about the state it checked.
    """
    from PySide6.QtCore import QSettings

    path = tmp_path_factory.mktemp("qsettings") / "prokname-studio.ini"
    appearance.use_settings(QSettings(str(path), QSettings.Format.IniFormat))
    yield path
    appearance.use_settings(None)


@pytest.fixture
def await_generation(qtbot):
    """Wait for a view's worker thread to hand its result back.

    ``generate()`` moved off the UI thread (Studio now
    has one thread rule, not two), so a test that triggers generation cannot
    assert in the same breath. This joins the *real* signal path: the worker is
    waited on, then the event loop is pumped until the result callback has
    populated the view. No fixed sleep on the success path.
    """

    def _wait(view, timeout_ms: int = 20_000):
        worker = view._worker
        if worker is not None:
            assert worker.wait(timeout_ms), "the generation worker never finished"

        def done() -> bool:
            # ``_worker`` is cleared by the single reset path, which runs after
            # the result callback, so both conditions together prove the view
            # has been rendered — not merely that the thread ended.
            return view._worker is None and bool(view._candidates)

        try:
            qtbot.waitUntil(done, timeout=timeout_ms)
        except Exception:  # noqa: BLE001 - re-raise with the view's own state
            raise AssertionError(
                "generation produced no rendered result: "
                f"worker={view._worker!r} candidates={view._candidates!r}"
            ) from None
        return view._candidates

    return _wait
