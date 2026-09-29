"""Check view — dedup / homonymy check (Phase 2).

A thin front-end over the engine's public ``check_name()`` API. The user enters
a candidate name, selects the near-match scan mode and distance threshold, and
clicks "Check". The verdict, sources, near matches, and warnings are rendered
via :class:`~prokname_studio.components.verdict_view.VerdictView`.

The check runs on a worker :class:`QThread`: the near-match scan is linear in
the corpus and would freeze the GUI thread on a full-size corpus.
"""
from __future__ import annotations

from prokname.dedup import check_name
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from .. import i18n
from ..components.verdict_view import VerdictView
from ..worker import EngineWorker, start

NEAR_MATCH_MODE_ITEMS = [
    ("near_match_whole", "whole"),
    ("near_match_stem", "stem"),
    ("near_match_both", "both"),
]


class CheckView(QWidget):
    """Dedup / homonymy check view."""

    def __init__(self, state, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._state = state
        self._report = None
        self._worker: EngineWorker | None = None
        # explicit label references: key → labels (no form-layout sniffing)
        self._labels: dict[str, list[QLabel]] = {}
        self._build_ui()
        self._connect_signals()
        self.retranslate_ui()
        i18n.connect_language_changed(self.retranslate_ui)

    # -- construction ---------------------------------------------------------

    def _label(self, key: str) -> QLabel:
        """Create a form label and remember it under ``key`` for retranslation."""
        label = QLabel()
        self._labels.setdefault(key, []).append(label)
        return label

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        form_box = QGroupBox()
        form = QFormLayout(form_box)

        self.name_input = QLineEdit()
        self.mode_combo = QComboBox()
        self.distance_spin = QSpinBox()
        self.distance_spin.setRange(0, 4)
        self.distance_spin.setValue(2)
        self.online_check = QCheckBox()
        self.online_check.setChecked(False)
        # M0-gated: stays disabled and unchecked. The state is deliberately
        # never read — Studio checks are offline only, and the tooltip says
        # which verdicts that leaves reachable. It used to blame "the M0
        # endpoint records", which now exist: what is actually missing is LPSN
        # credentials and a by-name lookup the Registry does not offer.
        self.online_check.setEnabled(False)
        self.online_check.setToolTip(i18n.tr("check_online_tooltip"))

        self.check_btn = QPushButton()
        self.check_btn.setObjectName("primaryButton")
        self.check_btn.setEnabled(False)  # enabled once a name is entered
        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        btn_row.addWidget(self.check_btn)
        form.addRow(self._label("check_name"), self.name_input)
        form.addRow(self._label("check_near_match_mode"), self.mode_combo)
        form.addRow(self._label("check_max_distance"), self.distance_spin)
        form.addRow(self.online_check)
        form.addRow(btn_row)

        root.addWidget(form_box)

        self.verdict_view = VerdictView()
        root.addWidget(self.verdict_view, 1)

    def _connect_signals(self) -> None:
        self.check_btn.clicked.connect(self._on_check)
        # Enter in the name field triggers the check
        self.name_input.returnPressed.connect(self._on_check)
        # responsive state: Check is only meaningful with a name
        self.name_input.textChanged.connect(self._refresh_action_state)

    # -- behaviour ------------------------------------------------------------

    def _refresh_action_state(self) -> None:
        self.check_btn.setEnabled(bool(self.name_input.text().strip()))

    def _on_check(self) -> None:
        name = self.name_input.text().strip()
        if not name:
            return
        mode = self.mode_combo.currentData() or "whole"
        max_dist = self.distance_spin.value()
        # The scan is linear in the corpus — run it off the GUI thread so a
        # full-size corpus cannot freeze the window (no progress, no cancel).
        # `studio.worker` owns the re-entry guard and the single reset path:
        # QThread.finished fires whether run() succeeded, failed, or the OS
        # refused the thread, so the button can never stay stuck on a disabled
        # "Check" that no signal will re-enable.
        self.check_btn.setEnabled(False)
        started = start(
            self, check_name,
            busy=lambda: self._worker is not None and self._worker.isRunning(),
            on_result=self._on_check_finished,
            on_error=self._on_check_failed,
            args=(name,),
            kwargs={"near_match": True, "max_distance": max_dist,
                    "near_match_mode": mode},
        )
        if started is None:
            return  # duplicate click while a check is in flight; keep that worker
        if started.isRunning():
            self._worker = started
            return
        # pragma: no cover - the OS refused the thread; the helper already ran
        # the reset path, so only the explanation is left to do here.
        QMessageBox.warning(
            self, i18n.tr("check_failed"),
            f"{i18n.tr('check_failed')}QThread could not be started",
        )

    def _on_worker_finished(self) -> None:
        """Single place where the in-flight worker is released."""
        worker = self._worker
        self._worker = None
        if worker is not None:
            worker.deleteLater()
        self._refresh_action_state()

    def _on_check_finished(self, report) -> None:
        self._report = report
        self._state.set_last_check(report)
        self.verdict_view.set_report(report)

    def _on_check_failed(self, message: str) -> None:
        QMessageBox.warning(
            self, i18n.tr("check_failed"), f"{i18n.tr('check_failed')}{message}"
        )

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
        self._fill_combo(self.mode_combo, NEAR_MATCH_MODE_ITEMS)

        # every form label is re-labelled from its own stored reference — no
        # assumption about how many QFormLayouts the widget tree holds.
        for key, labels in self._labels.items():
            text = i18n.tr(key)
            for label in labels:
                label.setText(text)

        self.online_check.setText(i18n.tr("check_online"))
        self.online_check.setToolTip(i18n.tr("check_online_tooltip"))
        self.check_btn.setText(i18n.tr("check_button"))
        self.name_input.setPlaceholderText(i18n.tr("check_name"))
