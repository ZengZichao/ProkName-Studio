"""Headless tests for the Studio's decision layer.

``prokname.presentation.decision`` and ``prokname.presentation.theme``
import no Qt, so
these run with or without the optional ``[gui]`` extra — they are the
regression net for the provenance and fail-safe-colouring logic even on a
machine where the Qt view tests have to be skipped.
"""
from __future__ import annotations

from enum import Enum, auto
from types import SimpleNamespace

from prokname.dedup.model import Verdict
from prokname.presentation import decision, theme


def _report(query: str | None, verdict: object = Verdict.BLOCKED,
            checked_at: object = "2026-09-21T09:00:00+00:00"):
    fields: dict[str, object] = {"verdict": verdict, "checked_at": checked_at}
    if query is not None:
        fields["query"] = query
    return SimpleNamespace(**fields)


# --------------------------------------------------------------------------- #
# Verdicts may only travel to the name they were obtained for
# --------------------------------------------------------------------------- #


class TestCheckProvenance:

    def test_matching_name_carries_verdict_query_and_timestamp(self):
        prov = decision.check_provenance_for(
            _report("Bacillus beijingensis"), "Bacillus beijingensis"
        )
        assert prov is not None
        assert prov.verdict == "blocked"
        assert prov.query == "Bacillus beijingensis"
        assert prov.checked_at == "2026-09-21T09:00:00+00:00"

    def test_cross_name_verdict_is_refused(self):
        """The scenario: BLOCKED for Bacillus beijingensis must never land
        on an unrelated Wukomonas candidate."""
        report = _report("Bacillus beijingensis")
        assert decision.check_provenance_for(report, "Wukomonas otherensis") is None

    def test_comparison_uses_the_dedup_normalisation(self):
        report = _report("  Wukomonas  Beijingensis ")
        prov = decision.check_provenance_for(report, "Wukomonas beijingensis")
        assert prov is not None and prov.verdict == "blocked"
        # accents are folded the same way the dedup layer folds them
        assert decision.names_agree("Münchner straße", "muenchner strasse")

    def test_subspecies_binomial_matches_itself_only(self):
        report = _report("Bacillus subtilis subsp. wukongensis")
        assert decision.check_provenance_for(
            report, "Bacillus subtilis subsp. wukongensis") is not None
        assert decision.check_provenance_for(
            report, "Bacillus subtilis") is None

    def test_no_report_or_no_verdict_yields_nothing(self):
        assert decision.check_provenance_for(None, "Bacillus wukongus") is None
        assert decision.check_provenance_for(
            _report("Bacillus wukongus", verdict=None), "Bacillus wukongus") is None

    def test_report_without_query_cannot_be_attached(self):
        """A verdict with no recorded query is untraceable → not inherited."""
        report = SimpleNamespace(verdict=Verdict.BLOCKED, checked_at="x")
        assert decision.check_provenance_for(report, "Bacillus wukongus") is None

    def test_empty_query_never_matches(self):
        assert decision.check_provenance_for(_report(""), "Bacillus wukongus") is None
        assert decision.check_provenance_for(_report(None), None) is None

    def test_plain_string_verdict_is_accepted(self):
        """Test doubles / cached reports may carry the bare value."""
        report = _report("Bacillus wukongus", verdict="conflict")
        prov = decision.check_provenance_for(report, "Bacillus wukongus")
        assert prov is not None and prov.verdict == "conflict"

    def test_missing_checked_at_is_tolerated(self):
        report = _report("Bacillus wukongus", checked_at=None)
        prov = decision.check_provenance_for(report, "Bacillus wukongus")
        assert prov is not None and prov.checked_at is None

    def test_verdict_value_of_nothing_is_none(self):
        assert decision.verdict_value(None) is None
        assert decision.verdict_value(SimpleNamespace()) is None
        assert decision.verdict_value(SimpleNamespace(verdict=None)) is None


# --------------------------------------------------------------------------- #
# Unknown must never render as optimistic
# --------------------------------------------------------------------------- #


