"""Smoke tests for Studio widgets.

These construct the real Qt views offscreen and exercise the generate path
end-to-end against the engine. PySide6 ships as a runtime dependency and
pytest-qt as a dev one, so there is no "GUI extra not installed" state left to
skip for: an import failure here is the install being broken.
"""
from __future__ import annotations

from prokname_studio import i18n
from prokname_studio.main_window import MainWindow
from prokname_studio.state import StudioState
from prokname_studio.views import (
    CheckView,
    DataView,
    GenerateView,
    ProjectView,
    RouteView,
)


def test_main_window_builds_all_nav_views(qapp) -> None:
    w = MainWindow(StudioState())
    assert w.stack.count() == 5
    w.show()
    w.close()


def test_generate_view_runs_engine(qapp, await_generation) -> None:
    v = GenerateView(StudioState())
    v.stem.setText("Wukong")
    v.type_combo.setCurrentIndex(0)  # feature
    v.rank_combo.setCurrentText("species")
    v.genus.setText("Bacillus")
    v._on_generate()
    await_generation(v)  # the engine call runs on a worker thread
    assert len(v._candidates) >= 1
    assert v.table.rowCount() == len(v._candidates)
    # selecting the first row renders a derivation tree
    v.table.selectRow(0)
    assert v.deriv.tree.topLevelItemCount() >= 1


def test_generate_view_gender_override_combo(qapp) -> None:
    """The gender override combo exists and is wired up."""
    v = GenerateView(StudioState())
    assert v.gender_override is not None
    assert v.gender_override.count() == 4  # auto, m, f, n


def test_route_view_runs_engine(qapp) -> None:
    v = RouteView(StudioState())
    v.source_combo.setCurrentIndex(0)  # pure_culture
    v._on_route()
    assert v._result is not None
    assert len(v._result.viable_paths) >= 1
    assert v.paths_table.rowCount() == len(v._result.viable_paths)


def test_route_view_icnp_occupied(qapp) -> None:
    """ICNP pre-emption produces conflict-guidance path."""
    v = RouteView(StudioState())
    v.source_combo.setCurrentIndex(0)  # pure_culture
    # select "yes" for icnp_occupied
    for i in range(v.icnp_combo.count()):
        if v.icnp_combo.itemData(i) == "yes":
            v.icnp_combo.setCurrentIndex(i)
            break
    v._on_route()
    assert v._result is not None
    assert any(p.role == "conflict-guidance" for p in v._result.viable_paths)


def test_check_view_runs_engine(qapp, qtbot) -> None:
    v = CheckView(StudioState())
    v.name_input.setText("Wukomonas beijingensis")
    v._on_check()
    # the check runs on a worker QThread — wait for the report to land
    qtbot.waitUntil(lambda: v._report is not None, timeout=10_000)
    assert v._report.verdict is not None
    assert v.verdict_view.sources_table.rowCount() >= 1


def test_project_view_builds(qapp) -> None:
    v = ProjectView(StudioState())
    assert v.project_list is not None
    assert v.proj_table is not None
    # the view should have built without error
    assert v.create_btn is not None


def test_data_view_populates(qapp) -> None:
    v = DataView(StudioState())
    assert v._status  # should have loaded something
    assert v.table.rowCount() >= 1
    # check headers are set
    assert v.table.columnCount() == 3


def test_i18n_switch_relabels_nav(qapp) -> None:
    """Switching language should re-label the nav items."""
    # Reset to a known language before creating the window
    i18n.set_language("zh")
    i18n.set_language("en")  # now we're at "en" for sure
    w = MainWindow(StudioState())
    assert w.nav.item(0).text() == "Generate"
    i18n.set_language("zh")
    assert w.nav.item(0).text() == "生成"
    w.close()
