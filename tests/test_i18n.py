"""Tests for the bilingual (zh/en) i18n layer.

``i18n`` imports Qt signals, and PySide6 is a runtime dependency of this
package: a run that cannot import it is a broken install, and failing is the
right answer. The ``importorskip`` gate that used to sit here belonged to the
engine repository, where the GUI was an optional extra.
"""
from __future__ import annotations

import pytest

from prokname_studio import i18n


def test_tr_default_falls_back_to_en() -> None:
    i18n.set_language("en")
    assert i18n.tr("nav_generate") == "Generate"


def test_tr_zh() -> None:
    i18n.set_language("zh")
    assert i18n.tr("nav_generate") == "生成"


def test_missing_key_returns_key() -> None:
    assert i18n.tr("no_such_key") == "no_such_key"


def test_set_language_emits_signal() -> None:
    i18n.set_language("en")
    received: list[str] = []
    i18n.connect_language_changed(received.append)
    i18n.set_language("zh")
    assert received == ["zh"]


def test_set_language_auto_resolves_to_supported() -> None:
    i18n.set_language_auto()
    assert i18n.current_language() in ("zh", "en")


# -- keys added in Phase 2–4 ---------------------------------------------------

_PHASE2_KEYS = [
    "route_source", "route_candidatus", "route_icnp_occupied",
    "route_button", "route_viable_paths", "route_col_code",
    "route_col_role", "route_col_tradeoffs",
    "check_name", "check_near_match_mode", "check_max_distance",
    "check_button", "check_verdict", "check_sources",
    "check_col_source", "check_col_tier", "check_col_status",
    "check_col_detail", "check_near_matches",
    "check_col_corpus", "check_col_distance", "check_col_nm_source",
    "verdict_conflict", "verdict_parahomonym_warning",
    "verdict_verify_warning", "verdict_blocked", "verdict_no_clear_conflict",
    "source_pure_culture", "source_MAG", "source_SAG", "source_unknown",
    "role_default", "role_alternative", "role_only_viable", "role_conflict_guidance",
    "near_match_whole", "near_match_stem", "near_match_both",
    "check_blocked_note", "check_online_tooltip",
]

_PHASE3_KEYS = [
    "proj_projects", "proj_create", "proj_name", "proj_data_source",
    "proj_target_code", "proj_create_btn", "proj_delete",
    "proj_delete_confirm", "proj_candidates", "proj_export",
    "proj_export_json", "proj_export_csv", "proj_export_md",
    "proj_empty", "proj_no_candidates", "proj_rate_prompt",
    "proj_col_name", "proj_col_category", "proj_col_compliant",
    "proj_col_score", "proj_export_ok", "proj_export_err",
]

_PHASE4_KEYS = [
    "data_title", "data_col_file", "data_col_version",
    "data_col_status", "data_empty",
]

_GEN_PHASE1_KEYS = [
    "gen_genus_gender", "gender_m", "gender_f", "gender_n",
    "app_subtitle",
]


@pytest.mark.parametrize("key", _PHASE2_KEYS + _PHASE3_KEYS + _PHASE4_KEYS + _GEN_PHASE1_KEYS)
def test_key_exists_in_both_languages(key: str) -> None:
    """Every i18n key must be present in both zh and en string tables."""
    for lang in ("zh", "en"):
        assert key in i18n.STRINGS[lang], f"key {key!r} missing from {lang!r}"


def test_zh_and_en_have_same_keys() -> None:
    """The zh and en tables must have exactly the same set of keys."""
    zh_keys = set(i18n.STRINGS["zh"].keys())
    en_keys = set(i18n.STRINGS["en"].keys())
    assert zh_keys == en_keys, (
        f"key mismatch: only-zh={zh_keys - en_keys}, only-en={en_keys - zh_keys}"
    )


def test_offline_explanations_name_the_real_gate() -> None:
    """The offline explanation must name the gate that actually gates.

    "The endpoint records are missing" is not the truth: those records exist
    (`docs/provenance/seqcode-registry-2026-09-25.md`). What Studio waits on is
    LPSN credentials plus a by-name lookup the Registry does not offer. The text
    has to be localised too, because a GUI user has no terminal manual open.
    """
    for lang in ("en", "zh"):
        i18n.set_language(lang)
        tooltip = i18n.tr("check_online_tooltip")
        note = i18n.tr("check_blocked_note")
        assert tooltip != "check_online_tooltip", "tooltip key not translated"
        for text in (tooltip, note):
            assert "M0" not in text, f"{lang}: blames the endpoint records"
            assert "LPSN" in text and "SeqCode" in text, f"{lang}: {text[:80]}"
            assert "check --online" in text, f"{lang}: no way out offered"
