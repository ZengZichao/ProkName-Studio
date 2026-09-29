"""Project candidates table widget for ProkName Studio.

A :class:`QTableWidget` wrapper that displays stored candidates. Scores are
edited through the rating controls in :mod:`~prokname_studio.views.project_view`,
which reloads the table after each change; the table itself stays read-only.
"""
from __future__ import annotations

from prokname.presentation import theme
from prokname.storage.model import Candidate
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import appearance, i18n

_COMPLIANT_KEY = {True: "compliant_yes", False: "compliant_no", None: "compliant_review"}
_COMPLIANT_COLOR = {
    True: theme.COLOR_SUCCESS,
    False: theme.COLOR_DANGER,
    None: theme.COLOR_WARNING,
}


class ProjectTable(QWidget):
    """Table of project candidates (read-only; rating lives in the parent view).

    Ratings are applied by :meth:`ProjectView._on_rate` via the ProjectStore;
    this widget deliberately stays read-only and emits no signals.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._candidates: list[Candidate] = []
        self._project_name: str | None = None
        self._build_ui()
        i18n.connect_language_changed(self.retranslate_ui)
        appearance.connect_changed(self.restyle)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.table = QTableWidget(0, 4)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        # the name is the primary datum — give it the elastic column
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for col in (1, 2):
            self.table.horizontalHeader().setSectionResizeMode(
                col, QHeaderView.ResizeMode.ResizeToContents
            )
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        self.retranslate_ui()

    def set_project(self, project_name: str, candidates: list[Candidate]) -> None:
        self._project_name = project_name
        self._candidates = candidates
        self._populate()

    def clear(self) -> None:
        self._candidates = []
        self._project_name = None
        self.table.setRowCount(0)

    def _populate(self) -> None:
        self.table.setRowCount(len(self._candidates))
        for i, c in enumerate(self._candidates):
            name_item = QTableWidgetItem(c.name)
            # localized label — engine enum values must not leak into the UI
            cat_item = QTableWidgetItem(i18n.category_label(c.grammatical_category))
            key = _COMPLIANT_KEY.get(c.compliant, "compliant_review")
            comp_item = QTableWidgetItem(i18n.tr(key))
            comp_item.setForeground(
                QColor(
                    appearance.token(
                        _COMPLIANT_COLOR.get(c.compliant, theme.COLOR_WARNING)
                    )
                )
            )
            score_item = QTableWidgetItem(str(c.score))
            self.table.setItem(i, 0, name_item)
            self.table.setItem(i, 1, cat_item)
            self.table.setItem(i, 2, comp_item)
            self.table.setItem(i, 3, score_item)

    def retranslate_ui(self) -> None:
        self.table.setHorizontalHeaderLabels([
            i18n.tr("proj_col_name"),
            i18n.tr("proj_col_category"),
            i18n.tr("proj_col_compliant"),
            i18n.tr("proj_col_score"),
        ])
        # re-populate to refresh compliance labels
        if self._candidates:
            self._populate()

    def restyle(self) -> None:
        """Re-colour the compliance column after a light/dark switch."""
        if self._candidates:
            self._populate()
