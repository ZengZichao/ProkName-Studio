"""Thin session state for ProkName Studio (derived data only; not persisted rules).

PySide6 is a hard dependency of this package, so there is one
:class:`StudioState` and no Qt-free twin: the headless variant existed only
because Studio used to live inside the engine, where the ``[gui]`` extra could be
absent. Here its absence is an install error, not a state to code for.
"""
from __future__ import annotations

from typing import Any

from prokname.presentation import decision
from PySide6.QtCore import QObject, Signal


class StudioState(QObject):
    """Holds transient UI state shared across views.

    All fields are derived from engine calls and can be rebuilt at any time; no
    naming rules are stored here. ``projects_changed`` lets views that mutate the
    project store (e.g. "add to project" from the Generate view) ask the Project
    view to reload its list.

    ``last_check`` is the raw :class:`prokname.dedup.model.CheckReport`; the three
    derived fields make its provenance readable without unwrapping the report at
    every call site. They are *derived from* ``last_check``, and every consumer
    that needs to attach a verdict to a candidate must go through
    :meth:`verdict_provenance_for` — which refuses to hand a verdict to a name
    other than the one that was queried.
    """

    projects_changed = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.candidates: list[Any] = []
        self.current_project: str | None = None
        self.last_check: Any = None
        # provenance of ``last_check``: the queried name, its verdict, its time
        self.last_check_query: str | None = None
        self.last_check_verdict: str | None = None
        self.last_checked_at: str | None = None

    def set_candidates(self, candidates: list[Any]) -> None:
        self.candidates = candidates

    def set_last_check(self, report: Any) -> None:
        """Record a finished dedup check and cache its provenance fields."""
        self.last_check = report
        self.last_check_query = getattr(report, "query", None)
        self.last_check_verdict = decision.verdict_value(report)
        checked_at = getattr(report, "checked_at", None)
        self.last_checked_at = str(checked_at) if checked_at else None

    def verdict_provenance_for(
        self, candidate_name: str | None
    ) -> decision.CheckProvenance | None:
        """Verdict (+query+timestamp) this candidate may inherit; else None."""
        return decision.check_provenance_for(self.last_check, candidate_name)

    def notify_projects_changed(self) -> None:
        self.projects_changed.emit()

    def clear(self) -> None:
        """Drop the transient candidate list (the last check is kept on purpose:
        it is the provenance of the session's check → project loop)."""
        self.candidates = []


__all__ = ["StudioState"]
