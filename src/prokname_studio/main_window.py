"""ProkName Studio main window.

Owns the navigation (QListWidget + QStackedWidget), the language and appearance
switchers in the toolbar, and the menu bar. Views are constructed once and
notified of language changes via the i18n ``languageChanged`` signal and of
light/dark changes via the appearance ``appearanceChanged`` signal — each view
re-translates and re-resolves the colours it paints itself.
"""
from __future__ import annotations

from prokname import DISCLAIMER
from prokname import __version__ as engine_version
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMenuBar,
    QMessageBox,
    QStackedWidget,
    QStatusBar,
    QToolBar,
    QWidget,
)

from . import __version__, appearance, i18n
from .state import StudioState
from .views import CheckView, DataView, GenerateView, ProjectView, RouteView

# nav_key -> (label i18n key, view class)
_NAV = [
    ("generate", "nav_generate", GenerateView),
    ("route", "nav_route", RouteView),
    ("check", "nav_check", CheckView),
    ("project", "nav_project", ProjectView),
    ("data", "nav_data", DataView),
]

_LANG_ITEMS = [("lang_auto", "auto"), ("中文", "zh"), ("English", "en")]

# (i18n label key, preference passed to appearance.set_preference)
_THEME_ITEMS = [
    ("theme_auto", appearance.AUTO),
    ("theme_light", appearance.LIGHT),
    ("theme_dark", appearance.DARK),
]


class MainWindow(QMainWindow):
    """Top-level Studio window."""

    def __init__(self, state: StudioState) -> None:
        super().__init__()
        self._state = state
        self._views: dict[str, QWidget] = {}
        self._build_ui()
        self._connect_signals()
        self.retranslate_ui()
        i18n.connect_language_changed(self.retranslate_ui)

    # -- construction ---------------------------------------------------------

    def _build_ui(self) -> None:
        self.setMinimumSize(880, 620)
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        self.nav = QListWidget()
        self.nav.setObjectName("navList")
        self.nav.setFixedWidth(170)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setUniformItemSizes(True)
        root.addWidget(self.nav)

        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        # populate nav + stack — each view gets the shared StudioState
        for key, _label_key, factory in _NAV:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, key)
            self.nav.addItem(item)
            view = factory(self._state)
            self._views[key] = view
            self.stack.addWidget(view)
        self.nav.setCurrentRow(0)

        # language + appearance toolbar
        self.lang_bar = QToolBar()
        self.lang_bar.setMovable(False)  # the switcher bar is chrome, not a palette
        self.lang_label = QLabel()
        self.lang_combo = QComboBox()
        for _label, value in _LANG_ITEMS:
            self.lang_combo.addItem(i18n.tr(_label), value)
        self.lang_bar.addWidget(self.lang_label)
        self.lang_bar.addWidget(self.lang_combo)
        self.lang_bar.addSeparator()

        self.theme_label = QLabel()
        self.theme_combo = QComboBox()
        for _label, value in _THEME_ITEMS:
            self.theme_combo.addItem(i18n.tr(_label), value)
        self._select_theme(appearance.current_preference())
        self.lang_bar.addWidget(self.theme_label)
        self.lang_bar.addWidget(self.theme_combo)
        self.lang_bar.addSeparator()

        self.subtitle_label = QLabel()
        # one line — a wrapping label would pump the toolbar height up and down
        # while the window is resized
        self.subtitle_label.setWordWrap(False)
        self.lang_bar.addWidget(self.subtitle_label)
        self.addToolBar(self.lang_bar)

        # menus
        self.menu_bar = QMenuBar()
        self.setMenuBar(self.menu_bar)
        self.menu_file = self.menu_bar.addMenu("")
        self.act_exit = self.menu_file.addAction("")
        self.menu_help = self.menu_bar.addMenu("")
        self.act_about = self.menu_help.addAction("")
        # native niceties: Cmd+Q to quit, About moved into the app menu on macOS
        self.act_exit.setShortcut(QKeySequence.StandardKey.Quit)
        self.act_exit.setMenuRole(QAction.MenuRole.QuitRole)
        self.act_about.setMenuRole(QAction.MenuRole.AboutRole)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

    def _connect_signals(self) -> None:
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.lang_combo.currentIndexChanged.connect(self._on_language_changed)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self.act_exit.triggered.connect(self.close)
        self.act_about.triggered.connect(self._show_about)

    # -- behaviour ------------------------------------------------------------

    def _on_language_changed(self) -> None:
        value = self.lang_combo.currentData()
        if value == "auto":
            i18n.set_language_auto()
        else:
            i18n.set_language(value)

    def _on_theme_changed(self) -> None:
        value = self.theme_combo.currentData()
        if value in appearance.PREFERENCES:
            appearance.set_preference(QApplication.instance(), value)

    def _select_theme(self, preference: str) -> None:
        self.theme_combo.blockSignals(True)
        for idx in range(self.theme_combo.count()):
            if self.theme_combo.itemData(idx) == preference:
                self.theme_combo.setCurrentIndex(idx)
                break
        self.theme_combo.blockSignals(False)

    def _show_about(self) -> None:
        text = (
            f"ProkName Studio {__version__}\n"
            f"prokname v{engine_version}\n\n"
            f"{DISCLAIMER}"
        )
        QMessageBox.about(self, i18n.tr("menu_about"), text)

    # -- i18n -----------------------------------------------------------------

    def retranslate_ui(self) -> None:
        self.setWindowTitle(i18n.tr("app_title"))

        for i in range(self.nav.count()):
            item = self.nav.item(i)
            key = item.data(Qt.ItemDataRole.UserRole)
            label_key = next(lk for k, lk, _ in _NAV if k == key)
            item.setText(i18n.tr(label_key))

        self.lang_label.setText(i18n.tr("lang"))
        self.subtitle_label.setText(i18n.tr("app_subtitle"))

        # re-label language combo, preserving selection — block signals
        # to prevent currentIndexChanged from re-triggering set_language
        # (which would reset the language and create an infinite loop).
        saved = self.lang_combo.currentData()
        self.lang_combo.blockSignals(True)
        self.lang_combo.clear()
        for label, value in _LANG_ITEMS:
            self.lang_combo.addItem(i18n.tr(label), value)
        for idx in range(self.lang_combo.count()):
            if self.lang_combo.itemData(idx) == saved:
                self.lang_combo.setCurrentIndex(idx)
                break
        self.lang_combo.blockSignals(False)

        # the same discipline for the appearance combo: its items are translatable
        # ("跟随系统"), so a language switch rebuilds them, and rebuilding must not
        # look like the user asked for a different theme.
        self.theme_label.setText(i18n.tr("theme"))
        saved_theme = self.theme_combo.currentData()
        self.theme_combo.blockSignals(True)
        self.theme_combo.clear()
        for label, value in _THEME_ITEMS:
            self.theme_combo.addItem(i18n.tr(label), value)
        for idx in range(self.theme_combo.count()):
            if self.theme_combo.itemData(idx) == saved_theme:
                self.theme_combo.setCurrentIndex(idx)
                break
        self.theme_combo.blockSignals(False)

        self.menu_file.setTitle(i18n.tr("menu_file"))
        self.menu_help.setTitle(i18n.tr("menu_help"))
        self.act_exit.setText(i18n.tr("menu_exit"))
        self.act_about.setText(i18n.tr("menu_about"))
        self.status_bar.showMessage(
            f"prokname v{engine_version} · {i18n.tr('app_title')}"
        )
