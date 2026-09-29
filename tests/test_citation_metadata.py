"""CITATION.cff is a mirror, so it needs a watchdog (the engine has one).

Studio's version is declared once, in ``src/prokname_studio/__init__.py``, and read
at build time by hatchling (``[tool.hatch.version]``) and by the PyInstaller spec.
``CITATION.cff`` is plain YAML: it cannot execute that file, so it keeps two literal
copies of the version plus a release date, an author and a repository URL that also
live in ``pyproject.toml``.

A citation record is the one artefact people actually act on years from now, so a
drift here is worse than a drift in a comment. These tests fail if any mirror moves
away from the source it mirrors, or from its counterpart in the other repository
language.

Nothing here imports PySide6: the literals are read from disk, so the gate runs even
when there is no Qt platform to initialise.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
INIT_FILE = REPO / "src" / "prokname_studio" / "__init__.py"
PYPROJECT = REPO / "pyproject.toml"
CFF_FILE = REPO / "CITATION.cff"
CHANGELOG = REPO / "CHANGELOG.md"
CHANGELOG_ZH = REPO / "CHANGELOG.zh.md"
README = REPO / "README.md"
README_ZH = REPO / "README.zh.md"

#: Same anchored regex the build backend and tests/test_spec.py use, so a runtime
#: re-binding of ``__version__`` can never become the build-time declaration.
VERSION_LITERAL_RE = re.compile(r'''^__version__\s*=\s*["']([^"']+)["']''', re.MULTILINE)
CFF_VERSION_RE = re.compile(r'''^\s*version:\s*["']?([^"'\s#]+)["']?\s*''', re.MULTILINE)
CFF_DATE_RE = re.compile(r'''^\s*date-released:\s*["']?(\d{4}-\d{2}-\d{2})["']?\s*''', re.MULTILINE)
CFF_ORCID_RE = re.compile(r'''^\s*orcid:\s*["']?(\S+?)["']?\s*$''', re.MULTILINE)
CFF_REPO_RE = re.compile(r'''^\s*repository-code:\s*["'](\S+)["']''', re.MULTILINE)
RELEASE_HEADING_RE = re.compile(r"^## \[(\d+\.\d+\.\d+)\] - (\d{4}-\d{2}-\d{2})$", re.MULTILINE)

ORCID = "https://orcid.org/0000-0001-6553-970X"
EXPECTED_URL = "https://github.com/ZengZichao/ProkName-Studio"


def _source_version() -> str:
    """The version declared by the single source of truth."""
    matches = VERSION_LITERAL_RE.findall(INIT_FILE.read_text(encoding="utf-8"))
    assert matches, f"no `__version__ = \"...\"` literal found in {INIT_FILE}"
    assert len(set(matches)) == 1, f"{INIT_FILE} declares more than one version: {matches}"
    return matches[0]


def _pyproject() -> dict:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def test_citation_file_exists_and_is_cff_1_2():
    assert CFF_FILE.is_file(), "CITATION.cff is missing: Studio has no citation record"
    text = CFF_FILE.read_text(encoding="utf-8")
    assert text.startswith("cff-version: 1.2.0"), "CITATION.cff must declare cff-version 1.2.0"


def test_cff_version_mirrors_match_the_source_literal():
    """Both mirrors (record and preferred-citation) must equal the one declaration."""
    expected = _source_version()
    found = CFF_VERSION_RE.findall(CFF_FILE.read_text(encoding="utf-8"))
    assert len(found) == 2, (
        f"CITATION.cff is expected to mirror the version exactly twice (record + "
        f"preferred-citation); found {len(found)}: {found}"
    )
    assert set(found) == {expected}, (
        f"CITATION.cff says {sorted(set(found))} but {INIT_FILE.relative_to(REPO)} "
        f"declares {expected!r} — bump the mirrors together with the release"
    )


def test_pyproject_does_not_fork_the_version():
    """hatchling reads the literal; a hand-written `version =` here would drift."""
    data = _pyproject()
    assert "version" not in data["project"], (
        "pyproject.toml must keep version dynamic and read __version__ from "
        "src/prokname_studio/__init__.py"
    )
    assert data["tool"]["hatch"]["version"]["path"] == "src/prokname_studio/__init__.py"


def test_cff_and_pyproject_agree_on_author_orcid_and_url():
    data = _pyproject()
    authors = data["project"]["authors"]
    assert [a["name"] for a in authors] == ["Zichao Zeng"], (
        f"pyproject authors drifted: {authors}"
    )

    text = CFF_FILE.read_text(encoding="utf-8")
    assert "family-names: \"Zeng\"" in text and "given-names: \"Zichao\"" in text, (
        "CITATION.cff must attribute the same author pyproject.toml declares"
    )
    orcids = set(CFF_ORCID_RE.findall(text))
    assert orcids == {ORCID}, f"CITATION.cff ORCID mirrors drifted: {sorted(orcids)}"

    urls = set(CFF_REPO_RE.findall(text))
    assert urls == {EXPECTED_URL}, (
        f"CITATION.cff repository-code must be the Studio repository, got {sorted(urls)}"
    )
    for key in ("Homepage", "Source", "Issues"):
        value = data["project"]["urls"][key]
        assert "prokname/prokname" not in value.lower(), (
            f"pyproject [project.urls] {key} still points at the placeholder org: {value}"
        )
    assert data["project"]["urls"]["Homepage"] == EXPECTED_URL


def test_author_email_is_the_declared_contact_in_both_records():
    """CFF carries no e-mail; the two places that do must agree."""
    data = _pyproject()
    emails = {a["email"] for a in data["project"]["authors"]}
    assert emails == {"zengzichao@sjtu.edu.cn"}, (
        f"pyproject author e-mail drifted to {sorted(emails)}; CITATION.cff and the "
        "README cite sections name the same author and must stay in step"
    )


def test_cff_release_date_matches_the_cut_changelog_heading():
    """The date a reader cites must be the date the release section claims."""
    cff_dates = set(CFF_DATE_RE.findall(CFF_FILE.read_text(encoding="utf-8")))
    assert len(cff_dates) == 1, f"CITATION.cff carries conflicting dates: {sorted(cff_dates)}"
    cff_date = cff_dates.pop()

    version = _source_version()
    for path in (CHANGELOG, CHANGELOG_ZH):
        headings = dict(
            (v, d) for v, d in RELEASE_HEADING_RE.findall(path.read_text(encoding="utf-8"))
        )
        assert version in headings, (
            f"{path.name} has no cut `## [{version}] - YYYY-MM-DD` heading — an "
            "unreleased CHANGELOG cannot back a date-released citation"
        )
        assert headings[version] == cff_date, (
            f"CITATION.cff date-released is {cff_date} but {path.name} cuts "
            f"[{version}] at {headings[version]}"
        )


def test_readme_cite_sections_name_the_author_with_orcid_in_both_languages():
    """English is the primary document; the Chinese one mirrors it, or neither is cited."""
    for path in (README, README_ZH):
        text = path.read_text(encoding="utf-8")
        assert "Zichao Zeng" in text, f"{path.name} does not name the author"
        assert ORCID in text, f"{path.name} is missing the author's ORCID link"
        assert "CITATION.cff" in text, f"{path.name} does not point at CITATION.cff"
