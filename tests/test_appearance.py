"""The light / dark appearance layer: resolution, tokens, and live switching.

The palette decision is split in two, and so is this file. :func:`resolve`,
:func:`token` and :func:`badge_css` are pure and are tested as such; the rest
needs a ``QApplication``, because it is about what the window actually looks like.
"""
from __future__ import annotations

import re

import pytest
from prokname.dedup.model import CheckReport, Verdict
from prokname.presentation import theme
from prokname.storage import ProjectStore
from prokname.storage.model import Candidate
from PySide6.QtCore import QSettings

from prokname_studio import appearance, i18n
from prokname_studio.main_window import MainWindow
from prokname_studio.state import StudioState

AUTO = appearance.AUTO
LIGHT = appearance.LIGHT
DARK = appearance.DARK


@pytest.fixture
def state():
    return StudioState()


@pytest.fixture(autouse=True)
def _english():
    i18n.set_language("en")


@pytest.fixture(autouse=True)
def _start_light(qapp):
    """Begin every test from a known mode, whatever the previous one left behind."""
    appearance.apply(qapp, LIGHT)


@pytest.fixture(autouse=True)
def _isolated_store(monkeypatch, tmp_path):
    """Keep the window's Project view off the developer's real projects."""
    monkeypatch.setattr(
        "prokname_studio.views.project_view.ProjectStore",
        lambda: ProjectStore(base_dir=tmp_path / "projects"),
    )


# --------------------------------------------------------------------------- #
# the pure part: which mode, which hue
# --------------------------------------------------------------------------- #


def test_explicit_preference_pins_the_mode():
    assert appearance.resolve(LIGHT, True) == LIGHT
    assert appearance.resolve(DARK, False) == DARK


def test_auto_follows_the_desktop():
    assert appearance.resolve(AUTO, True) == DARK
    assert appearance.resolve(AUTO, False) == LIGHT


@pytest.mark.parametrize("junk", ["", "Light", "system", None])
def test_an_unknown_preference_falls_back_to_auto(junk):
    """A typo must not force a look the user never asked for."""
    assert appearance.resolve(junk, True) == DARK  # what auto would do
    assert appearance.resolve(junk, False) == LIGHT


def test_every_semantic_token_has_a_dark_spelling():
    """Each hue the decision layer can hand a widget must lift for a dark surface.

    A token missing from the map lifts nothing: the widget then paints a hue
    specified against white onto a near-black window, and this is the one place
    that can notice without a screenshot.
    """
    tokens = {value.lower() for name, value in vars(theme).items()
              if name.startswith("COLOR_")}
    unmapped = sorted(tokens - set(appearance.DARK_TOKENS))
    assert not unmapped, f"tokens with no dark spelling: {unmapped}"


def test_token_is_identity_in_light_and_lifted_in_dark():
    assert appearance.token(theme.COLOR_SUCCESS, LIGHT) == theme.COLOR_SUCCESS
    lifted = appearance.token(theme.COLOR_SUCCESS, DARK)
    assert lifted != theme.COLOR_SUCCESS
    assert _luminance(lifted) > _luminance(theme.COLOR_SUCCESS)


def test_an_unmapped_colour_passes_through_unchanged():
    """Degrade to the original hue, never to no colour at all."""
    assert appearance.token("#123456", DARK) == "#123456"


def test_every_lifted_token_stays_readable_on_the_dark_surface():
    for light, dark in appearance.DARK_TOKENS.items():
        ratio = _contrast(dark, appearance.DARK_SPEC.base)
        assert ratio >= 4.5, f"{light} → {dark} is only {ratio:.2f}:1 on the dark base"


def test_light_paints_the_engine_tokens_unchanged():
    """Studio invents no light hues: they are the engine's semantic tokens.

    Recording what this does *not* fix, so the next reader does not mistake it for
    an accessibility pass: on the white surface the inherited success and warning
    inks sit at 2.9:1 and 2.2:1, under WCAG AA for body text. That is the engine
    palette's business (the CLI renders the same tokens as ANSI colours, where it
    is a non-issue), and dark mode is where Studio chose its own hues — every
    lifted token above clears 4.5:1.
    """
    for color in appearance.DARK_TOKENS:
        assert appearance.token(color, LIGHT) == color


def test_badge_is_a_solid_pill_in_light_and_a_tinted_one_in_dark():
    light = appearance.badge_css(theme.COLOR_DANGER, mode=LIGHT)
    assert f"background-color: {theme.COLOR_DANGER}" in light
    assert "color: #ffffff" in light

    dark = appearance.badge_css(theme.COLOR_DANGER, mode=DARK)
    assert "rgba(" in dark
    assert "border: 1px solid" in dark
    assert f"color: {appearance.DARK_TOKENS[theme.COLOR_DANGER]}" in dark
    assert "color: #ffffff" not in dark, "white ink is the light mode's pill recipe"


