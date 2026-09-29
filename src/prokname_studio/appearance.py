"""Light / dark appearance for ProkName Studio.

The engine's :mod:`prokname.presentation.theme` owns the *semantic* colour
tokens (a conflict is red, a clean verdict is green). Which hue a semantic token
takes on screen is not a property of the verdict — it is a property of the
surface it is painted on — so that decision lives here: Studio owns how it looks.

Two preferences exist, and ``auto`` is the third that resolves to one of them:

``light`` / ``dark``
    an explicit choice, written to :class:`QSettings` so it survives a restart
    instead of being a cosmetic change that vanishes on the next launch.
``auto`` (the default)
    follow the desktop's colour scheme, and re-apply the moment the user changes
    it while Studio is open.

Switching is live: :func:`apply` re-pins the Fusion palette, swaps the
application stylesheet, and emits ``appearanceChanged`` so every widget
re-resolves the colours it paints inline (badges, table foregrounds, muted
placeholders). Widgets that only inherit from the palette need no help.

Both looks are one :class:`Spec` of colours each and one shared
``string.Template`` stylesheet over it, so light and dark cannot drift apart the
way two hand-maintained stylesheets would.
"""
from __future__ import annotations

import string
from typing import NamedTuple

from PySide6.QtCore import QObject, QSettings, Qt, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

AUTO = "auto"
LIGHT = "light"
DARK = "dark"
PREFERENCES: tuple[str, ...] = (AUTO, LIGHT, DARK)

_SETTINGS_ORGANIZATION = "ProkName"
_SETTINGS_APPLICATION = "ProkName Studio"
_SETTINGS_KEY = "ui/theme"

#: The ``QSettings`` scope preferences are stored in; ``app.py`` sets it on the
#: application so what is written and what is read back are the same scope.
ORGANIZATION = _SETTINGS_ORGANIZATION
APPLICATION = _SETTINGS_APPLICATION

DEFAULT_PREFERENCE = AUTO

#: Set by :func:`use_settings`; ``None`` means "the native store".
_STORED_SETTINGS: QSettings | None = None


class Spec(NamedTuple):
    """Every surface/ink colour one appearance mode is built from."""

    window: str
    base: str
    alternate_base: str
    text: str
    disabled: str
    button: str
    button_text: str
    tooltip_base: str
    tooltip_text: str
    highlight: str
    highlight_text: str
    placeholder: str
    border: str
    border_strong: str
    header_background: str
    header_text: str
    gridline: str
    selection_background: str
    selection_text: str
    nav_text: str
    nav_hover: str
    primary: str
    primary_hover: str
    primary_pressed: str
    primary_disabled: str
    primary_disabled_text: str
    status_text: str


LIGHT_SPEC = Spec(
    window="#ffffff",
    base="#ffffff",
    alternate_base="#f6f8fa",
    text="#2c3e50",
    disabled="#a6adb3",
    button="#f4f6f8",
    button_text="#2c3e50",
    tooltip_base="#ffffdc",
    tooltip_text="#2c3e50",
    highlight="#2980b9",
    highlight_text="#ffffff",
    placeholder="#9aa5af",
    border="#dfe4e9",
    border_strong="#d3dae0",
    header_background="#f0f3f6",
    header_text="#55606b",
    gridline="#e6eaee",
    selection_background="#d8e9f6",
    selection_text="#1b2733",
    nav_text="#2c3e50",
    nav_hover="#e8eff5",
    primary="#2980b9",
    primary_hover="#2e8bc9",
    primary_pressed="#256d9c",
    primary_disabled="#b9cddb",
    primary_disabled_text="#f2f5f7",
    status_text="#7f8c8d",
)

