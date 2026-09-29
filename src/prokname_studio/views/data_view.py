"""Data assets status view (Phase 4).

A thin front-end over the engine's ``data_assets.asset_status()`` API. Displays
a table of all packaged data files (rules.json, genus_gender.json, etc.) with
their version and gating/expert-review status, giving users transparency into
the engine's coverage boundary.
"""
from __future__ import annotations

from prokname.engine import data as data_assets
from PySide6.QtWidgets import (
    QAbstractItemView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import i18n

_STATUS_PREVIEW_CHARS = 56


def _truncate(text: str, limit: int = _STATUS_PREVIEW_CHARS) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


class DataView(QWidget):
    """Data assets status view."""

    def __init__(self, state, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._status: dict = {}
        self._build_ui()
        self._load_data()
        self.retranslate_ui()
        i18n.connect_language_changed(self.retranslate_ui)

    # -- construction ---------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.title_label = QLabel()
        self.title_label.setObjectName("sectionHeader")
        layout.addWidget(self.title_label)

        self.table = QTableWidget(0, 3)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        self.empty_label = QLabel()
        self.empty_label.hide()
        layout.addWidget(self.empty_label)

    def _load_data(self) -> None:
        try:
            self._status = data_assets.asset_status()
        except Exception:
            self._status = {}
        self._populate()

    def _populate(self) -> None:
        if not self._status:
            self.table.setRowCount(0)
            self.empty_label.show()
            return
        self.empty_label.hide()
        self.table.setRowCount(len(self._status))
        for i, (filename, info) in enumerate(sorted(self._status.items())):
            self.table.setItem(i, 0, QTableWidgetItem(filename))
            self.table.setItem(i, 1, QTableWidgetItem(info.get("version") or "-"))
            # status notes run long — keep the cell scannable, full text on hover
            note = info.get("status") or "-"
            cell = QTableWidgetItem(_truncate(note))
            cell.setToolTip(note)
            self.table.setItem(i, 2, cell)

    def retranslate_ui(self) -> None:
        self.title_label.setText(i18n.tr("data_title"))
        self.empty_label.setText(i18n.tr("data_empty"))
        self.table.setHorizontalHeaderLabels([
            i18n.tr("data_col_file"),
            i18n.tr("data_col_version"),
            i18n.tr("data_col_status"),
        ])