def test_both_stylesheets_are_fully_substituted():
    for mode, qss in appearance.QSS.items():
        assert "$" not in qss, f"{mode} QSS left a placeholder unsubstituted"
        assert "navList" in qss and "primaryButton" in qss


def test_the_two_stylesheets_are_not_the_same_text():
    assert appearance.QSS[LIGHT] != appearance.QSS[DARK]


# --------------------------------------------------------------------------- #
# the painted part: what the application actually gets
# --------------------------------------------------------------------------- #


def test_light_paints_a_light_window(qapp):
    appearance.apply(qapp, LIGHT)
    assert appearance.current_mode() == LIGHT
    assert qapp.palette().window().color().name() == appearance.LIGHT_SPEC.window


def test_dark_paints_a_dark_window(qapp):
    appearance.apply(qapp, DARK)
    assert appearance.current_mode() == DARK
    window = qapp.palette().window().color().name()
    assert window == appearance.DARK_SPEC.window
    assert _luminance(window) < 0.2, f"{window} is not a dark window colour"
    assert appearance.QSS[DARK] in qapp.styleSheet()


def test_switching_replaces_the_previous_stylesheet(qapp):
    """``setStyleSheet`` replaces rather than appends.

    A dark stylesheet stacked on a light one would keep the light rules alive for
    any selector the dark text happened not to repeat.
    """
    appearance.apply(qapp, DARK)
    assert appearance.LIGHT_SPEC.nav_hover not in qapp.styleSheet()
    appearance.apply(qapp, LIGHT)
    assert appearance.DARK_SPEC.nav_hover not in qapp.styleSheet()


def test_fusion_style_survives_a_switch(qapp):
    """Both modes ride the same Fusion base, so the look stays cross-platform."""
    for mode in (LIGHT, DARK, LIGHT):
        appearance.apply(qapp, mode)
        klass = qapp.style().metaObject().className()
        assert klass in ("QFusionStyle", "QStyleSheetStyle"), klass


def test_the_change_signal_carries_the_resolved_mode(qapp):
    seen: list[str] = []
    slot = lambda mode: seen.append(mode)  # noqa: E731 - one-line observer
    appearance.connect_changed(slot)
    try:
        appearance.apply(qapp, DARK)
        appearance.apply(qapp, LIGHT)
    finally:
        appearance._manager().appearanceChanged.disconnect(slot)
    assert seen == [DARK, LIGHT]


def test_auto_mode_rereads_the_desktop_scheme(qapp, monkeypatch):
    monkeypatch.setattr(appearance, "system_prefers_dark", lambda: True)
    assert appearance.apply(qapp, AUTO) == DARK
    monkeypatch.setattr(appearance, "system_prefers_dark", lambda: False)
    assert appearance.apply(qapp, AUTO) == LIGHT


def test_the_desktop_is_watched_once_per_app(qapp):
    """Repeated installs must not stack handlers on ``colorSchemeChanged``.

    A second connection means a desktop switch repaints twice and emits twice —
    which turns a live switch into a flicker and a widget's re-render into two.
    """
    appearance.install(qapp, AUTO)
    watcher = getattr(qapp, "_prokname_desktop_watcher", None)
    assert watcher is not None
    appearance.install(qapp, AUTO)
    assert qapp._prokname_desktop_watcher is watcher


# --------------------------------------------------------------------------- #
# the stored preference
# --------------------------------------------------------------------------- #


def test_preference_round_trips_through_settings(tmp_path):
    settings = QSettings(str(tmp_path / "studio.ini"), QSettings.Format.IniFormat)
    assert appearance.load_preference(settings) == AUTO
    appearance.save_preference(DARK, settings)
    assert appearance.load_preference(settings) == DARK


def test_a_bogus_stored_value_reads_back_as_auto(tmp_path):
    settings = QSettings(str(tmp_path / "studio.ini"), QSettings.Format.IniFormat)
    appearance.save_preference("neon", settings)
    assert appearance.load_preference(settings) == AUTO


def test_install_uses_the_stored_preference(qapp):
    appearance.save_preference(DARK)
    try:
        assert appearance.install(qapp) == DARK
        assert appearance.current_preference() == DARK
    finally:
        appearance.save_preference(AUTO)


def test_a_command_line_theme_does_not_overwrite_the_stored_one(qapp):
    """``--theme light`` is for this run; only a toolbar choice is remembered.

    A launch flag that wrote to settings would silently retire the user's own
    choice for every later start.
    """
    appearance.save_preference(DARK)
    try:
        appearance.install(qapp, LIGHT)
        assert appearance.current_mode() == LIGHT
        assert appearance.load_preference() == DARK
    finally:
        appearance.save_preference(AUTO)


def test_the_toolbar_choice_is_the_one_that_persists(qapp, state):
    appearance.save_preference(AUTO)
    window = MainWindow(state)
    try:
        _select_theme(window, DARK)
        assert appearance.current_mode() == DARK
        assert appearance.load_preference() == DARK
    finally:
        appearance.save_preference(AUTO)
        window.deleteLater()