#: A dark surface lifts every hue: the light palette's ``#c0392b`` is unreadable
#: as ink on ``#1e2327``, and a solid ``#27ae60`` pill floats badly on it.
DARK_SPEC = Spec(
    window="#2b3237",
    base="#1e2327",
    alternate_base="#262c31",
    text="#e6ebef",
    disabled="#7c868f",
    button="#333b41",
    button_text="#e6ebef",
    tooltip_base="#3a4045",
    tooltip_text="#e6ebef",
    highlight="#2f6c99",
    highlight_text="#ffffff",
    placeholder="#8b97a1",
    border="#3a4249",
    border_strong="#454e55",
    header_background="#2a3137",
    header_text="#aebac4",
    gridline="#3a4249",
    selection_background="#2f4d63",
    selection_text="#eaf3fa",
    nav_text="#dbe3ea",
    nav_hover="#39434a",
    primary="#2e8bc9",
    primary_hover="#3d9bd9",
    primary_pressed="#2678ab",
    primary_disabled="#3f4a52",
    primary_disabled_text="#8b97a1",
    status_text="#9aa5af",
)

SPECS: dict[str, Spec] = {LIGHT: LIGHT_SPEC, DARK: DARK_SPEC}

#: Semantic token → its dark-surface spelling. A token missing from this map is
#: passed through unchanged: it renders in its light hue, which is a legible
#: complaint, unlike an unmapped token becoming no colour at all.
DARK_TOKENS: dict[str, str] = {
    "#27ae60": "#3dd68c",  # success
    "#f39c12": "#f5b041",  # warning
    "#c0392b": "#e0685c",  # danger
    "#e74c3c": "#ff8a7a",  # danger, bright (BLOCKED)
    "#2980b9": "#5cb3e8",  # info
    "#7f8c8d": "#9aa5af",  # muted / unknown
    "#2c3e50": "#e6ebef",  # text
}

_QSS_TEMPLATE = string.Template("""
QListWidget#navList {
    background: transparent;
    border: none;
    outline: 0;
    padding: 6px 0;
}
QListWidget#navList::item {
    padding: 9px 14px;
    margin: 2px 8px;
    border-radius: 6px;
    color: $nav_text;
}
QListWidget#navList::item:selected {
    background: $primary;
    color: $highlight_text;
}
QListWidget#navList::item:hover:!selected {
    background: $nav_hover;
}

QLabel#sectionHeader {
    font-weight: 600;
    font-size: 13px;
    color: $text;
    padding-top: 2px;
}

QTableWidget, QTreeWidget {
    alternate-background-color: $alternate_base;
    gridline-color: $gridline;
    selection-background-color: $selection_background;
    selection-color: $selection_text;
    border: 1px solid $border;
    border-radius: 4px;
}
QHeaderView::section {
    background: $header_background;
    color: $header_text;
    padding: 5px 8px;
    border: none;
    border-right: 1px solid $border;
    border-bottom: 1px solid $border_strong;
    font-weight: 600;
}

QGroupBox {
    font-weight: 600;
}

QPushButton#primaryButton {
    background: $primary;
    color: $highlight_text;
    font-weight: 600;
    padding: 6px 20px;
    border: none;
    border-radius: 5px;
}
QPushButton#primaryButton:hover {
    background: $primary_hover;
}
QPushButton#primaryButton:pressed {
    background: $primary_pressed;
}
QPushButton#primaryButton:disabled {
    background: $primary_disabled;
    color: $primary_disabled_text;
}

QStatusBar {
    color: $status_text;
}
""")

QSS: dict[str, str] = {mode: _QSS_TEMPLATE.substitute(spec._asdict())
                       for mode, spec in SPECS.items()}


def current_mode() -> str:
    """The mode Studio is painted in right now (``light`` or ``dark``)."""
    return _manager().mode


def current_preference() -> str:
    """The preference the user (or the command line) last asked for."""
    return _manager().preference


def spec(mode: str | None = None) -> Spec:
    """The :class:`Spec` of ``mode`` — by default, the mode Studio is in."""
    return SPECS[mode or current_mode()]


