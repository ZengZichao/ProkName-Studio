"""Route view — dual-code (ICNP / SeqCode) routing (Phase 2).

A thin front-end over the engine's public ``route()`` API. The user selects the
data source, toggles Candidatus, and sets the ICNP occupancy status. The result
is rendered as a table of viable paths with their roles and trade-offs, plus
warnings and notes.
"""
from __future__ import annotations

from prokname.presentation import decision
from prokname.routing import route
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .. import appearance, i18n

SOURCE_ITEMS = [
    ("source_pure_culture", "pure_culture"),
    ("source_MAG", "MAG"),
    ("source_SAG", "SAG"),
    ("source_unknown", "unknown"),
]

ICNP_OCCUPIED_ITEMS = [
    ("route_icnp_auto", "auto"),
    ("route_icnp_yes", "yes"),
    ("route_icnp_no", "no"),
]


class RouteView(QWidget):
    """Dual-code routing decision-tree view."""

    def __init__(self, state, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._result = None
        # explicit label references: key → labels (no form-layout sniffing)
        self._labels: dict[str, list[QLabel]] = {}
        self._build_ui()
        self._connect_signals()
        self.retranslate_ui()
        i18n.connect_language_changed(self.retranslate_ui)
        appearance.connect_changed(self.restyle)

    # -- construction ---------------------------------------------------------

    def _label(self, key: str) -> QLabel:
        """Create a form label and remember it under ``key`` for retranslation."""
        label = QLabel()
        self._labels.setdefault(key, []).append(label)
        return label

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # --- input form ---
        form_box = QGroupBox()
        form = QFormLayout(form_box)

        self.source_combo = QComboBox()
        self.candidatus_check = QCheckBox()
        self.candidatus_check.setChecked(False)
        self.icnp_combo = QComboBox()

        self.route_btn = QPushButton()
        self.route_btn.setObjectName("primaryButton")
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.route_btn)
        form.addRow(self._label("route_source"), self.source_combo)
        form.addRow(self.candidatus_check)
        form.addRow(self._label("route_icnp_occupied"), self.icnp_combo)
        form.addRow(btn_row)

        root.addWidget(form_box)

        # --- output ---
        self.paths_label = QLabel()
        self.paths_label.setObjectName("sectionHeader")
        root.addWidget(self.paths_label)

        self.paths_table = QTableWidget(0, 3)
        self.paths_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.paths_table.setAlternatingRowColors(True)
        self.paths_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.paths_table.verticalHeader().setVisible(False)
        self.paths_table.setColumnWidth(0, 100)
        self.paths_table.setColumnWidth(1, 120)
        self.paths_table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.paths_table, 1)

        # warnings + notes
        self.info_box = QTextEdit()
        self.info_box.setReadOnly(True)
        self.info_box.setMaximumHeight(150)
        root.addWidget(self.info_box)

    def _connect_signals(self) -> None:
        self.route_btn.clicked.connect(self._on_route)

    # -- behaviour ------------------------------------------------------------

    def _on_route(self) -> None:
        source_val = self.source_combo.currentData() or "unknown"
        candidatus = self.candidatus_check.isChecked()
        icnp_val = self.icnp_combo.currentData() or "auto"
        icnp_occupied = {"auto": None, "yes": True, "no": False}.get(icnp_val)

        try:
            result = route(
                source_val,
                candidatus=candidatus,
                icnp_occupied=icnp_occupied,
            )
        except (ValueError, RuntimeError) as exc:
            QMessageBox.warning(self, i18n.tr("route_button"), str(exc))
            return

        self._result = result
        self._populate(result)
        self.retranslate_ui()

    def _populate(self, result) -> None:
        paths = result.viable_paths
        # an explicit "no viable paths" state beats a bare "(0)" counter
        if paths:
            self.paths_label.setText(
                f"{i18n.tr('route_viable_paths')} ({len(paths)})"
            )
        else:
            self.paths_label.setText(i18n.tr("route_no_paths"))
        self.paths_table.setRowCount(len(paths))
        for i, p in enumerate(paths):
            code_item = QTableWidgetItem(p.code)
            # an unmapped role must read as *unknown*, never as "default"
            # (the recommended path) — see decision.role_style
            style = decision.role_style(p.role)
            role_item = QTableWidgetItem(i18n.tr(style.key))
            role_item.setForeground(QColor(appearance.token(style.color)))
            tradeoffs_text = "\n".join(f"  • {t}" for t in p.tradeoffs)
            tradeoffs_item = QTableWidgetItem(tradeoffs_text)
            self.paths_table.setItem(i, 0, code_item)
            self.paths_table.setItem(i, 1, role_item)
            self.paths_table.setItem(i, 2, tradeoffs_item)
        # multi-line trade-off bullets need taller rows to stay readable
        self.paths_table.resizeRowsToContents()

        # warnings + notes (hidden entirely when there is nothing to say)
        lines = []
        if result.warnings:
            lines.append(f"⚠ {i18n.tr('route_warnings')}:")
            for w in result.warnings:
                lines.append(f"  • {w}")
        if result.notes:
            lines.append(f"📝 {i18n.tr('route_notes')}:")
            for n in result.notes:
                lines.append(f"  • {n}")
        self.info_box.setPlainText("\n".join(lines))
        self.info_box.setVisible(bool(lines))

    # -- helpers --------------------------------------------------------------

    def _fill_combo(self, combo: QComboBox, items) -> None:
        saved = combo.currentData()
        combo.clear()
        for label_key, value in items:
            combo.addItem(i18n.tr(label_key), value)
        for idx in range(combo.count()):
            if combo.itemData(idx) == saved:
                combo.setCurrentIndex(idx)
                break

    # -- i18n -----------------------------------------------------------------

    def retranslate_ui(self) -> None:
        self._fill_combo(self.source_combo, SOURCE_ITEMS)
        self._fill_combo(self.icnp_combo, ICNP_OCCUPIED_ITEMS)

        # every form label is re-labelled from its own stored reference — no
        # assumption about how many QFormLayouts the widget tree holds
        for key, labels in self._labels.items():
            text = i18n.tr(key)
            for label in labels:
                label.setText(text)

        self.candidatus_check.setText(i18n.tr("route_candidatus"))
        self.route_btn.setText(i18n.tr("route_button"))
        if self._result is not None:
            self.paths_label.setText(
                f"{i18n.tr('route_viable_paths')} ({len(self._result.viable_paths)})"
            )
        else:
            self.paths_label.setText(i18n.tr("route_empty"))

        self.paths_table.setHorizontalHeaderLabels([
            i18n.tr("route_col_code"),
            i18n.tr("route_col_role"),
            i18n.tr("route_col_tradeoffs"),
        ])

        # re-render result under new language
        if self._result is not None:
            self._populate(self._result)

    def restyle(self) -> None:
        """Re-colour the route-role column after a light/dark switch."""
        if self._result is not None:
            self._populate(self._result)
