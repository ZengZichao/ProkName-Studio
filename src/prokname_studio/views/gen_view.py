"""Generate view — the Phase-1 flagship of ProkName Studio.

A thin, interactive front-end over the engine's public ``generate()`` API. Every
control maps 1:1 onto a ``generate()`` keyword; nothing is re-implemented here.
Results are shown in a table, and selecting a row renders that candidate's full
derivation in the :class:`DerivationView`. "Add to project" reuses the exact
persistence path the ``prokname project add`` CLI command uses (ProjectStore),
and it inherits a dedup verdict only when that verdict was obtained for the very
name being added (see :mod:`prokname.presentation.decision`).
"""
from __future__ import annotations

from prokname.engine.gender import Gender, gender_of
from prokname.engine.generate import generate, known_ranks
from prokname.engine.orthography import latinize_words
from prokname.presentation import decision
from prokname.storage import Candidate as StoredCandidate
from prokname.storage import ProjectStore
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .. import appearance, i18n
from ..components.derivation_view import DerivationView
from ..worker import EngineWorker, start

# (i18n key or literal label, value passed to generate())
TYPE_ITEMS = [
    ("type_feature", "feature"),
    ("type_place", "place"),
    ("type_person", "person"),
    ("type_thing", "thing"),
]
PERSON_GENDER_ITEMS = [("gen_auto", None), ("gen_male", "male"), ("gen_female", "female")]
GENDER_OVERRIDE_ITEMS = [
    ("gen_auto", None),
    ("gender_m", "m"),
    ("gender_f", "f"),
    ("gender_n", "n"),
]
ADJECTIVE_ITEMS = [
    ("gen_auto", None),
    ("adj_second_declension", "second_declension"),
    ("adj_third_declension", "third_declension"),
    ("adj_loving", "loving"),
    ("adj_nourishing", "nourishing"),
    ("adj_place", "place"),
]

_SPECIES_RANKS = {"species", "subspecies"}


def _rank_names() -> list[str]:
    """Rank names, read when the view is built rather than at import.

    This used to be a module-level ``_RANKS = list(known_ranks().keys())``, which
    froze the rule asset into the GUI for the life of the process: an expert
    sign-off that replaced rules.json would not show up until Studio restarted
. prokname.reload_data()
    now reaches the ranks a view offers because nothing cached them at import.
    """
    return list(known_ranks().keys())


