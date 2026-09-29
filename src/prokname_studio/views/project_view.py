"""Project management view (Phase 3).

A thin front-end over the engine's ``ProjectStore`` API. Lists projects, creates
new ones with metadata, displays candidates in a table with rating controls,
and exports to JSON / CSV / Markdown. Interacts with the Generate view via
``StudioState``: adding a candidate from Generate emits ``projects_changed``
and this view reloads its list; ``StudioState.current_project`` mirrors the
selection here.
"""
from __future__ import annotations

from pathlib import Path

from prokname._atomic import atomic_write_text
from prokname.presentation import theme
from prokname.storage import ProjectLoadError, ProjectStore
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .. import appearance, i18n
from ..components.project_table import ProjectTable

# (i18n key or None for the literal value, value stored in the project metadata)
DATA_SOURCE_ITEMS = [
    ("proj_meta_any", ""),
    ("source_pure_culture", "pure_culture"),
    ("source_MAG", "MAG"),
    ("source_SAG", "SAG"),
    ("source_unknown", "unknown"),
]
TARGET_CODE_ITEMS = [
    ("proj_meta_any", ""),
    (None, "ICNP"),
    (None, "SeqCode"),
    (None, "both"),
]
EXPORT_FORMATS = [
    ("proj_export_json", "json"),
    ("proj_export_csv", "csv"),
    ("proj_export_md", "markdown"),
]
_EXPORT_EXT = {"json": "json", "csv": "csv", "markdown": "md"}


