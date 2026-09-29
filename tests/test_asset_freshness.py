"""The views must read the engine's rule assets live, not at import time.

An import-time snapshot is the trap: ``_RANKS = list(known_ranks())``
at module level would freeze the rule asset into the running GUI, so an expert
sign-off that replaced ``rules.json`` would not reach the rank dropdown until
Studio restarted — the window would look refreshed and would not be.
``prokname.reload_data()`` reaches what a view offers, and this guard keeps it
that way.

The textual half is what catches the regression when the behavioural half cannot:
an import-time call is invisible to a test that only ever checks the happy path.
"""
from __future__ import annotations

import ast
from pathlib import Path

from prokname.engine.generate import known_ranks

from prokname_studio.views.gen_view import _rank_names

GEN_VIEW = Path(__file__).resolve().parents[1] / "src" / "prokname_studio" / "views" / "gen_view.py"


def test_gen_view_does_not_freeze_the_rank_asset_at_import():
    """No module-level name may hold a snapshot of the engine's rule assets.

    Checked by AST rather than by substring: gen_view's own docstring quotes the
    old ``_RANKS = list(known_ranks().keys())`` line to explain why it is wrong,
    and a text search would fail on the explanation rather than on the defect.
    """
    tree = ast.parse(GEN_VIEW.read_text(encoding="utf-8"))
    frozen = [
        target.id
        for node in tree.body if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
        and any(
            isinstance(call, ast.Call)
            and getattr(call.func, "id", getattr(call.func, "attr", "")) == "known_ranks"
            for call in ast.walk(node.value)
        )
    ]
    assert not frozen, f"gen_view froze the rank asset at import time again: {frozen}"
    assert "_rank_names()" in GEN_VIEW.read_text(encoding="utf-8")


def test_the_rank_list_offered_tracks_the_engine():
    """What the view offers is what the engine currently knows, right now."""
    assert _rank_names() == list(known_ranks().keys())
