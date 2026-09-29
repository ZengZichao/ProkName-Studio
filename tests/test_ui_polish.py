"""Tests for the Studio UI polish pass: derivation tree fix, responsive
action states, empty-state placeholders, translated combos, and cross-view
project refresh.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from prokname.presentation import theme
from prokname.storage import ProjectStore

from prokname_studio import i18n
from prokname_studio.components.derivation_view import DerivationView
from prokname_studio.main_window import MainWindow
from prokname_studio.state import StudioState
from prokname_studio.views import CheckView, GenerateView, ProjectView, RouteView
from prokname_studio.views.gen_view import ADJECTIVE_ITEMS


@pytest.fixture(autouse=True)
def _english():
    """Deterministic UI language for label assertions."""
    i18n.set_language("en")


@pytest.fixture
def state():
    return StudioState()


@pytest.fixture
def tmp_store(monkeypatch, tmp_path):
    """Isolate ProjectView from the user's real projects directory."""
    from prokname.storage import ProjectStore

    monkeypatch.setattr(
        "prokname_studio.views.project_view.ProjectStore",
        lambda: ProjectStore(base_dir=tmp_path / "projects"),
    )


# -- derivation tree structure -------------------------------------------------


def test_derivation_tree_nests_under_single_root(qapp):
    """Regression: derivation must be a child of the name root, not a second
    top-level item, and the root must not be attached twice."""
    from prokname.engine.generate import generate

    view = DerivationView()
    cands = generate("Wukong", "feature", "species", genus="Bacillus")
    assert cands
    cand = cands[0]
    view.set_candidate(cand)

    tree = view.tree
    assert tree.topLevelItemCount() == 1
    root = tree.topLevelItem(0)
    assert root.text(0) == cand.name
    labels = {root.child(i).text(0) for i in range(root.childCount())}
    assert any(t.startswith("Derivation") for t in labels), labels
    assert not any("Generation failed" in t for t in labels)


def test_derivation_tree_renders_warnings_subtree(qapp):
    view = DerivationView()
    cand = SimpleNamespace(
        name="Bacillus wukongus",
        compliant=None,
        rank="species",
        grammatical_category="adjective",
        gender="m",
        derivation="stem Wukong → …",
        warnings=["needs_review: seed lexicon"],
    )
    view.set_candidate(cand)

    root = view.tree.topLevelItem(0)
    labels = {root.child(i).text(0) for i in range(root.childCount())}
    assert "Warnings" in labels


# -- responsive action states --------------------------------------------------


def test_generate_button_follows_stem_state(qapp, state):
    view = GenerateView(state)
    assert not view.generate_btn.isEnabled()
    view.stem.setText("Wukong")
    assert view.generate_btn.isEnabled()
    view.stem.setText("   ")
    assert not view.generate_btn.isEnabled()


def test_check_button_follows_name_state(qapp, state):
    view = CheckView(state)
    assert not view.check_btn.isEnabled()
    view.name_input.setText("Wukomonas beijingensis")
    assert view.check_btn.isEnabled()


def test_create_button_follows_project_name(qapp, state, tmp_store):
    view = ProjectView(state)
    assert not view.create_btn.isEnabled()
    view.create_name.setText("My project")
    assert view.create_btn.isEnabled()


def test_project_actions_disabled_without_selection(qapp, state, tmp_store):
    view = ProjectView(state)  # empty isolated store → no selection possible
    assert not view.delete_btn.isEnabled()
    assert not view.export_btn.isEnabled()
    assert not view.rate_btn.isEnabled()


# -- empty-state placeholders --------------------------------------------------


def test_check_view_placeholder_until_first_report(qapp, qtbot, state):
    view = CheckView(state)
    assert not view.verdict_view.placeholder.isHidden()
    assert view.verdict_view.sources_table.isHidden()
    assert view.verdict_view.verdict_label.isHidden()

    view.name_input.setText("Wukomonas beijingensis")
    view._on_check()
    # the check runs on a worker QThread — wait for the report to land, then
    # verify the view switched from placeholder to report rendering
    qtbot.waitUntil(lambda: view._report is not None, timeout=10_000)
    assert view.verdict_view.placeholder.isHidden()
    assert not view.verdict_view.sources_table.isHidden()
    assert not view.verdict_view.verdict_label.isHidden()
    # the loop is closed: the report also lands in the shared session state
    assert state.last_check is view._report


