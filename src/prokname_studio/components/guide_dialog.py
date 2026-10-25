"""Getting-started guide dialog for ProkName Studio.

A step-by-step new-user walkthrough: one page of prose per screen of the app,
plus an overview and a set of interface tips. Each step tied to a real page
carries a "go to this page" button, so reading the guide and acting on it are
the same gesture — that is the guided part of the guide.

The dialog is deliberately never shown on its own: MainWindow constructs it
lazily when the toolbar button or the Help-menu entry is clicked, and shows it
modeless so the user can follow along on the real pages underneath.
"""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QListWidget,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from .. import i18n

# (nav key the step can jump to — None for steps that own no page — and the
# i18n keys of the step's title and body). The order follows the recommended
# workflow (check → generate → route → project), not the nav's own order.
_STEPS: list[tuple[str | None, str, str]] = [
    (None, "guide_step_overview", "guide_content_overview"),
    ("check", "guide_step_check", "guide_content_check"),
    ("generate", "guide_step_generate", "guide_content_generate"),
    ("route", "guide_step_route", "guide_content_route"),
    ("project", "guide_step_project", "guide_content_project"),
    ("data", "guide_step_data", "guide_content_data"),
    (None, "guide_step_tips", "guide_content_tips"),
]


class GuideDialog(QDialog):
    """Modeless, lazily created new-user guide."""

    def __init__(
        self,
        go_to_page: Callable[[str], None],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._go_to_page = go_to_page
        self._build_ui()
        self._connect_signals()
        self.retranslate_ui()
        i18n.connect_language_changed(self.retranslate_ui)

    # -- construction ---------------------------------------------------------

    def _build_ui(self) -> None:
        self.resize(760, 480)
        root = QVBoxLayout(self)

        body = QHBoxLayout()
        self.step_list = QListWidget()
        self.step_list.setMaximumWidth(200)
        body.addWidget(self.step_list)

        self.text = QTextBrowser()
        self.text.setOpenExternalLinks(False)
        body.addWidget(self.text, 1)
        root.addLayout(body, 1)

        btn_row = QHBoxLayout()
        self.prev_btn = QPushButton()
        self.next_btn = QPushButton()
        self.go_btn = QPushButton()
        self.close_btn = QPushButton()
        btn_row.addWidget(self.prev_btn)
        btn_row.addWidget(self.next_btn)
        btn_row.addStretch(1)
        btn_row.addWidget(self.go_btn)
        btn_row.addWidget(self.close_btn)
        root.addLayout(btn_row)

    def _connect_signals(self) -> None:
        self.step_list.currentRowChanged.connect(self._on_step)
        self.prev_btn.clicked.connect(lambda: self._move(-1))
        self.next_btn.clicked.connect(lambda: self._move(1))
        self.go_btn.clicked.connect(self._go_to_current_page)
        self.close_btn.clicked.connect(self.close)

    # -- behaviour ------------------------------------------------------------

    def _move(self, delta: int) -> None:
        row = self.step_list.currentRow() + delta
        if 0 <= row < self.step_list.count():
            self.step_list.setCurrentRow(row)

    def _on_step(self, row: int) -> None:
        if not 0 <= row < len(_STEPS):
            return
        page_key, _title_key, content_key = _STEPS[row]
        self.text.setHtml(i18n.tr(content_key))
        self.prev_btn.setEnabled(row > 0)
        self.next_btn.setEnabled(row < len(_STEPS) - 1)
        # steps that own no page have nowhere to navigate to
        self.go_btn.setEnabled(page_key is not None)

    def _go_to_current_page(self) -> None:
        row = self.step_list.currentRow()
        if not 0 <= row < len(_STEPS) or _STEPS[row][0] is None:
            return
        if self._go_to_page is not None:
            self._go_to_page(_STEPS[row][0])

    # -- i18n -----------------------------------------------------------------

    def retranslate_ui(self) -> None:
        self.setWindowTitle(i18n.tr("guide_title"))

        # rebuild the step list around the current row; blocking signals keeps
        # the rebuild from looking like the user picked a different step
        row = max(self.step_list.currentRow(), 0)
        self.step_list.blockSignals(True)
        self.step_list.clear()
        for _page_key, title_key, _content_key in _STEPS:
            self.step_list.addItem(i18n.tr(title_key))
        self.step_list.setCurrentRow(row)
        self.step_list.blockSignals(False)

        self.prev_btn.setText(i18n.tr("guide_prev"))
        self.next_btn.setText(i18n.tr("guide_next"))
        self.go_btn.setText(i18n.tr("guide_go"))
        self.close_btn.setText(i18n.tr("guide_close"))

        # the blocked rebuild fired no currentRowChanged, so the body and the
        # button states (enabled/disabled) have to be refreshed for this row
        self._on_step(row)