class GenerateView(QWidget):
    """Interactive name-generation view."""

    def __init__(self, state, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._candidates: list = []
        # The engine call runs on a worker thread, so the widget-derived
        # facts its result must be annotated with are captured before start()
        # and read back in the result callback — never from the worker.
        self._worker: EngineWorker | None = None
        self._provenance_request: tuple | None = None
        # how the genus gender of the *current* result set was obtained
        # ("lookup" | "inference" | "override" | "unknown" | None) and the
        # engine's own reason — surfaced in the results table.
        self._gender_mode: str | None = None
        self._gender_reason: str = ""
        # explicit label references: key → labels (no form-layout sniffing)
        self._labels: dict[str, list[QLabel]] = {}
        self._build_ui()
        self._connect_signals()
        self._refresh_field_enablement()
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

        self.stem = QLineEdit()
        self.type_combo = QComboBox()
        self.rank_combo = QComboBox()
        self.rank_combo.addItems(_rank_names())
        self.rank_combo.setCurrentText("species")  # the common case
        self.genus = QLineEdit()

        self.person_gender = QComboBox()
        self.gender_override = QComboBox()

        self.advanced = QGroupBox()
        self.advanced.setCheckable(True)
        self.advanced.setChecked(False)
        adv_form = QFormLayout(self.advanced)
        self.genus_suffix = QLineEdit()
        self.adjective = QComboBox()
        adv_form.addRow(self._label("gen_genus_suffix"), self.genus_suffix)
        adv_form.addRow(self._label("gen_adjective_formation"), self.adjective)

        form.addRow(self._label("gen_stem"), self.stem)
        form.addRow(self._label("gen_type"), self.type_combo)
        form.addRow(self._label("gen_rank"), self.rank_combo)
        form.addRow(self._label("gen_genus"), self.genus)
        form.addRow(self._label("gen_person_gender"), self.person_gender)
        form.addRow(self._label("gen_genus_gender"), self.gender_override)
        form.addRow(self.advanced)

        self.generate_btn = QPushButton()
        self.generate_btn.setObjectName("primaryButton")
        self.generate_btn.setEnabled(False)  # enabled once a stem is entered
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.generate_btn)
        form.addRow(btn_row)

        root.addWidget(form_box)

        # --- results ---
        self.results_label = QLabel()
        self.results_label.setObjectName("sectionHeader")
        root.addWidget(self.results_label)

        self.table = QTableWidget(0, 5)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.verticalHeader().setVisible(False)
        # name stays readable; metadata columns hug their content
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in (1, 2, 3):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        root.addWidget(self.table, 1)

        self.deriv = DerivationView()
        self.deriv.setMaximumHeight(220)
        root.addWidget(self.deriv)

        self.add_btn = QPushButton()
        self.add_btn.setEnabled(False)
        add_row = QHBoxLayout()
        add_row.addStretch(1)
        add_row.addWidget(self.add_btn)
        root.addLayout(add_row)

    def _connect_signals(self) -> None:
        self.generate_btn.clicked.connect(self._on_generate)
        self.add_btn.clicked.connect(self._on_add_to_project)
        self.type_combo.currentIndexChanged.connect(self._refresh_field_enablement)
        self.rank_combo.currentIndexChanged.connect(self._refresh_field_enablement)
        self.genus.textChanged.connect(self._refresh_field_enablement)
        self.advanced.toggled.connect(self._refresh_field_enablement)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        # Enter in the stem/genus fields triggers generation
        self.stem.returnPressed.connect(self._on_generate)
        self.genus.returnPressed.connect(self._on_generate)
        # responsive state: Generate is only meaningful with a stem
        self.stem.textChanged.connect(self._refresh_action_state)

    # -- behaviour ------------------------------------------------------------

    def _refresh_action_state(self) -> None:
        has_stem = bool(self.stem.text().strip())
        # A generation in flight is not clickable: without this, typing while a
        # worker ran would re-enable the button and invite a second one.
        busy = self._worker is not None and self._worker.isRunning()
        self.generate_btn.setEnabled(has_stem and not busy)

    def _refresh_field_enablement(self) -> None:
        rank = self.rank_combo.currentText()
        etype = self._current_type_value()
        is_species = rank in _SPECIES_RANKS
        is_genus = rank == "genus"
        has_genus = bool(self.genus.text().strip())

        self.genus.setEnabled(is_species)
        self.person_gender.setEnabled(is_species and etype == "person")
        # gender override is meaningful when a genus is supplied
        self.gender_override.setEnabled(is_species and has_genus)
        # advanced block gates the two optional fields; genus_suffix is only
        # meaningful for genus-rank names.
        self.genus_suffix.setEnabled(self.advanced.isChecked() and is_genus)
        self.adjective.setEnabled(self.advanced.isChecked())

    def _on_generate(self) -> None:
        stem = self.stem.text().strip()
        if not stem:
            QMessageBox.information(self, i18n.tr("app_title"), i18n.tr("gen_empty"))
            return

        etype = self._current_type_value()
        rank = self.rank_combo.currentText()
        genus = self.genus.text().strip() or None
        person_gender = self.person_gender.currentData()
        genus_suffix = (
            self.genus_suffix.text().strip() or None if self.genus_suffix.isEnabled() else None
        )
        adjective_formation = (
            self.adjective.currentData() if self.adjective.isEnabled() else None
        )

        # gender override: convert "m"/"f"/"n" to Gender enum
        if self.gender_override.isEnabled():
            override_val = self.gender_override.currentData()
        else:
            override_val = None
        gender_override = Gender(override_val) if override_val else None

        # Same thread rule as `check`: the view reads every widget
        # here, then hands the pure computation to studio.worker, because a
        # QThread must never touch the UI. `generate()` is in-memory today, so
        # this buys no visible speed — what it buys is that the next person to
        # make generation heavier (a corpus scan, cache IO) cannot freeze the
        # window by following the other view's example.
        self._provenance_request = (rank, genus, gender_override)
        started = start(
            self, generate,
            busy=lambda: self._worker is not None and self._worker.isRunning(),
            on_result=self._on_candidates,
            on_error=self._on_generate_failed,
            args=(stem, etype, rank),
            kwargs={
                "genus": genus,
                "person_gender": person_gender,
                "gender_override": gender_override,
                "genus_suffix": genus_suffix,
                "adjective_formation": adjective_formation,
            },
        )
        if started is None:
            return  # already running; that call owns the table
        if started.isRunning():
            self._worker = started
        self._refresh_action_state()

    def _on_worker_finished(self) -> None:
        """Single place where the in-flight worker is released."""
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        self._refresh_action_state()

    def _on_generate_failed(self, message: str) -> None:
        """Engine refusal, reported rather than swallowed.

        `generate()` raises for an unresolvable stem or an illegal rank/etype
        combination. The worker turns that into text with the exception type
        attached, because a bare ``str(exc)`` can be empty and an empty dialog
        teaches the user nothing.
        """
        QMessageBox.warning(self, i18n.tr("app_title"),
                            i18n.tr("gen_err") + message)

    def _on_candidates(self, candidates: list) -> None:
        rank, genus, gender_override = self._provenance_request or (None, None, None)
        self._candidates = candidates
        self._state.set_candidates(candidates)
        self._capture_gender_provenance(rank, genus, gender_override)
        self._populate_table(candidates)
        self.deriv.set_candidate(candidates[0] if candidates else None)
        self.add_btn.setEnabled(bool(candidates))
        self._update_results_label()

    def _capture_gender_provenance(
        self, rank: str, genus: str | None, gender_override: Gender | None
    ) -> None:
        """Record *how* the genus gender behind this result set was obtained.

        ``generate()`` resolves the genus gender once per call (via the public
        ``gender_of()``) and its engine ``Candidate`` carries no mode field, so
        the view asks that same public API — the only way to tell a lexicon-backed
        "compliant" from a low-confidence inferred one without re-deriving
        anything. Higher/genus ranks decline nothing: provenance is cleared.
        """
        if rank not in _SPECIES_RANKS or not genus:
            self._gender_mode = None
            self._gender_reason = ""
            return
        tokens = latinize_words(genus)
        if not tokens:
            self._gender_mode = None
            self._gender_reason = ""
            return
        result = gender_of(tokens[0], gender_override)
        self._gender_mode = result.mode
        self._gender_reason = result.reason

    def _update_results_label(self) -> None:
        if self._candidates:
            self.results_label.setText(
                f"{i18n.tr('gen_results')} ({len(self._candidates)})"
            )
        else:
            self.results_label.setText(i18n.tr("gen_empty"))

    def _populate_table(self, candidates: list) -> None:
        self.table.setRowCount(len(candidates))
        for i, c in enumerate(candidates):
            self.table.setItem(i, 0, QTableWidgetItem(c.name))
            # localized labels — engine enum values must not leak into the UI
            self.table.setItem(i, 1, QTableWidgetItem(i18n.category_label(c.grammatical_category)))
            self.table.setItem(i, 2, QTableWidgetItem(i18n.gender_label(c.gender)))
            # "compliant=yes" must say whether the genus gender behind it came
            # from the lexicon or from low-confidence inference: inference is
            # never authority, so it never gets the plain green "yes".
            style = decision.compliance_style(
                c.compliant, self._gender_mode, c.grammatical_category
            )
            comp_item = QTableWidgetItem(i18n.tr(style.key))
            comp_item.setForeground(QColor(appearance.token(style.color)))
            if style.key in ("compliant_yes_inferred", "compliant_yes_unverified"):
                hint = i18n.tr(decision.INFERRED_GENDER_HINT_KEY)
                tip = f"{hint}\n{self._gender_reason}" if self._gender_reason else hint
                comp_item.setToolTip(tip)
            self.table.setItem(i, 3, comp_item)
            short = (c.derivation or "-").split("\n", 1)[0]
            self.table.setItem(i, 4, QTableWidgetItem(short))
        if candidates:
            self.table.selectRow(0)

    def _on_selection_changed(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self._candidates):
            self.deriv.set_candidate(self._candidates[row])

    def _on_add_to_project(self) -> None:
        row = self.table.currentRow()
        if not (0 <= row < len(self._candidates)):
            return
        cand = self._candidates[row]
        name, ok = QInputDialog.getText(
            self,
            i18n.tr("add_to_project"),
            i18n.tr("add_prompt"),
            text=i18n.tr("add_default_project"),
        )
        if not ok or not name.strip():
            return
        # Close the check → project loop *with its provenance*: the session's
        # last verdict is inherited only when it was obtained for this exact
        # name. A check of "Bacillus beijingensis" must never follow an
        # unrelated "Wukomonas ..." candidate into the project file, the CSV
        # and the Markdown deliverable — verdicts have to stay traceable to the
        # authority query they came from.
        provenance = self._state.verdict_provenance_for(cand.name)
        stored = StoredCandidate(
            name=cand.name,
            epithet=cand.epithet,
            rank=cand.rank,
            grammatical_category=cand.grammatical_category,
            gender=cand.gender,
            derivation=cand.derivation,
            compliant=cand.compliant,
            warnings=list(cand.warnings),
            check_verdict=provenance.verdict if provenance else None,
            check_query=provenance.query if provenance else None,
            checked_at=provenance.checked_at if provenance else None,
        )
        # The store write stays on the UI thread on purpose, unlike the engine
        # call above: it is one small atomic write of a record the user just
        # asked for, its failure must be shown as a dialog before the project
        # state moves on, and `ProjectStore` is not thread-safe. Threading it
        # would trade a sub-millisecond stall for a race on `self._state`.
        ProjectStore().add_candidate(name.strip(), stored)
        self._state.current_project = name.strip()
        # let the Project view reload its list without a restart
        self._state.notify_projects_changed()
        QMessageBox.information(
            self, i18n.tr("add_to_project"), f"{i18n.tr('add_ok')}{name.strip()}"
        )

    # -- helpers --------------------------------------------------------------

    def _current_type_value(self) -> str:
        data = self.type_combo.currentData()
        return data if data is not None else "feature"

    def _fill_combo(self, combo: QComboBox, items) -> None:
        saved = combo.currentData()
        combo.clear()
        for label_key, value in items:
            combo.addItem(i18n.tr(label_key), value)
        # restore previous selection by value
        for idx in range(combo.count()):
            if combo.itemData(idx) == saved:
                combo.setCurrentIndex(idx)
                break

    # -- i18n -----------------------------------------------------------------

    def retranslate_ui(self) -> None:
        self._fill_combo(self.type_combo, TYPE_ITEMS)
        self._fill_combo(self.person_gender, PERSON_GENDER_ITEMS)
        self._fill_combo(self.gender_override, GENDER_OVERRIDE_ITEMS)
        self._fill_combo(self.adjective, ADJECTIVE_ITEMS)

        # every form label is re-labelled from its own stored reference — no
        # assumption about how many QFormLayouts the widget tree holds
        # (`findChild(QFormLayout)` would only ever reach the first one).
        for key, labels in self._labels.items():
            text = i18n.tr(key)
            for label in labels:
                label.setText(text)

        self.advanced.setTitle(i18n.tr("gen_advanced"))

        self.generate_btn.setText(i18n.tr("gen_button"))
        self.add_btn.setText(i18n.tr("add_to_project"))
        self.stem.setPlaceholderText(i18n.tr("gen_stem"))
        self.genus.setPlaceholderText(i18n.tr("gen_genus"))
        self.genus_suffix.setPlaceholderText(i18n.tr("gen_genus_suffix"))

        self.table.setHorizontalHeaderLabels(
            [
                i18n.tr("col_name"),
                i18n.tr("col_category"),
                i18n.tr("col_gender"),
                i18n.tr("col_compliant"),
                i18n.tr("col_derivation"),
            ]
        )
        self._update_results_label()
        # re-render candidate data under the new language, keeping the selection
        if self._candidates:
            row = max(self.table.currentRow(), 0)
            self._populate_table(self._candidates)
            self.table.selectRow(row)
            self.deriv.set_candidate(self._candidates[row])

    def restyle(self) -> None:
        """Re-colour the compliance column after a light/dark switch.

        The derivation tree handles itself on the same signal, so this owns only
        the table — whose selected row has to survive the redraw.
        """
        if not self._candidates:
            return
        row = max(self.table.currentRow(), 0)
        self._populate_table(self._candidates)
        self.table.selectRow(row)
