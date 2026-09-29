"""Every prose document ships in two languages, and English is the primary one.

The rule, shared with the engine repository: a document exists as ``NAME.md``
(English) plus ``NAME.zh.md`` (Chinese), each opening with
``[English](…) | [中文](…)`` and English listed first. English leads because the
repository is public and its readership is international; the Chinese companion
exists because the community the tool is written for works in Chinese.

For Studio the rule is not cosmetic — the interface itself is bilingual and
``tests/test_i18n_parity.py`` refuses to let a UI string exist in one language only.
Documentation is held to the same standard as the strings, because a design document
that only half the readership can read is exactly how a decision stops being
reviewable.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

SWITCH_RE = re.compile(r"\[English\]\(([^)]+)\)\s*\|\s*\[中文\]\(([^)]+)\)")
CJK_RE = re.compile(r"[㐀-䶿一-鿿]")
ASCII_LETTER_RE = re.compile(r"[A-Za-z]")

DOC_DIRS = [REPO, REPO / "docs"]

#: Documents whose Chinese companion must name the English file as authoritative.
REFERENCE_DOCS = ["docs/STUDIO_PLAN.zh.md"]

_SWITCH_HEAD_LINES = 12


def _markdown_files() -> list[Path]:
    found: list[Path] = []
    for directory in DOC_DIRS:
        if directory.is_dir():
            found.extend(sorted(directory.glob("*.md")))
    return found


def _pairs() -> list[tuple[Path, Path]]:
    out: list[tuple[Path, Path]] = []
    for path in _markdown_files():
        if path.name.endswith(".zh.md"):
            continue
        out.append((path, path.with_name(path.name[: -len(".md")] + ".zh.md")))
    return out


def test_every_english_document_has_a_chinese_companion() -> None:
    missing = sorted(
        f"{en.relative_to(REPO)} -> {zh.name}"
        for en, zh in _pairs()
        if en.is_file() and not zh.is_file()
    )
    assert not missing, (
        "these documents have no Chinese companion, so half the readership cannot "
        "read them: " + ", ".join(missing)
    )


def test_no_chinese_document_is_orphaned() -> None:
    orphans = sorted(
        path.relative_to(REPO).as_posix()
        for path in _markdown_files()
        if path.name.endswith(".zh.md")
        and not path.with_name(path.name[: -len(".zh.md")] + ".md").is_file()
    )
    assert not orphans, (
        "English is the primary document; these have no English original: "
        + ", ".join(orphans)
    )


def test_both_copies_open_with_a_language_switch_listing_english_first() -> None:
    offenders: list[str] = []
    for en, zh in _pairs():
        for path in (en, zh):
            if not path.is_file():
                continue
            head = "\n".join(path.read_text(encoding="utf-8").splitlines()[:_SWITCH_HEAD_LINES])
            match = SWITCH_RE.search(head)
            if match is None:
                offenders.append(
                    f"{path.relative_to(REPO)}: no `[English](…) | [中文](…)` line "
                    f"within its first {_SWITCH_HEAD_LINES} lines"
                )
                continue
            if head.find("[English]") > head.find("[中文]"):
                offenders.append(f"{path.relative_to(REPO)}: 中文 is listed before English")
    assert not offenders, "language switch missing or mis-ordered:\n  " + "\n  ".join(offenders)


def test_the_english_copy_is_english_and_the_chinese_copy_is_chinese() -> None:
    problems: list[str] = []
    for en, zh in _pairs():
        for path in (en, zh):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            cjk = len(CJK_RE.findall(text))
            latin = len(ASCII_LETTER_RE.findall(text))
            if path.name.endswith(".zh.md"):
                if cjk < 50:
                    problems.append(
                        f"{path.relative_to(REPO)}: only {cjk} CJK characters — "
                        "the companion is not actually translated"
                    )
            elif cjk >= latin:
                problems.append(
                    f"{path.relative_to(REPO)}: {cjk} CJK vs {latin} Latin characters — "
                    "the file named as the English original looks like the translation"
                )
    assert not problems, (
        "a document's language does not match its name:\n  " + "\n  ".join(problems)
    )


def test_reference_companions_declare_the_english_file_authoritative() -> None:
    missing = [
        name
        for name in REFERENCE_DOCS
        if (REPO / name).is_file() and "权威" not in (REPO / name).read_text(encoding="utf-8")
    ]
    assert not missing, (
        "these Chinese documents do not state that the English original is the "
        "authoritative text (权威): " + ", ".join(missing)
    )
