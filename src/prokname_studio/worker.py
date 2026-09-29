"""One thread boundary for every engine call a Studio view makes.

Before this module existed, `check` ran on a `QThread` and `gen` ran on the UI
thread, so the same question — "is a view allowed to block the event loop?" —
had two different answers inside one application. The inconsistency was
invisible while generation is pure in-memory work; it would have become a
frozen window the first time a generation path touched a corpus scan or cache
IO, because the second view would have been written against the other rule.

The contract here is deliberately small and is now the only way a view reaches
the engine:

* hand over a callable plus its arguments (read the widgets *before* calling,
  because `run()` executes on the worker thread);
* receive exactly one of ``result_ready`` / ``failed``, then ``finished``;
* nothing may escape `run()` — in Qt 6 an uncaught Python exception in a
  `QThread` aborts the process, and the caller's button would stay disabled
  forever anyway.

`start()` also covers the two shapes that used to be re-implemented per view:
the re-entry guard, and the single "put the widget back" reset path.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QWidget


def describe(exc: BaseException) -> str:
    """Exception text for the UI: type plus message, so the cause is visible.

    A bare ``str(exc)`` is empty for many real errors (``KeyError``, ``TypeError``
    from C code), which would leave the user staring at an empty dialog.
    """
    text = str(exc).strip()
    name = type(exc).__name__
    return f"{name}: {text}" if text else name


class EngineWorker(QThread):
    """Run one callable off the GUI thread and report its outcome."""

    result_ready = Signal(object)
    failed = Signal(str)

    def __init__(self, fn: Callable[..., Any], *args: Any,
                 parent: QWidget | None = None, **kwargs: Any) -> None:
        super().__init__(parent)
        self._fn = fn
        self._args = args
        self._kwargs = kwargs

    def run(self) -> None:  # pragma: no cover - body is trivial, contract is tested
        try:
            value = self._fn(*self._args, **self._kwargs)
        except BaseException as exc:  # noqa: BLE001 - nothing may escape a thread
            self.failed.emit(describe(exc))
            return
        self.result_ready.emit(value)


def start(view: QWidget, fn: Callable[..., Any], *,
          busy: Callable[[], bool],
          on_result: Callable[[Any], None],
          on_error: Callable[[str], None],
          args: tuple[Any, ...] = (),
          kwargs: dict[str, Any] | None = None) -> EngineWorker | None:
    """Wire a worker to ``view`` and start it, unless one is already running.

    ``view`` must implement ``_on_worker_finished()``: that is the single reset
    path, connected to ``finished`` so success and failure put the controls
    back identically. ``busy`` is the view's own re-entry test (typically a
    lambda over a stored worker); returning early keeps the previous run's
    result authoritative instead of letting two threads race to repaint the
    same table.

    Arguments are passed as ``args``/``kwargs`` rather than as trailing
    parameters because Python forbids positional arguments after keyword ones.
    """
    if busy():
        return None
    worker = EngineWorker(fn, *args, parent=view, **(kwargs or {}))
    worker.result_ready.connect(on_result)
    worker.failed.connect(on_error)
    worker.finished.connect(view._on_worker_finished)
    worker.start()
    if not worker.isRunning():  # pragma: no cover - OS refused the thread
        view._on_worker_finished()
    # The worker is returned even when the OS refused to start it: `None` means
    # "a run was already in flight", and the view needs to tell those apart to
    # decide whether to warn. `isRunning()` is the caller's test for refusal.
    return worker
