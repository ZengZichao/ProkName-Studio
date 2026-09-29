"""Derivation tree widget for ProkName Studio.

Renders a single engine ``Candidate`` as a small, scannable tree so the user can
see *why* a name was produced — the grammatical category, the gender it declines
against, the free-text derivation, and any warnings. This is a pure view: it
never re-derives anything, it only visualises the engine's own output.
"""
from __future__ import annotations

from prokname.presentation import theme
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from .. import appearance, i18n

_COMPLIANT_KEY = {True: "compliant_yes", False: "compliant_no", None: "compliant_review"}
_COMPLIANT_COLOR = {
    True: theme.COLOR_SUCCESS,
    False: theme.COLOR_DANGER,
    None: theme.COLOR_WARNING,
}


class DerivationView(QWidget):
    """Tree view of one candidate's derivation."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._candidate = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setAlternatingRowColors(True)
        self.tree.setWordWrap(False)
        layout.addWidget(self.tree)
        i18n.connect_language_changed(self.retranslate_ui)
        appearance.connect_changed(self.restyle)

    # -- public API -----------------------------------------------------------

    def set_candidate(self, candidate) -> None:
        """Populate the tree from an engine ``Candidate``."""
        self._candidate = candidate
        self.tree.clear()
        if candidate is None:
            return

        # Built detached, then attached once — constructing QTreeWidgetItem
        # with a widget parent would insert it directly as a second top-level
        # item instead of nesting derivation/warnings under the name.
        root = QTreeWidgetItem([candidate.name or "-"])

        compliance = i18n.tr(_COMPLIANT_KEY.get(candidate.compliant, "compliant_review"))
        comp = self._leaf(root, f"{i18n.tr('col_compliant')}: {compliance}")
        comp_color = _COMPLIANT_COLOR.get(candidate.compliant, theme.COLOR_WARNING)
        comp.setForeground(0, QColor(appearance.token(comp_color)))
        self._leaf(root, f"{i18n.tr('gen_rank')}: {candidate.rank or '-'}")
        self._leaf(
            root,
            f"{i18n.tr('col_category')}: {i18n.category_label(candidate.grammatical_category)}",
        )
        self._leaf(root, f"{i18n.tr('col_gender')}: {i18n.gender_label(candidate.gender)}")

        deriv = QTreeWidgetItem([i18n.tr("col_derivation")])
        root.addChild(deriv)
        self._leaf(deriv, candidate.derivation or "-")

        if candidate.warnings:
            warn = QTreeWidgetItem([i18n.tr("warnings_label")])
            warn.setForeground(0, QColor(appearance.token(theme.COLOR_WARNING)))
            root.addChild(warn)
            for w in candidate.warnings:
                leaf = self._leaf(warn, w)
                leaf.setForeground(0, QColor(appearance.token(theme.COLOR_WARNING)))

        self.tree.addTopLevelItem(root)
        # expansion is only reliable once the item is attached to the widget
        root.setExpanded(True)
        deriv.setExpanded(True)
        if candidate.warnings:
            warn.setExpanded(True)

    def clear(self) -> None:
        self._candidate = None
        self.tree.clear()

    def restyle(self) -> None:
        """Re-render the stored candidate so its colours follow the new mode."""
        self.set_candidate(self._candidate)

    # -- i18n -----------------------------------------------------------------

    def retranslate_ui(self) -> None:
        """Re-translate static labels; dynamic candidate data is re-set by caller."""
        # The tree content is candidate-driven; views re-call set_candidate()
        # after a language switch. Nothing static to re-label here.
        pass

    # -- helpers --------------------------------------------------------------

    @staticmethod
    def _leaf(parent: QTreeWidgetItem, text: str) -> QTreeWidgetItem:
        item = QTreeWidgetItem(parent, [text])
        item.setExpanded(True)
        return item
