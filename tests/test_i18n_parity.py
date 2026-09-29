"""i18n table parity — checked by reading the source, not by importing Qt.

Closes the review's residual uncertainty ("``i18n.py``: whether the zh/en key
sets correspond 1:1 was not compared line by line"). The STRINGS table is a
plain literal dict, so it is read straight out of the module source: the parity
verdict does not depend on a widget being constructed, and a key that only exists
in one language fails here as a *table* problem rather than as a blank label in
somebody's screenshot.

Two parity gaps this guard is written against:

* a key present in one language only → ``tr()`` silently falls back to the raw
  key (or to the other language) in the shipped UI;
* a key referenced by a view but absent from both tables → the UI shows
  ``"gen_stem"`` to the user.

The scanners deliberately distinguish keys from *display text*: ``tr()`` falls
back to its argument unchanged, which the language picker uses to keep
"中文"/"English" untranslated. See :data:`KEY_NAME` for the convention that
separates the two, and the positive-control tests below for the proof that
ignoring display text does not blind the scanner to a missing key.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest
from prokname.presentation import decision

STUDIO_DIR = Path(__file__).resolve().parents[1] / "src" / "prokname_studio"
I18N_FILE = STUDIO_DIR / "i18n.py"

_LANGS = ("zh", "en")

# -- what counts as a translation key ---------------------------------------
# ``i18n.tr()`` is ``STRINGS[lang].get(key, key)``: a string that is not a key
# comes back unchanged.  The language picker deliberately exploits that, since
# a language must be spelled the same way in every UI language::
#
#     _LANG_ITEMS = [("lang_auto", "auto"), ("中文", "zh"), ("English", "en")]
#                                  ^ display names, not keys
#
# So ``("中文", "zh")`` must not be reported as an untranslated key.  It is
# recognisable without a hardcoded exclusion list, because keys follow a strict
# convention in this project: every key of the STRINGS tables is a
# lowercase-initial ASCII identifier ("nav_generate", "gen_male",
# "source_MAG"), which display text is not.  Only the *item tables* filter on
# that shape — a literal ``tr("...")`` argument is taken verbatim, because
# writing it at all means it is meant as a key.  The convention is asserted by
# test_translation_keys_follow_the_naming_convention below, so a genuine key can
# never hide from the item-table scanner by breaking it: it fails that test
# instead of passing unnoticed.
KEY_NAME = re.compile(r"\A[a-z][A-Za-z0-9_]*\Z")


def is_translation_key(candidate: str) -> bool:
    """True for an i18n key, False for display text such as "English"."""
    return bool(KEY_NAME.fullmatch(candidate))


def strings_tables() -> dict[str, dict[str, str]]:
    """The STRINGS literal of studio/i18n.py, evaluated without importing Qt."""
    tree = ast.parse(I18N_FILE.read_text(encoding="utf-8"))
    for node in tree.body:
        targets: list[ast.expr] = []
        if isinstance(node, ast.Assign):
            targets = list(node.targets)
        elif isinstance(node, ast.AnnAssign):  # STRINGS: dict[...] = {...}
            targets = [node.target]
        if any(isinstance(t, ast.Name) and t.id == "STRINGS" for t in targets):
            return ast.literal_eval(node.value)
    raise AssertionError("STRINGS table not found in studio/i18n.py")


def _source_files() -> list[Path]:
    return sorted(STUDIO_DIR.rglob("*.py"))


# ``(?<![A-Za-z0-9_])`` stops "str(...)" / "_ctr(...)" from being read as a
# tr() call; the "{" exclusion skips the dynamic families built as
# ``tr(f"category_{value}")`` / ``tr(f"gender_{value}")`` in i18n.py — those
# guard themselves with ``if f"category_{value}" in STRINGS[lang]``, so an
# unknown value falls back to the raw engine value instead of a key.
_TR_CALL = re.compile(r"""(?<![A-Za-z0-9_])tr\(\s*f?(['"])([^'"\n{}]+)\1""")


def _literal_tr_keys() -> set[str]:
    """Every literal passed to ``tr(...)`` anywhere in the Studio sources.

    A *literal* argument is unambiguously meant to be a key, so it is taken
    verbatim and never shape-filtered — an accidental ``tr("Chinees")`` has to
    fail the parity check, not slip through a heuristic.
    """
    keys: set[str] = set()
    for path in _source_files():
        keys.update(
            match.group(2) for match in _TR_CALL.finditer(path.read_text(encoding="utf-8"))
        )
    return keys


def _item_table_keys(studio_dir: Path = STUDIO_DIR) -> set[str]:
    """Keys of the ``(i18n_key, display_or_value)`` combo tables in the views.

    Only entries that name a key are returned: the language picker's table
    mixes one key (``lang_auto``) with two display names, and the display names
    are filtered out by the convention documented on :data:`KEY_NAME`.
    """
    keys: set[str] = set()
    for path in sorted(studio_dir.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            target = node.targets[0] if isinstance(node, ast.Assign) else node.target
            name = getattr(target, "id", "")
            if not name.endswith("_ITEMS") or not isinstance(node.value, (ast.List,)):
                continue
            for element in node.value.elts:
                if isinstance(element, ast.Tuple) and element.elts:
                    first = element.elts[0]
                    if isinstance(first, ast.Constant) and isinstance(first.value, str):
                        if is_translation_key(first.value):
                            keys.add(first.value)
    return keys


def keys_missing_from_both(used: set[str], tables: dict[str, dict[str, str]]) -> set[str]:
    """The parity verdict shared by the view scan and its positive controls."""
    return {key for key in used if key not in tables["zh"] or key not in tables["en"]}


@pytest.fixture(scope="module")
def tables() -> dict[str, dict[str, str]]:
    return strings_tables()


def test_zh_and_en_have_exactly_the_same_keys(tables):
    """M-1: no key may exist in only one language."""
    zh, en = set(tables["zh"]), set(tables["en"])
    assert zh == en, f"only-zh={sorted(zh - en)} only-en={sorted(en - zh)}"


def test_no_translation_is_empty_or_whitespace(tables):
    for lang in _LANGS:
        empty = [k for k, v in tables[lang].items() if not str(v).strip()]
        assert not empty, f"{lang} has empty values: {empty}"


def test_no_unsubstituted_format_placeholder(tables):
    """A value must not carry a ``{}``/``%s`` the UI never fills in."""
    offenders = {
        f"{lang}:{key}"
        for lang in _LANGS
        for key, value in tables[lang].items()
        if re.search(r"\{\}|\{\d|\{[0-9]+\}|%s|%d", str(value))
    }
    assert not offenders, f"empty/unfilled format placeholders: {sorted(offenders)}"


def test_both_languages_agree_on_placeholders(tables):
    """zh and en must interpolate the same number of named fields."""
    def fields(value: str) -> tuple[str, ...]:
        return tuple(sorted(re.findall(r"\{(\w+)\}", str(value))))

    mismatched = {
        key for key in tables["en"] if fields(tables["en"][key]) != fields(tables["zh"][key])
    }
    assert not mismatched, f"placeholder mismatch: {sorted(mismatched)}"


def test_every_key_used_by_the_views_exists_in_both_tables(tables):
    used = _literal_tr_keys() | _item_table_keys()
    assert used, "the scanner found no i18n keys — the test itself is broken"
    # Positive control against the tempting wrong fix (silently narrowing the
    # scanners): keys read out of the item tables of every view must still be
    # seen, including "lang_auto", which shares its table with the two language
    # display names that ARE ignored.
    seen_from_tables = {
        "lang_auto",  # main_window._LANG_ITEMS
        "source_MAG",  # project_view / route_view (upper-case segment, still a key)
        "type_feature",  # gen_view.TYPE_ITEMS
        "near_match_whole",  # check_view.NEAR_MATCH_MODE_ITEMS
        "route_icnp_auto",  # route_view.ICNP_OCCUPIED_ITEMS
        "proj_meta_any",  # project_view.DATA_SOURCE_ITEMS
    }
    lost = seen_from_tables - used
    assert not lost, f"the key scanner stopped seeing real keys: {sorted(lost)}"
    missing = keys_missing_from_both(used, tables)
    assert not missing, f"views reference untranslated keys: {sorted(missing)}"


def test_translation_keys_follow_the_naming_convention(tables):
    """Guard for :func:`is_translation_key`: the shape filter may only skip
    non-keys, because every real key obeys the convention it checks for.
    """
    offenders = {
        f"{lang}:{key}" for lang in _LANGS for key in tables[lang] if not is_translation_key(key)
    }
    assert not offenders, f"keys outside the [a-z][A-Za-z0-9_]* convention: {sorted(offenders)}"


def test_a_key_referenced_by_an_item_table_still_goes_red(tmp_path, tables):
    """The scanner is not neutered: an untranslated combo entry is reported."""
    module = tmp_path / "regression_view.py"
    module.write_text(
        "SOME_MODE_ITEMS = [\n"
        "    ('type_feature', 'feature'),\n"
        "    ('zh_only_key_absent_everywhere', 'x'),\n"
        "    ('中文', 'zh'),\n"
        "]\n",
        encoding="utf-8",
    )
    found = _item_table_keys(tmp_path)
    assert found == {"type_feature", "zh_only_key_absent_everywhere"}, found
    assert keys_missing_from_both(found, tables) == {"zh_only_key_absent_everywhere"}


def test_decision_layer_labels_are_translated(tables):
    """Every badge/label the decision layer can emit must be bilingual."""
    emitted = set(decision.STYLE_COLORS) | {decision.INFERRED_GENDER_HINT_KEY}
    missing = {key for key in emitted if key not in tables["zh"] or key not in tables["en"]}
    assert not missing, f"decision labels missing from i18n: {sorted(missing)}"


def test_tr_never_falls_back_to_the_raw_key(tables):
    """With a complete table, tr() of any known key is never the key itself."""
    for lang in _LANGS:
        for key, value in tables[lang].items():
            assert value != key, f"{lang}:{key} is its own translation"