class ProjectView(QWidget):
    """Project management view."""

    def __init__(self, state, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._store = ProjectStore()
        self._build_ui()
        self._apply_styles()
        self._connect_signals()
        self._refresh_projects()
        self.retranslate_ui()
        i18n.connect_language_changed(self.retranslate_ui)
        appearance.connect_changed(self.restyle)
        # reload when another view (e.g. Generate) touches the store
        self._state.projects_changed.connect(self._refresh_projects)

    # -- construction ---------------------------------------------------------

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)

        # --- left: project list + create form ---
        left = QVBoxLayout()
        self.projects_label = QLabel()
        self.projects_label.setObjectName("sectionHeader")
        left.addWidget(self.projects_label)

        self.project_list = QListWidget()
        left.addWidget(self.project_list, 1)

        # create form
        create_box = QGroupBox()
        create_form = QFormLayout(create_box)
        self.create_name = QLineEdit()
        self.create_name_label = QLabel()
        self.create_data_source = QComboBox()
        self.create_data_source_label = QLabel()
        self.create_target_code = QComboBox()
        self.create_target_code_label = QLabel()
        self.create_btn = QPushButton()
        self.create_btn.setObjectName("primaryButton")
        self.create_btn.setEnabled(False)  # enabled once a name is entered
        create_form.addRow(self.create_name_label, self.create_name)
        create_form.addRow(self.create_data_source_label, self.create_data_source)
        create_form.addRow(self.create_target_code_label, self.create_target_code)
        create_form.addRow(self.create_btn)
        left.addWidget(create_box)

        self.delete_btn = QPushButton()
        left.addWidget(self.delete_btn)

        root.addLayout(left, 1)

        # --- right: candidates table + export ---
        right = QVBoxLayout()
        self.candidates_label = QLabel()
        self.candidates_label.setObjectName("sectionHeader")
        right.addWidget(self.candidates_label)

        self.empty_label = QLabel()
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        right.addWidget(self.empty_label)

        self.proj_table = ProjectTable()
        right.addWidget(self.proj_table, 1)

        # inline rating
        rate_row = QHBoxLayout()
        self.rate_label = QLabel()
        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(0, 5)
        self.rate_btn = QPushButton()
        rate_row.addWidget(self.rate_label)
        rate_row.addWidget(self.rate_spin)
        rate_row.addWidget(self.rate_btn)
        rate_row.addStretch(1)
        right.addLayout(rate_row)

        # export row
        export_row = QHBoxLayout()
        self.export_label = QLabel()
        self.export_combo = QComboBox()
        self.export_btn = QPushButton()
        export_row.addWidget(self.export_label)
        export_row.addWidget(self.export_combo)
        export_row.addWidget(self.export_btn)
        export_row.addStretch(1)
        right.addLayout(export_row)

        root.addLayout(right, 2)

    def _apply_styles(self) -> None:
        """(Re-)resolve the colour this view states in a widget stylesheet."""
        self.empty_label.setStyleSheet(
            f"color: {appearance.token(theme.COLOR_MUTED)}; padding: 18px;"
        )

    def restyle(self) -> None:
        """Re-paint after a light/dark switch.

        The candidates table subscribes to the same signal and re-colours its own
        compliance cells, so this covers only the label this view owns.
        """
        self._apply_styles()

    def _connect_signals(self) -> None:
        self.create_btn.clicked.connect(self._on_create)
        self.delete_btn.clicked.connect(self._on_delete)
        self.rate_btn.clicked.connect(self._on_rate)
        self.export_btn.clicked.connect(self._on_export)
        self.project_list.currentTextChanged.connect(self._on_project_selected)
        self.create_name.textChanged.connect(self._refresh_action_state)
        self.proj_table.table.itemSelectionChanged.connect(self._refresh_action_state)

    # -- behaviour ------------------------------------------------------------

    def _refresh_action_state(self) -> None:
        """Enable project-scoped actions only when they can act."""
        has_name = bool(self.create_name.text().strip())
        self.create_btn.setEnabled(has_name)

        has_project = self.project_list.currentItem() is not None
        has_candidate_row = 0 <= self.proj_table.table.currentRow() < len(
            self.proj_table._candidates
        )
        self.delete_btn.setEnabled(has_project)
        self.export_btn.setEnabled(has_project)
        self.rate_btn.setEnabled(has_project and has_candidate_row)

    def _refresh_projects(self) -> None:
        self.project_list.clear()
        names = self._store.list_projects()
        self.project_list.addItems(names)
        # if state has a current project, select it
        if self._state.current_project and self._state.current_project in names:
            self.project_list.setCurrentRow(names.index(self._state.current_project))
        elif names:
            self.project_list.setCurrentRow(0)
        else:
            self._state.current_project = None
            self._show_empty()
        self._refresh_action_state()

    def _on_project_selected(self, name: str) -> None:
        if not name:
            self._show_empty()
            self._refresh_action_state()
            return
        try:
            project = self._store.load(name)
        except ProjectLoadError as exc:
            QMessageBox.warning(self, i18n.tr("app_title"), str(exc))
            return
        if project is None:
            self._show_empty()
            self._refresh_action_state()
            return
        self._state.current_project = name
        self.candidates_label.setText(
            f"{i18n.tr('proj_candidates')} — {project.name} ({len(project.candidates)})"
        )
        self.empty_label.setVisible(not project.candidates)
        if not project.candidates:
            self.empty_label.setText(i18n.tr("proj_no_candidates"))
        self.proj_table.set_project(name, project.candidates)
        self._refresh_action_state()

    def _show_empty(self) -> None:
        self.candidates_label.setText(i18n.tr("proj_candidates"))
        self.empty_label.setText(i18n.tr("proj_empty"))
        self.empty_label.show()
        self.proj_table.clear()

    def _on_create(self) -> None:
        name = self.create_name.text().strip()
        if not name:
            return
        data_source = self.create_data_source.currentData()
        target_code = self.create_target_code.currentData()
        try:
            self._store.create(name, data_source=data_source, target_code=target_code)
        except Exception as exc:
            QMessageBox.warning(self, i18n.tr("app_title"), str(exc))
            return
        self.create_name.clear()
        self._refresh_projects()
        # select the new project
        for i in range(self.project_list.count()):
            if self.project_list.item(i).text() == name:
                self.project_list.setCurrentRow(i)
                break

    def _on_delete(self) -> None:
        name = self.project_list.currentItem()
        if name is None:
            return
        name_text = name.text()
        reply = QMessageBox.question(
            self,
            i18n.tr("proj_delete"),
            f"{i18n.tr('proj_delete_confirm')} {name_text}?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._store.delete(name_text)
        if self._state.current_project == name_text:
            self._state.current_project = None
        self._refresh_projects()

    def _on_rate(self) -> None:
        name = self.project_list.currentItem()
        if name is None:
            return
        project_name = name.text()
        row = self.proj_table.table.currentRow()
        if row < 0 or row >= len(self.proj_table._candidates):
            return
        cand = self.proj_table._candidates[row]
        score = self.rate_spin.value()
        try:
            self._store.rate_candidate(project_name, cand.name, score)
        except (FileNotFoundError, ValueError, ProjectLoadError) as exc:
            QMessageBox.warning(self, i18n.tr("app_title"), str(exc))
            return
        # refresh the table
        self._on_project_selected(project_name)

    def _on_export(self) -> None:
        name = self.project_list.currentItem()
        if name is None:
            return
        project_name = name.text()
        fmt = self.export_combo.currentData() or "json"
        ext = _EXPORT_EXT.get(fmt, fmt)
        try:
            if fmt == "json":
                content = self._store.export_json(project_name)
            elif fmt == "csv":
                content = self._store.export_csv(project_name)
            else:
                content = self._store.export_markdown(project_name)
        except (FileNotFoundError, ProjectLoadError) as exc:
            QMessageBox.warning(self, i18n.tr("proj_export_err"), str(exc))
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            i18n.tr("proj_export"),
            f"{project_name}.{ext}",
            f"{fmt.upper()} (*.{ext});;All Files (*)",
        )
        if not path:
            return
        try:
            # same durability discipline as the project store and the dedup
            # cache: temp file in the target directory + fsync + os.replace.
            # A plain write_text() would leave a *truncated* deliverable behind
            # on interruption — one that still carries the "prokname v… exported
            # at …" header and the licence footer, so it would read as complete.
            atomic_write_text(Path(path), content)
        except OSError as exc:
            QMessageBox.warning(self, i18n.tr("proj_export_err"), str(exc))
            return
        QMessageBox.information(
            self, i18n.tr("proj_export"), f"{i18n.tr('proj_export_ok')}{path}"
        )

    # -- helpers --------------------------------------------------------------

    def _fill_combo(self, combo: QComboBox, items) -> None:
        saved = combo.currentData()
        combo.clear()
        for label_key, value in items:
            label = i18n.tr(label_key) if label_key else value
            combo.addItem(label, value)
        for idx in range(combo.count()):
            if combo.itemData(idx) == saved:
                combo.setCurrentIndex(idx)
                break

    # -- i18n -----------------------------------------------------------------

    def retranslate_ui(self) -> None:
        self.projects_label.setText(i18n.tr("proj_projects"))
        self.create_btn.setText(i18n.tr("proj_create_btn"))
        self.delete_btn.setText(i18n.tr("proj_delete"))
        self.rate_label.setText(i18n.tr("proj_rate_prompt"))
        self.rate_btn.setText(i18n.tr("proj_rate_btn"))
        self.export_label.setText(i18n.tr("proj_export"))
        self.export_btn.setText(i18n.tr("proj_export"))
        self.candidates_label.setText(i18n.tr("proj_candidates"))

        self.create_name_label.setText(i18n.tr("proj_name"))
        self.create_data_source_label.setText(i18n.tr("proj_data_source"))
        self.create_target_code_label.setText(i18n.tr("proj_target_code"))
        self._fill_combo(self.create_data_source, DATA_SOURCE_ITEMS)
        self._fill_combo(self.create_target_code, TARGET_CODE_ITEMS)
        self._fill_combo(self.export_combo, EXPORT_FORMATS)

        # refresh the candidates pane for the current selection
        current = self.project_list.currentItem()
        if current is not None and current.text():
            self._on_project_selected(current.text())
        else:
            self._show_empty()