def resolve(preference: str, system_prefers_dark: bool) -> str:
    """The mode ``preference`` resolves to, given the desktop colour scheme.

    An unknown preference is not guessed into light or dark: ``auto`` is the
    preference that defers to the desktop, so it is also the fail-safe.
    """
    if preference in (LIGHT, DARK):
        return preference
    return DARK if system_prefers_dark else LIGHT


def system_prefers_dark() -> bool:
    """The desktop colour scheme, as Qt reports it.

    ``Unknown`` counts as dark-on-capable-platforms-no: it is reported when Qt
    cannot tell, and the Studio palette then stays where it started — the light
    look every screenshot and every contrast check was made against.
    """
    app = QApplication.instance()
    if app is None:
        return False
    return app.styleHints().colorScheme() is Qt.ColorScheme.Dark


def token(color: str, mode: str | None = None) -> str:
    """``color`` as it should be painted on the surface of ``mode``.

    The engine's semantic tokens are specified against a light surface; on a
    dark one the same hue is too dark to read as ink, so it is lifted to its
    ``DARK_TOKENS`` spelling.
    """
    if (mode or current_mode()) != DARK:
        return color
    return DARK_TOKENS.get(color.lower(), color)


def badge_css(color: str, *, weight: str = "600", mode: str | None = None) -> str:
    """CSS for a verdict / route-role pill.

    Light: the token fills the pill and the label is white — the look the token
    palette was designed against. Dark: a solid saturated pill floats badly on a
    dark window, so the fill becomes a tint of the same hue, the label takes the
    lifted token, and a border keeps the pill's edge legible.
    """
    active = mode or current_mode()
    base = "padding: 6px 22px; border-radius: 6px;"
    if active != DARK:
        return f"{base}background-color: {color}; color: #ffffff; font-weight: {weight};"
    lifted = token(color, DARK)
    return (
        f"{base}background-color: {_rgba(lifted, 0.22)}; color: {lifted};"
        f" border: 1px solid {_rgba(lifted, 0.5)}; font-weight: {weight};"
    )


def _rgba(color: str, alpha: float) -> str:
    rgb = QColor(color)
    return f"rgba({rgb.red()}, {rgb.green()}, {rgb.blue()}, {alpha:g})"


def load_preference(settings: QSettings | None = None) -> str:
    """The stored preference, or ``auto`` when nothing valid is stored."""
    value = (settings or _settings()).value(_SETTINGS_KEY, DEFAULT_PREFERENCE)
    return value if value in PREFERENCES else DEFAULT_PREFERENCE


def save_preference(value: str, settings: QSettings | None = None) -> None:
    """Remember ``value`` — an unusable spelling stores ``auto``, not junk."""
    stored = value if value in PREFERENCES else DEFAULT_PREFERENCE
    (settings or _settings()).setValue(_SETTINGS_KEY, stored)


def _settings() -> QSettings:
    if _STORED_SETTINGS is not None:
        return _STORED_SETTINGS
    return QSettings(_SETTINGS_ORGANIZATION, _SETTINGS_APPLICATION)


def use_settings(settings: QSettings | None) -> None:
    """Point the preference store at ``settings`` (``None`` restores the default).

    ``QSettings(organization, application)`` is a *native* store: on macOS that is
    ``~/Library/Preferences/com.prokname.ProkName Studio.plist``, and on Windows
    the registry. A test suite that switches the theme therefore writes the
    developer's own machine, and a green run stops meaning anything about the
    checked-out state. This hook lets the suite aim at a throwaway ini file.
    """
    global _STORED_SETTINGS
    _STORED_SETTINGS = settings


