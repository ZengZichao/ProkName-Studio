"""Verdict visualisation widget for ProkName Studio.

Renders a :class:`~prokname.dedup.model.CheckReport` verdict as a colored badge
and maps each :class:`~prokname.dedup.model.SourceResult` to a row in a table.
This is a pure view — it never re-checks anything, only visualises the engine's
own output. Until the first report arrives it shows a muted placeholder so the
section never renders as a cluster of empty tables.
"""
from __future__ import annotations

from prokname.dedup.model import Verdict
from prokname.presentation import decision, theme
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import appearance, i18n

# found* statuses are the risky ones (red), not_found is safe (green),
# everything else (unavailable/blocked) is caution (orange).
_STATUS_COLOR = {"found": theme.COLOR_DANGER, "not_found": theme.COLOR_SUCCESS}


class VerdictView(QWidget):
    """Verdict badge + sources table + near-match table for a check report."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._report = None
        self._build_ui()
        self._apply_styles()
        self._show_placeholder()
        i18n.connect_language_changed(self.retranslate_ui)
        appearance.connect_changed(self.restyle)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # empty-state placeholder (visible until the first report arrives)
        self.placeholder = QLabel()
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setWordWrap(True)
        layout.addWidget(self.placeholder)

        # verdict badge — stretches either side so it reads as a pill, not a banner
        badge_row = QHBoxLayout()
        badge_row.addStretch(1)
        self.verdict_label = QLabel()
        self.verdict_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = self.verdict_label.font()
        font.setBold(True)
        font.setPointSize(14)
        self.verdict_label.setFont(font)
        badge_row.addWidget(self.verdict_label)
        badge_row.addStretch(1)
        layout.addLayout(badge_row)

        # blocked note
        self.blocked_note = QLabel()
        self.blocked_note.setWordWrap(True)
        self.blocked_note.hide()
        layout.addWidget(self.blocked_note)

        # sources table
        self.sources_label = QLabel()
        self.sources_label.setObjectName("sectionHeader")
        layout.addWidget(self.sources_label)
        self.sources_table = QTableWidget(0, 4)
        self._style_table(self.sources_table)
        layout.addWidget(self.sources_table)

        # near matches table
        self.near_label = QLabel()
        self.near_label.setObjectName("sectionHeader")
        layout.addWidget(self.near_label)
        self.near_table = QTableWidget(0, 3)
        self._style_table(self.near_table)
        layout.addWidget(self.near_table)
        # muted "no near matches" hint — an empty table must not read as
        # "the scan has not run yet"
        self.near_empty = QLabel()
        self.near_empty.hide()
        layout.addWidget(self.near_empty)

        # warnings
        self.warnings_label = QLabel()
        self.warnings_label.setWordWrap(True)
        layout.addWidget(self.warnings_label)

    def _apply_styles(self) -> None:
        """(Re-)resolve the colours this widget states in a widget stylesheet.

        ``setStyleSheet`` freezes the hue it was handed, so these are the labels
        that would otherwise stay dark-grey-on-dark after a light/dark switch.
        """
        muted = appearance.token(theme.COLOR_MUTED)
        self.placeholder.setStyleSheet(f"color: {muted}; padding: 24px;")
        self.near_empty.setStyleSheet(f"color: {muted}; padding: 4px;")
        self.blocked_note.setStyleSheet(
            f"color: {appearance.token(theme.COLOR_DANGER_BRIGHT)}; font-style: italic;"
        )
        self.warnings_label.setStyleSheet(
            f"color: {appearance.token(theme.COLOR_WARNING)};"
        )

    @staticmethod
    def _style_table(table: QTableWidget) -> None:
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setWordWrap(False)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)

    def set_report(self, report) -> None:
        """Populate from an engine :class:`CheckReport`."""
        self._report = report
        self._populate(report)
        self.retranslate_ui()

    def clear(self) -> None:
        self._report = None
        self._show_placeholder()

    def restyle(self) -> None:
        """Re-paint what this widget owns after a light/dark switch.

        The report is re-rendered rather than re-checked: the numbers on screen
        are the engine's answer, and a theme change must not touch them.
        """
        self._apply_styles()
        if self._report is not None:
            self._populate(self._report)

    def _show_placeholder(self) -> None:
        """Muted hint instead of a stack of empty tables."""
        self.placeholder.setText(i18n.tr("check_empty"))
        self.placeholder.show()
        self.verdict_label.hide()
        self.blocked_note.hide()
        self.sources_label.hide()
        self.sources_table.hide()
        self.near_label.hide()
        self.near_table.hide()
        self.near_empty.hide()
        self.warnings_label.hide()

    def _show_report_widgets(self) -> None:
        self.placeholder.hide()
        self.verdict_label.show()
        self.sources_label.show()
        self.sources_table.show()
        self.near_label.show()
        self.near_table.show()

    def _render_verdict_badge(self, verdict: Verdict | None) -> None:
        """Always rewrite the badge — text *and* colour — for this verdict.

        A report without a verdict (or with a verdict this UI has no mapping
        for) renders as a neutral "unknown" pill: it must never leave the
        previous check's wording on screen, and it must never fall back to the
        most optimistic label.
        """
        style = decision.verdict_style(verdict)
        self.verdict_label.setText(i18n.tr(style.key))
        weight = "bold" if verdict == Verdict.BLOCKED else "600"
        self.verdict_label.setStyleSheet(
            appearance.badge_css(style.color, weight=weight)
        )

    def _populate(self, report) -> None:
        self._show_report_widgets()

        # verdict badge
        verdict = report.verdict
        self._render_verdict_badge(verdict)

        # blocked note
        self.blocked_note.setVisible(verdict == Verdict.BLOCKED)
        self.blocked_note.setText(i18n.tr("check_blocked_note"))

        # sources table
        self.sources_table.setRowCount(len(report.sources))
        for i, s in enumerate(report.sources):
            name_item = QTableWidgetItem(s.name)
            tier_item = QTableWidgetItem(s.tier)
            status_item = QTableWidgetItem(s.status)
            detail_item = QTableWidgetItem(s.detail or "-")
            detail_item.setToolTip(s.detail or "")
            color = next(
                (c for prefix, c in _STATUS_COLOR.items() if s.status.startswith(prefix)),
                theme.COLOR_WARNING,
            )
            status_item.setForeground(QColor(appearance.token(color)))
            self.sources_table.setItem(i, 0, name_item)
            self.sources_table.setItem(i, 1, tier_item)
            self.sources_table.setItem(i, 2, status_item)
            self.sources_table.setItem(i, 3, detail_item)

        # near matches table
        matches = report.near_matches or []
        self.near_table.setRowCount(len(matches))
        for i, m in enumerate(matches):
            self.near_table.setItem(i, 0, QTableWidgetItem(m.corpus_name))
            self.near_table.setItem(i, 1, QTableWidgetItem(str(m.distance)))
            self.near_table.setItem(i, 2, QTableWidgetItem(m.source))
        self.near_empty.setVisible(not matches)
        self.near_empty.setText(i18n.tr("check_no_matches"))

        # warnings
        if report.warnings:
            header = i18n.tr("check_warnings")
            self.warnings_label.setText(
                f"{header}:\n" + "\n".join(f"⚠ {w}" for w in report.warnings)
            )
            self.warnings_label.show()
        else:
            self.warnings_label.hide()

    def retranslate_ui(self) -> None:
        self.placeholder.setText(i18n.tr("check_empty"))
        self.blocked_note.setText(i18n.tr("check_blocked_note"))
        self.near_empty.setText(i18n.tr("check_no_matches"))
        self.sources_label.setText(i18n.tr("check_sources"))
        self.sources_table.setHorizontalHeaderLabels([
            i18n.tr("check_col_source"),
            i18n.tr("check_col_tier"),
            i18n.tr("check_col_status"),
            i18n.tr("check_col_detail"),
        ])
        self.near_label.setText(i18n.tr("check_near_matches"))
        self.near_table.setHorizontalHeaderLabels([
            i18n.tr("check_col_corpus"),
            i18n.tr("check_col_distance"),
            i18n.tr("check_col_nm_source"),
        ])
        # re-render report content (verdict text, warnings) under the new language
        if self._report is not None:
            self._render_verdict_badge(self._report.verdict)
            if self._report.warnings:
                header = i18n.tr("check_warnings")
                self.warnings_label.setText(
                    f"{header}:\n"
                    + "\n".join(f"⚠ {w}" for w in self._report.warnings)
                )
