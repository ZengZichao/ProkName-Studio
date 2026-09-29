"""Headless tests for Studio session state (no Qt dependency)."""
from __future__ import annotations

from prokname_studio.state import StudioState


def test_initial_state_is_empty() -> None:
    s = StudioState()
    assert s.candidates == []
    assert s.current_project is None
    assert s.last_check is None


def test_set_candidates_replaces() -> None:
    s = StudioState()
    s.set_candidates([1, 2, 3])
    assert s.candidates == [1, 2, 3]


def test_clear_empties_candidates() -> None:
    s = StudioState()
    s.set_candidates(["a", "b"])
    s.clear()
    assert s.candidates == []