class _AppearanceManager(QObject):
    """The preference, the resolved mode, and the signal that ties them to widgets."""

    appearanceChanged = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.preference = DEFAULT_PREFERENCE
        self.mode = LIGHT

    def set(self, app: QApplication, preference: str) -> str:
        self.preference = preference if preference in PREFERENCES else DEFAULT_PREFERENCE
        self.mode = resolve(self.preference, system_prefers_dark())
        _apply_palette(app, SPECS[self.mode])
        app.setStyleSheet(QSS[self.mode])
        self.appearanceChanged.emit(self.mode)
        return self.mode


class _DesktopWatcher(QObject):
    """Re-applies ``auto`` when the desktop switches between colour schemes.

    Parented to the application and created at most once per application, so
    repeated :func:`install` calls cannot stack duplicate connections and the
    handler cannot outlive the app it reads ``styleHints()`` from.
    """

    def __init__(self, app: QApplication) -> None:
        super().__init__(app)
        self._app = app
        app.styleHints().colorSchemeChanged.connect(self._on_scheme_changed)

    def _on_scheme_changed(self, *_args) -> None:
        if _manager().preference == AUTO:
            _manager().set(self._app, AUTO)


def install(app: QApplication, preference: str | None = None) -> str:
    """Paint ``app`` and start following the desktop in ``auto`` mode.

    ``None`` means "whatever the user last chose": the choice is read from
    :class:`QSettings`. A preference passed in (the ``--theme`` flag) is applied
    for this run only — a per-launch flag must not silently become permanent.
    """
    chosen = load_preference() if preference is None else preference
    mode = _manager().set(app, chosen)
    _watch_desktop(app)
    return mode


def set_preference(app: QApplication, preference: str) -> str:
    """Change the preference, repaint, and remember it."""
    mode = _manager().set(app, preference)
    save_preference(preference)
    _watch_desktop(app)
    return mode


def apply(app: QApplication, preference: str) -> str:
    """Alias of :func:`set_preference` without the persistence.

    Kept because the engine's ``presentation.theme`` exposed ``apply()``, and the
    test that pins "Studio paints Fusion" reads better against the same verb.
    """
    mode = _manager().set(app, preference)
    _watch_desktop(app)
    return mode


def connect_changed(slot) -> None:
    """Subscribe ``slot`` to ``appearanceChanged(mode)``."""
    _manager().appearanceChanged.connect(slot)


def _watch_desktop(app: QApplication) -> None:
    if getattr(app, "_prokname_desktop_watcher", None) is None:
        app._prokname_desktop_watcher = _DesktopWatcher(app)


_MANAGER: _AppearanceManager | None = None


def _manager() -> _AppearanceManager:
    global _MANAGER
    if _MANAGER is None:
        _MANAGER = _AppearanceManager()
    return _MANAGER


def _apply_palette(app: QApplication, appearance: Spec) -> None:
    """Pin the Fusion palette to ``appearance`` (idempotent)."""
    if app.style().objectName().lower() != "fusion":
        app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(appearance.window))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(appearance.text))
    palette.setColor(QPalette.ColorRole.Base, QColor(appearance.base))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(appearance.alternate_base))
    palette.setColor(QPalette.ColorRole.Text, QColor(appearance.text))
    palette.setColor(QPalette.ColorRole.Button, QColor(appearance.button))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(appearance.button_text))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(appearance.tooltip_base))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(appearance.tooltip_text))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(appearance.highlight))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(appearance.highlight_text))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(appearance.placeholder))
    for role in (
        QPalette.ColorRole.Text,
        QPalette.ColorRole.WindowText,
        QPalette.ColorRole.ButtonText,
    ):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(appearance.disabled))
    app.setPalette(palette)


__all__ = [
    "APPLICATION",
    "AUTO",
    "DARK",
    "LIGHT",
    "ORGANIZATION",
    "PREFERENCES",
    "Spec",
    "apply",
    "badge_css",
    "connect_changed",
    "current_mode",
    "current_preference",
    "install",
    "load_preference",
    "resolve",
    "save_preference",
    "set_preference",
    "spec",
    "system_prefers_dark",
    "token",
    "use_settings",
]