# --------------------------------------------------------------------------- #
# live switching: the window follows the mode without a restart
# --------------------------------------------------------------------------- #


def test_the_window_offers_both_modes_and_auto(qapp, state):
    window = MainWindow(state)
    data = [window.theme_combo.itemData(i) for i in range(window.theme_combo.count())]
    assert data == [AUTO, LIGHT, DARK]
    labels = [window.theme_combo.itemText(i) for i in range(window.theme_combo.count())]
    assert labels == ["Follow system", "Light", "Dark"]
    window.deleteLater()


def test_the_appearance_switcher_is_translated(qapp, state):
    """The control that changes the look must itself speak the current language."""
    window = MainWindow(state)
    i18n.set_language("zh")
    try:
        assert window.theme_label.text() == "外观"
        assert window.theme_combo.currentText() == "亮色"
        labels = [window.theme_combo.itemText(i) for i in range(window.theme_combo.count())]
        assert labels == ["跟随系统", "亮色", "暗色"]
    finally:
        i18n.set_language("en")
    window.deleteLater()


def test_choosing_dark_from_the_toolbar_repaints_the_window(qapp, state):
    window = MainWindow(state)
    _select_theme(window, DARK)
    assert qapp.palette().window().color().name() == appearance.DARK_SPEC.window
    window.deleteLater()


def test_switching_language_does_not_change_the_mode(qapp, state):
    window = MainWindow(state)
    appearance.apply(qapp, DARK)
    i18n.set_language("zh")
    try:
        assert appearance.current_mode() == DARK
    finally:
        i18n.set_language("en")
    window.deleteLater()


def test_the_verdict_badge_follows_the_mode(qapp, state):
    """A report rendered while dark must not keep the light pill it was built with."""
    window = MainWindow(state)
    verdict_view = window._views["check"].verdict_view
    verdict_view.set_report(CheckReport(
        query="Bacillus wukongus",
        checked_at="2026-09-29T00:00:00+00:00",
        verdict=Verdict.CONFLICT,
    ))
    appearance.apply(qapp, LIGHT)
    light_sheet = verdict_view.verdict_label.styleSheet()
    appearance.apply(qapp, DARK)
    dark_sheet = verdict_view.verdict_label.styleSheet()
    assert light_sheet != dark_sheet
    assert theme.COLOR_DANGER in light_sheet
    assert appearance.DARK_TOKENS[theme.COLOR_DANGER] in dark_sheet
    window.deleteLater()


def test_table_foregrounds_follow_the_mode(qapp, state, tmp_path):
    store = ProjectStore(base_dir=tmp_path / "projects")
    store.create("Theme")
    store.add_candidate("Theme", Candidate(
        name="Bacillus wukongus", epithet="wukongus", rank="species",
        grammatical_category="adjective", gender="m", derivation="stem",
        compliant=True, warnings=[],
    ))

    window = MainWindow(state)
    project_view = window._views["project"]
    project_view.project_list.setCurrentRow(0)
    table = project_view.proj_table.table
    assert table.item(0, 2) is not None, "the candidate did not reach the table"
    light_foreground = table.item(0, 2).foreground().color().name()

    appearance.apply(qapp, DARK)
    dark_foreground = table.item(0, 2).foreground().color().name()

    assert light_foreground == theme.COLOR_SUCCESS
    assert dark_foreground == appearance.DARK_TOKENS[theme.COLOR_SUCCESS]
    window.deleteLater()


def test_muted_placeholder_text_follows_the_mode(qapp, state):
    window = MainWindow(state)
    placeholder = window._views["check"].verdict_view.placeholder
    appearance.apply(qapp, LIGHT)
    assert theme.COLOR_MUTED in placeholder.styleSheet()
    appearance.apply(qapp, DARK)
    assert appearance.DARK_TOKENS[theme.COLOR_MUTED] in placeholder.styleSheet()
    assert theme.COLOR_MUTED not in placeholder.styleSheet()
    window.deleteLater()


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #


def _select_theme(window: MainWindow, preference: str) -> None:
    index = next(
        i for i in range(window.theme_combo.count())
        if window.theme_combo.itemData(i) == preference
    )
    window.theme_combo.setCurrentIndex(index)


_HEX = re.compile(r"#([0-9a-f]{6})\Z", re.I)


def _rgb(color: str) -> tuple[int, int, int]:
    match = _HEX.match(color)
    assert match, f"not a 6-digit hex colour: {color!r}"
    digits = match.group(1)
    return tuple(int(digits[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore[return-value]


def _luminance(color: str) -> float:
    """WCAG relative luminance of a hex colour (0 = black, 1 = white)."""
    r, g, b = (c / 255 for c in _rgb(color))

    def channel(value: float) -> float:
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4

    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast(foreground: str, background: str) -> float:
    lighter, darker = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)