def test_result_table_and_derivation_localize_engine_keys(qapp, state,
                                                          await_generation):
    """Regression (i18n leak): under the zh UI, category/gender columns and
    the derivation tree must render localized labels, never the raw engine
    enum values. (In English the labels coincide with the enum spelling, so
    the leak is only observable in Chinese.)"""
    i18n.set_language("zh")
    view = GenerateView(state)
    view.stem.setText("Wukong")
    view.genus.setText("Bacillus")
    view._on_generate()
    await_generation(view)

    raw_keys = {"adjective", "genitive", "appositive", "m", "f", "n"}
    for row in range(view.table.rowCount()):
        cat = view.table.item(row, 1).text()
        gender = view.table.item(row, 2).text()
        assert cat not in raw_keys, f"raw category leaked: {cat!r}"
        assert gender not in raw_keys, f"raw gender leaked: {gender!r}"
    # and the localized labels actually appear
    assert "形容词" in {view.table.item(r, 1).text() for r in range(view.table.rowCount())}

    view.table.selectRow(0)
    texts = []
    for i in range(view.deriv.tree.topLevelItemCount()):
        root = view.deriv.tree.topLevelItem(i)
        for j in range(root.childCount()):
            texts.append(root.child(j).text(0))
    joined = " | ".join(texts)
    for key in ("adjective", "appositive"):
        assert key not in joined, f"raw category leaked into derivation tree: {key}"
    assert "形容词" in joined


def test_route_view_empty_state_hint(qapp, state):
    view = RouteView(state)
    assert view.paths_label.text() == i18n.tr("route_empty")
    view._on_route()
    assert view._result is not None
    assert view.paths_label.text().startswith(i18n.tr("route_viable_paths"))
    # info box mirrors whether there is anything to say
    has_info = bool(view._result.warnings or view._result.notes)
    assert view.info_box.isHidden() != has_info


# -- translated combos ---------------------------------------------------------


def test_adjective_formation_items_are_translated(qapp, state):
    view = GenerateView(state)
    texts = [view.adjective.itemText(i) for i in range(view.adjective.count())]
    assert len(texts) == len(ADJECTIVE_ITEMS)
    # raw enum keys must never leak into the UI
    assert all("_" not in t for t in texts), texts
    # values preserved for the engine call
    data = [view.adjective.itemData(i) for i in range(view.adjective.count())]
    assert data == [item[1] for item in ADJECTIVE_ITEMS]


def test_project_meta_combos_are_translated(qapp, state, tmp_store):
    view = ProjectView(state)
    src_first = view.create_data_source.itemText(0)
    assert src_first == i18n.tr("proj_meta_any")
    src_data = [
        view.create_data_source.itemData(i) for i in range(view.create_data_source.count())
    ]
    assert src_data == ["", "pure_culture", "MAG", "SAG", "unknown"]
    export_data = [view.export_combo.itemData(i) for i in range(view.export_combo.count())]
    assert set(export_data) == {"json", "csv", "markdown"}


def test_rate_button_uses_dedicated_label(qapp, state, tmp_store):
    view = ProjectView(state)
    assert view.rate_btn.text() == i18n.tr("proj_rate_btn")
    assert view.rate_btn.text() != i18n.tr("proj_rate_prompt")


# -- cross-view project refresh -------------------------------------------------


def test_projects_changed_signal_reloads_project_list(qapp, state, tmp_store):
    view = ProjectView(state)
    assert view.project_list.count() == 0

    view._store.create("Cross view")
    state.notify_projects_changed()
    items = [view.project_list.item(i).text() for i in range(view.project_list.count())]
    assert "Cross view" in items


def test_theme_tokens_match_legacy_badge_hues():
    """The central tokens keep the palette users already know.

    The hues themselves are the engine's semantic tokens; how they are painted on
    a light or a dark surface is Studio's decision (see ``test_appearance.py``,
    which owns the Fusion/palette assertions).
    """
    assert theme.COLOR_SUCCESS == "#27ae60"
    assert theme.COLOR_WARNING == "#f39c12"
    assert theme.COLOR_DANGER == "#c0392b"
    assert theme.COLOR_INFO == "#2980b9"


# -- check → project loop --------------------------------------------------------


def _patch_add_to_project(monkeypatch, tmp_path, project_name="Verdict loop"):
    from prokname.storage import ProjectStore

    monkeypatch.setattr(
        "prokname_studio.views.gen_view.ProjectStore",
        lambda: ProjectStore(base_dir=tmp_path / "projects"),
    )
    monkeypatch.setattr(
        "prokname_studio.views.gen_view.QInputDialog.getText",
        lambda *a, **kw: (project_name, True),
    )
    monkeypatch.setattr(
        "prokname_studio.views.gen_view.QMessageBox.information",
        lambda *a, **kw: None,
    )
    return ProjectStore(base_dir=tmp_path / "projects")


