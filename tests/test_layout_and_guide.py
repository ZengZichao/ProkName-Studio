"""Adjustable layout (splitters, draggable table columns) and the guide.

The 0.2.0 layout contract: the panes a reader wants to resize are separated by
draggable ``QSplitter`` handles, the results table's columns resize by dragging
their header dividers, and the getting-started guide exists behind its own
button — never opened on its own.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QHeaderView, QSplitter

from prokname_studio import i18n
from prokname_studio.main_window import MainWindow
from prokname_studio.state import StudioState
from prokname_studio.views import GenerateView, ProjectView, RouteView

# A widget height the derivation/notes panes must no longer be capped at.
_WIDGET_MAX = 16_777_215


def _dispose(*widgets) -> None:
    """Tear widgets down deterministically before the test ends.

    Every window here subscribes to the module-global i18n signal, and
    ``deleteLater`` only takes effect when the event loop delivers the deferred
    delete — a bare ``processEvents()`` does not. Without forcing it through,
    the widgets stayed alive into the next test (whose language fixture then
    fired ``languageChanged`` into them) and into interpreter shutdown, whose
    GC ordering against the signal's QObject aborted the ubuntu/3.11 CI leg at
    exit (``none_dealloc``). Disconnect from the signal, close, and force the
    deferred deletion through before returning.
    """
    manager = i18n._manager()
    for widget in widgets:
        try:
            manager.languageChanged.disconnect(widget.retranslate_ui)
        except RuntimeError:
            pass  # not connected (already destroyed) — nothing to undo
        widget.close()
        widget.deleteLater()
    QApplication.instance().processEvents()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    QApplication.instance().processEvents()


@pytest.fixture(autouse=True)
def _english():
    i18n.set_language("en")


@pytest.fixture
def tmp_store(monkeypatch, tmp_path):
    """Isolate ProjectView from the user's real projects directory."""
    from prokname.storage import ProjectStore

    monkeypatch.setattr(
        "prokname_studio.views.project_view.ProjectStore",
        lambda: ProjectStore(base_dir=tmp_path / "projects"),
    )


def _fake_candidate(**overrides):
    base = dict(
        name="Bacillus wukongus",
        epithet="wukongus",
        rank="species",
        grammatical_category="adjective",
        gender="m",
        derivation="stem Wukong → wukong + -us",
        compliant=None,
        warnings=[],
    )
    base.update(overrides)
    return SimpleNamespace(**base)


# -- generate view: draggable columns ------------------------------------------


def test_generate_table_columns_are_interactive(qapp):
    view = GenerateView(StudioState())
    header = view.table.horizontalHeader()
    for col in range(view.table.columnCount()):
        mode = header.sectionResizeMode(col)
        assert mode == QHeaderView.ResizeMode.Interactive, f"column {col} is {mode}"
    # the last column still fills the leftover width, so resizing the others
    # never leaves a dead margin on the right of the table
    assert header.stretchLastSection()


def test_generate_column_width_survives_repopulation(qapp):
    """Dragging a column sticks: a re-render (language/theme switch, new
    generate) must not undo the width the user set."""
    view = GenerateView(StudioState())
    candidates = [_fake_candidate(), _fake_candidate(name="Wukomonas beijingensis")]
    view._populate_table(candidates)  # first populate auto-fits once
    view.table.setColumnWidth(0, 300)
    view.table.setColumnWidth(1, 160)
    view._populate_table(candidates)
    assert view.table.columnWidth(0) == 300
    assert view.table.columnWidth(1) == 160


def test_generate_columns_autofit_once_on_first_result(qapp):
    view = GenerateView(StudioState())
    view._populate_table([_fake_candidate()])
    assert view._columns_fitted
    # the auto-fit is a one-shot: a second populate keeps user widths, and an
    # empty result set must not trigger the fit at all
    view2 = GenerateView(StudioState())
    view2._populate_table([])
    assert not view2._columns_fitted


# -- generate view: vertical splitter ------------------------------------------


def test_generate_results_split_vertically_on_a_draggable_divider(qapp):
    view = GenerateView(StudioState())
    assert isinstance(view.splitter, QSplitter)
    assert view.splitter.orientation() == Qt.Orientation.Vertical
    assert view.splitter.widget(0) is view.table
    assert view.splitter.widget(1) is view.deriv
    # a pane that cannot be collapsed would let one drag erase the other
    assert not view.splitter.childrenCollapsible()
    # the fixed height cap is gone, or the handle could not grow the tree
    assert view.deriv.maximumHeight() == _WIDGET_MAX


def test_generate_table_keeps_the_extra_space(qapp):
    """With room to spare the table (stretch 1) — not the derivation pane —
    absorbs it."""
    from PySide6.QtWidgets import QGroupBox

    view = GenerateView(StudioState())
    view.resize(900, 900)
    view.show()
    # A short screen clamps the window, so guarantee the surplus instead of
    # hoping for it: hide the input form (irrelevant to what this checks) and
    # give the splitter nearly the whole page.
    groups = view.findChildren(QGroupBox)
    if groups:
        groups[0].hide()
    QApplication.instance().processEvents()
    sizes = view.splitter.sizes()
    assert sizes[0] > sizes[1]
    _dispose(view)


def test_generate_splitter_resizes_the_derivation_pane(qapp):
    view = GenerateView(StudioState())
    view.resize(900, 780)
    view.show()
    total = view.splitter.height() - view.splitter.handleWidth()
    want = (total + 2) // 3
    view.splitter.setSizes([total - want, want])
    assert view.deriv.height() >= want - 10
    _dispose(view)