class TestVerdictStyles:

    def test_every_engine_verdict_has_its_own_style(self):
        for verdict in Verdict:
            style = decision.verdict_style(verdict)
            assert style.key != decision.UNKNOWN_VERDICT_KEY, (
                f"{verdict!r} has no badge mapping yet (decision._VERDICT_KEYS)"
            )
        assert decision.mapped_verdicts() == set(Verdict)

    def test_new_enum_member_cannot_render_green_or_optimistic(self):
        """A Verdict member added to the engine without a UI mapping must not
        borrow the most optimistic wording ("no clear conflict") or its green."""

        class FutureVerdict(Enum):
            SOMETHING_NEW = auto()

        style = decision.verdict_style(FutureVerdict.SOMETHING_NEW)
        assert style.key == decision.UNKNOWN_VERDICT_KEY
        assert style.color == theme.COLOR_MUTED
        assert style.color not in (
            theme.COLOR_SUCCESS, theme.COLOR_INFO, theme.COLOR_WARNING,
        )

    def test_unknown_verdict_spelling_cannot_be_guessed(self):
        assert decision.verdict_style("not_a_verdict").key == decision.UNKNOWN_VERDICT_KEY
        assert decision.verdict_style(None).key == decision.UNKNOWN_VERDICT_KEY

    def test_blocked_and_conflict_stay_dangerous(self):
        assert decision.verdict_style(Verdict.BLOCKED).color == theme.COLOR_DANGER_BRIGHT
        assert decision.verdict_style(Verdict.CONFLICT).color == theme.COLOR_DANGER

    def test_only_no_clear_conflict_is_green(self):
        greens = {
            v for v in Verdict if decision.verdict_style(v).color == theme.COLOR_SUCCESS
        }
        assert greens == {Verdict.NO_CLEAR_CONFLICT}


class TestRoleStyles:

    def test_new_role_cannot_render_as_default_recommended(self):
        style = decision.role_style("some-future-role")
        assert style.key == decision.UNKNOWN_ROLE_KEY
        assert style.color == theme.COLOR_MUTED
        assert style.key != "role_default"

    def test_missing_role_is_unknown_too(self):
        for role in (None, "", 42):
            assert decision.role_style(role).key == decision.UNKNOWN_ROLE_KEY

    def test_only_viable_is_not_coloured_as_success(self):
        """MAG/SAG ⇒ SeqCode-only is a constraint, not a smooth path."""
        style = decision.role_style("only-viable")
        assert style.key == "role_only_viable"
        assert style.color != theme.COLOR_SUCCESS
        assert style.color == theme.COLOR_WARNING

    def test_router_roles_are_all_mapped(self):
        """The roles routing/router.py can emit must all be mapped explicitly."""
        emitted = {"default", "alternative", "only-viable", "conflict-guidance"}
        assert emitted == decision.mapped_roles()

    def test_conflict_guidance_is_not_green(self):
        assert decision.role_style("conflict-guidance").color == theme.COLOR_DANGER_BRIGHT


# --------------------------------------------------------------------------- #
# Inference must be visible in the results table
# --------------------------------------------------------------------------- #


class TestComplianceStyles:

    def test_lexicon_yes_is_green_plain_yes(self):
        style = decision.compliance_style(True, "lookup", "adjective")
        assert (style.key, style.color) == ("compliant_yes", theme.COLOR_SUCCESS)

    def test_inference_yes_is_not_the_same_as_lexicon_yes(self):
        lexicon = decision.compliance_style(True, "lookup", "adjective")
        inferred = decision.compliance_style(True, "inference", "adjective")
        assert inferred.key != lexicon.key
        assert inferred.color != theme.COLOR_SUCCESS
        assert inferred.key == "compliant_yes_inferred"
        assert inferred.color == theme.COLOR_WARNING

    def test_override_yes_is_authoritative(self):
        assert decision.compliance_style(
            True, "override", "adjective").key == "compliant_yes"

    def test_unrecorded_basis_is_flagged_too(self):
        assert decision.compliance_style(
            True, None, "adjective").key == "compliant_yes_unverified"

    def test_appositive_names_do_not_decline_so_inference_is_irrelevant(self):
        assert decision.compliance_style(
            True, "inference", "appositive").key == "compliant_yes"
        assert decision.compliance_style(
            True, "inference", "genitive").key == "compliant_yes"

    def test_three_state_rendering_is_conservative(self):
        """None (and anything unexpected) must stay orange, never green."""
        assert decision.compliance_style(None, "lookup", "adjective").key == (
            "compliant_review"
        )
        assert decision.compliance_style(None, "inference", None).color == (
            theme.COLOR_WARNING
        )
        assert decision.compliance_style(False, "lookup", "adjective").key == (
            "compliant_no"
        )
        assert decision.compliance_style(False, "lookup", "adjective").color == (
            theme.COLOR_DANGER
        )

    def test_no_compliant_style_ever_falls_through_to_green(self):
        styles = {
            decision.compliance_style(compliant, mode, category)
            for compliant in (True, False, None)
            for mode in (None, "lookup", "inference", "override", "unknown", "junk")
            for category in (None, "adjective", "genitive", "appositive", "junk")
        }
        green = {s for s in styles if s.color == theme.COLOR_SUCCESS}
        assert {s.key for s in green} == {"compliant_yes"}


class TestStylePlumbing:

    def test_unmapped_label_key_is_neutral(self):
        style = decision.style_for("verdict_something_nobody_added")
        assert style.color == theme.COLOR_MUTED

    def test_style_colours_are_real_palette_tokens(self):
        tokens = {
            value for name, value in vars(theme).items() if name.startswith("COLOR_")
        }
        assert set(decision.STYLE_COLORS.values()) <= tokens