def _generated_view(state, await_generation):
    view = GenerateView(state)
    view.stem.setText("Wukong")
    view.genus.setText("Bacillus")
    view._on_generate()
    await_generation(view)  # generation is off the UI thread
    view.table.selectRow(0)
    return view


def test_add_to_project_persists_matching_check_verdict(
        qapp, state, monkeypatch, tmp_path, await_generation):
    """Matched case: a verdict obtained *for this name* is persisted with
    its query and timestamp, so exports stay traceable."""
    from prokname.dedup.model import CheckReport, Verdict

    store = _patch_add_to_project(monkeypatch, tmp_path)
    checked = CheckReport(
        query="Bacillus wukongus",
        checked_at="2026-09-21T09:00:00+00:00",
        verdict=Verdict.BLOCKED,
    )
    state.set_last_check(checked)

    view = _generated_view(state, await_generation)
    assert view._candidates[0].name == "Bacillus wukongus"
    view._on_add_to_project()

    project = store.load("Verdict loop")
    assert project is not None and project.candidates
    cand = project.candidates[0]
    assert cand.check_verdict == "blocked"
    assert cand.check_query == "Bacillus wukongus"
    assert cand.checked_at == "2026-09-21T09:00:00+00:00"
    # and the provenance is visible in both machine- and human-readable exports
    assert "2026-09-21T09:00:00+00:00" in store.export_csv("Verdict loop")
    assert "Bacillus wukongus @ 2026-09-21T09:00:00+00:00" in store.export_markdown(
        "Verdict loop"
    )


def test_add_to_project_never_inherits_a_foreign_verdict(
        qapp, state, monkeypatch, tmp_path, await_generation):
    """Cross-name case: checking Bacillus beijingensis must not put its
    BLOCKED ruling onto an unrelated Wukomonas/Bacillus-wukongus candidate."""
    from prokname.dedup.model import CheckReport, Verdict

    store = _patch_add_to_project(monkeypatch, tmp_path)
    state.set_last_check(CheckReport(
        query="Bacillus beijingensis",
        checked_at="2026-09-21T09:00:00+00:00",
        verdict=Verdict.CONFLICT,
    ))

    view = _generated_view(state, await_generation)
    view._on_add_to_project()

    cand = store.load("Verdict loop").candidates[0]
    assert cand.name == "Bacillus wukongus"
    assert cand.check_verdict is None, "a foreign verdict must not be attached"
    assert cand.check_query is None and cand.checked_at is None
    csv_text = store.export_csv("Verdict loop")
    assert "conflict" not in csv_text
    assert cand.check_provenance == ""


def test_verdict_provenance_survives_a_reload(qapp, state, monkeypatch, tmp_path, await_generation):
    """The stored provenance is part of the project file, not of the session."""
    from prokname.dedup.model import CheckReport, Verdict

    _patch_add_to_project(monkeypatch, tmp_path)
    state.set_last_check(CheckReport(
        query="Bacillus wukongus", checked_at="2026-09-21T09:00:00+00:00",
        verdict=Verdict.NO_CLEAR_CONFLICT,
    ))
    _generated_view(state, await_generation)._on_add_to_project()

    reloaded = ProjectStore(base_dir=tmp_path / "projects").load("Verdict loop")
    assert reloaded.candidates[0].check_verdict == "no_clear_conflict"
    assert reloaded.candidates[0].check_query == "Bacillus wukongus"


def test_add_to_project_without_any_check_stores_no_verdict(
        qapp, state, monkeypatch, tmp_path, await_generation):
    store = _patch_add_to_project(monkeypatch, tmp_path)
    _generated_view(state, await_generation)._on_add_to_project()
    cand = store.load("Verdict loop").candidates[0]
    assert cand.check_verdict is None and cand.check_query is None


# -- main window chrome ----------------------------------------------------------


def test_main_window_nav_and_toolbar_chrome(qapp):
    w = MainWindow(StudioState())
    assert w.nav.objectName() == "navList"
    assert not w.lang_bar.isMovable()
    assert not w.nav.horizontalScrollBarPolicy() == 0  # scrollbar off (policy constant)


def test_new_i18n_keys_exist_in_both_languages():
    new_keys = [
        "adj_place",
        "adj_second_declension",
        "adj_third_declension",
        "adj_loving",
        "adj_nourishing",
        "proj_rate_btn",
        "proj_meta_any",
    ]
    for key in new_keys:
        for lang in ("zh", "en"):
            assert key in i18n.STRINGS[lang], f"{key!r} missing from {lang!r}"