# -- route view: vertical splitter ---------------------------------------------


def test_route_results_split_vertically_on_a_draggable_divider(qapp):
    view = RouteView(StudioState())
    assert isinstance(view.splitter, QSplitter)
    assert view.splitter.orientation() == Qt.Orientation.Vertical
    assert view.splitter.widget(0) is view.paths_table
    assert view.splitter.widget(1) is view.info_box
    assert not view.splitter.childrenCollapsible()
    assert view.info_box.maximumHeight() == _WIDGET_MAX


# -- project view: horizontal splitter -----------------------------------------


def test_project_panes_split_horizontally_on_a_draggable_divider(qapp, tmp_store):
    view = ProjectView(StudioState())
    assert isinstance(view.splitter, QSplitter)
    assert view.splitter.orientation() == Qt.Orientation.Horizontal
    assert view.splitter.count() == 2
    assert not view.splitter.childrenCollapsible()


def test_project_candidates_pane_keeps_the_larger_share(qapp, tmp_store):
    """The candidates pane starts with the larger share (the old 1 : 2 stretch);
    the splitter only makes the split point user-adjustable."""
    view = ProjectView(StudioState())
    view.resize(1000, 600)
    view.show()
    sizes = view.splitter.sizes()
    assert sizes[1] > sizes[0]
    _dispose(view)


def test_project_splitter_resizes_the_panes(qapp, tmp_store):
    view = ProjectView(StudioState())
    view.resize(1000, 600)
    view.show()
    total = view.splitter.width() - view.splitter.handleWidth()
    want = (total + 3) // 4
    view.splitter.setSizes([total - want, want])
    assert view.splitter.widget(1).width() >= want - 10
    _dispose(view)


# -- the getting-started guide --------------------------------------------------


def test_guide_is_closed_by_default(qapp):
    """The walkthrough is opt-in: nothing may put it on screen at startup."""
    w = MainWindow(StudioState())
    assert w._guide_dialog is None
    w.show()
    _dispose(w)
    assert w._guide_dialog is None


def test_guide_opens_from_the_toolbar_button(qapp):
    w = MainWindow(StudioState())
    w._show_guide()
    dialog = w._guide_dialog
    assert dialog is not None
    assert not dialog.isHidden()
    # modeless: the user has to be able to act on the pages underneath
    assert not dialog.isModal()
    # disposing the window deletes its child dialog with it
    _dispose(w)


def test_guide_button_and_menu_entry_are_labelled(qapp):
    w = MainWindow(StudioState())
    assert w.guide_btn.text() == i18n.tr("guide_button")
    assert w.act_guide.text() == i18n.tr("guide_button")
    i18n.set_language("zh")
    assert w.guide_btn.text() == i18n.tr("guide_button")
    assert w.guide_btn.text() == "新手引导"
    _dispose(w)


def test_go_to_page_switches_the_navigation(qapp):
    w = MainWindow(StudioState())
    w.go_to_page("route")
    assert w.nav.currentRow() == 1
    w.go_to_page("project")
    assert w.nav.currentRow() == 3
    # an unknown key changes nothing instead of crashing the walkthrough
    w.go_to_page("no_such_page")
    assert w.nav.currentRow() == 3
    _dispose(w)


def test_guide_steps_and_navigation(qapp):
    w = MainWindow(StudioState())
    w._show_guide()
    dialog = w._guide_dialog
    # overview + five pages + interface tips
    assert dialog.step_list.count() == 7

    # the overview owns no page, so it cannot navigate
    dialog.step_list.setCurrentRow(0)
    assert not dialog.go_btn.isEnabled()
    assert not dialog.prev_btn.isEnabled()
    assert dialog.next_btn.isEnabled()

    # a page-bound step can jump, and the jump moves the real navigation
    dialog.step_list.setCurrentRow(1)  # check
    assert dialog.go_btn.isEnabled()
    dialog.go_btn.click()
    assert w.nav.currentRow() == 2  # check is the third nav entry

    # the last step has no "next" left
    dialog.step_list.setCurrentRow(6)
    assert not dialog.next_btn.isEnabled()
    dialog.next_btn.click()  # no-op at the end
    assert dialog.step_list.currentRow() == 6

    # disposing the window deletes its child dialog with it
    _dispose(w)


def test_guide_retranslates(qapp):
    w = MainWindow(StudioState())
    w._show_guide()
    dialog = w._guide_dialog
    dialog.step_list.setCurrentRow(2)  # generate
    i18n.set_language("zh")
    assert dialog.step_list.item(2).text() == "② 生成"
    assert "生成" in dialog.text.toPlainText()
    # disposing the window deletes its child dialog with it
    _dispose(w)


def test_guide_i18n_keys_exist_in_both_languages():
    keys = [
        "guide_button",
        "guide_title",
        "guide_prev",
        "guide_next",
        "guide_go",
        "guide_close",
        "guide_step_overview",
        "guide_step_check",
        "guide_step_generate",
        "guide_step_route",
        "guide_step_project",
        "guide_step_data",
        "guide_step_tips",
        "guide_content_overview",
        "guide_content_check",
        "guide_content_generate",
        "guide_content_route",
        "guide_content_project",
        "guide_content_data",
        "guide_content_tips",
    ]
    for key in keys:
        for lang in ("zh", "en"):
            assert key in i18n.STRINGS[lang], f"{key!r} missing from {lang!r}"
