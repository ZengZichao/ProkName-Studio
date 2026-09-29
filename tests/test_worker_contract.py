"""The one thread rule Studio now has.

`check` used to run on a `QThread` while `gen` ran on the UI thread, so "may a
view block the event loop?" had two answers in one app. The fix is a shared
worker; these tests hold the properties the views depend on — because the
failure mode of getting any of them wrong is a window that never gives its
button back, which no amount of reading the happy path would reveal.
"""

from __future__ import annotations

import ast
import pathlib

from PySide6.QtWidgets import QWidget  # noqa: E402

from prokname_studio import worker as worker_mod  # noqa: E402
from prokname_studio.views import check_view, gen_view  # noqa: E402


def test_worker_reports_success_once_and_resets(qtbot) -> None:
    host = _Host()
    started = worker_mod.start(
        host, lambda: 42, busy=lambda: False,
        on_result=host.got, on_error=host.err)
    assert started is not None
    qtbot.waitUntil(lambda: host.finishes == 1, timeout=10_000)
    assert host.results == [42] and host.errors == []


def test_a_raising_callable_becomes_text_not_a_dead_button(qtbot) -> None:
    """`run()` must swallow nothing silently and must never let it escape."""
    host = _Host()

    def boom() -> None:
        raise KeyError("genus")          # str(KeyError) alone is unusably terse

    worker_mod.start(host, boom, busy=lambda: False,
                     on_result=host.got, on_error=host.err)
    qtbot.waitUntil(lambda: host.finishes == 1, timeout=10_000)
    assert host.results == []
    assert host.errors == ["KeyError: 'genus'"], host.errors


def test_busy_guard_starts_nothing(qtbot) -> None:
    host = _Host()
    started = worker_mod.start(
        host, lambda: 1, busy=lambda: True,
        on_result=host.got, on_error=host.err)
    assert started is None
    assert host.results == [] and host.errors == [] and host.finishes == 0


def test_exception_description_keeps_the_type_name() -> None:
    assert worker_mod.describe(ValueError("bad stem")) == "ValueError: bad stem"
    assert worker_mod.describe(RuntimeError("  ")) == "RuntimeError"
    assert worker_mod.describe(KeyError("x")) == "KeyError: 'x'"


def test_both_engine_views_go_through_the_shared_worker() -> None:
    """Structural tripwire: a view may not call the engine on the UI thread.

    Checked at source level because the regression would be silent — a
    synchronous call still *works*, it just freezes the window as soon as the
    computation stops being trivial.
    """
    for module in (check_view, gen_view):
        tree = ast.parse(pathlib.Path(module.__file__).read_text(encoding="utf-8"))
        imported = any(
            isinstance(node, ast.ImportFrom) and node.module == "worker"
            and any(a.name == "start" for a in node.names)
            for node in ast.walk(tree))
        assert imported, f"{module.__name__} no longer uses studio.worker.start"
        called = {
            node.func.id for node in ast.walk(tree)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        engine_call = {"check_name", "generate"} & called
        assert not engine_call, (
            f"{module.__name__} calls {engine_call} directly; hand it to the worker")


class _Host(QWidget):
    """Minimal view stand-in: the helper needs the reset path and two slots."""

    def __init__(self) -> None:
        super().__init__()
        self.results: list = []
        self.errors: list = []
        self.finishes = 0
        self._worker = None

    def got(self, value) -> None:
        self.results.append(value)

    def err(self, message: str) -> None:
        self.errors.append(message)

    def _on_worker_finished(self) -> None:
        self.finishes += 1
