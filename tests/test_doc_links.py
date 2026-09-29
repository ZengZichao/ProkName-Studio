"""No document may link to something the reader cannot open.

The Studio plan document carried a link to a `USAGE.zh.md#prokname-studio` section
that left the repository — with the command it described — at the 2026-09-29 split.
Nothing in the suite noticed: the other gates read code, licence strings and the
bundle description, and none of them resolves a markdown link.

A front end whose whole premise is that it points at the published engine rather
than at a folder on one developer's disk has to hold its documentation to the same
standard: a link that resolves on nobody's machine is that premise failing.

Anchors are generated the way GitHub does it — lower-cased, punctuation dropped,
spaces to hyphens, CJK kept — so a heading in either language resolves.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DOC_ROOTS = [REPO, REPO / "docs"]
SKIP_PARTS = {
    ".venv", ".git", "__pycache__", ".pytest_cache", ".ruff_cache",
    "build", "dist", "node_modules",
}

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
#: A link written inside a code span is documentation *about* the syntax, not a link
#: to follow — CONTRIBUTING writes `[English](…) | [中文](…)` to explain the convention.
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
EXTERNAL_PREFIXES = ("http://", "https://", "mailto:", "tel:", "//")


def _links(text: str) -> list[str]:
    return LINK_RE.findall(INLINE_CODE_RE.sub("", text))


def _markdown_files() -> list[Path]:
    found: list[Path] = []
    for root in DOC_ROOTS:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.md")):
            if SKIP_PARTS & set(path.relative_to(REPO).parts):
                continue
            found.append(path)
    return found


def _slug(heading: str) -> str:
    text = re.sub(r"[*`_]", "", heading.strip())
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    return text.strip().lower().replace(" ", "-")


def _anchors(text: str) -> set[str]:
    out: set[str] = set()
    inside = False
    for line in text.splitlines():
        if FENCE_RE.match(line):
            inside = not inside
            continue
        if inside:
            continue
        match = re.match(r"^#{1,6}\s+(.*)$", line)
        if match:
            out.add(_slug(match.group(1)))
    return out


_ANCHOR_CACHE: dict[Path, set[str]] = {}


def _anchors_of(path: Path) -> set[str]:
    if path not in _ANCHOR_CACHE:
        _ANCHOR_CACHE[path] = _anchors(path.read_text(encoding="utf-8"))
    return _ANCHOR_CACHE[path]


def test_no_relative_link_points_at_a_missing_file() -> None:
    broken = []
    for path in _markdown_files():
        for target in _links(path.read_text(encoding="utf-8")):
            if target.startswith(EXTERNAL_PREFIXES):
                continue
            file_part = target.partition("#")[0]
            if file_part and not (path.parent / file_part).resolve().exists():
                broken.append(f"{path.relative_to(REPO)}: {target}")
    assert not broken, (
        "these documentation links resolve to nothing a reader can open:\n  "
        + "\n  ".join(sorted(broken))
    )


def test_every_in_page_anchor_matches_a_heading() -> None:
    broken = []
    for path in _markdown_files():
        own = _anchors_of(path)
        for target in _links(path.read_text(encoding="utf-8")):
            if target.startswith(EXTERNAL_PREFIXES) or "#" not in target:
                continue
            file_part, _, fragment = target.partition("#")
            if not fragment:
                continue
            if file_part:
                resolved = (path.parent / file_part).resolve()
                if not resolved.is_file():
                    continue
                available = _anchors_of(resolved)
            else:
                available = own
            if fragment not in available:
                broken.append(f"{path.relative_to(REPO)}: {target}")
    assert not broken, (
        "these links name an anchor no heading produces:\n  " + "\n  ".join(sorted(broken))
    )


def test_contents_list_covers_every_top_level_heading() -> None:
    """The README's Contents block is how a reader navigates; a section missing from it
    is a section nobody finds."""
    problems = []
    for name in ("README.md", "README.zh.md"):
        path = REPO / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        listed = set(re.findall(r"\]\(#([^)]+)\)", text))
        inside = False
        actual = set()
        for line in text.splitlines():
            if FENCE_RE.match(line):
                inside = not inside
                continue
            if inside:
                continue
            match = re.match(r"^##\s+(.*)$", line)
            if match:
                slug = _slug(match.group(1))
                if slug in _slug("Contents") or slug in _slug("目录"):
                    continue
                actual.add(slug)
        missing = sorted(actual - listed)
        if missing:
            problems.append(f"{name}: not listed in Contents -> {missing}")
    assert not problems, "\n  ".join(problems)


def test_no_document_links_to_the_placeholder_organisation() -> None:
    for path in _markdown_files():
        assert "github.com/prokname/" not in path.read_text(encoding="utf-8"), (
            f"{path.relative_to(REPO)} still links to the placeholder organisation"
        )


#: The organisation that did not exist. Documentation is not the only place a URL
#: hides — pyproject, CITATION.cff and HTTP User-Agent strings carry one too.
PLACEHOLDER = "github.com/prokname/"

#: A path that resolves on one machine only. Matched as `home/<user>/`, not as a bare
#: prefix: `tests/test_boundaries.py` keeps a regex mentioning `/Users/` as the very rule
#: it enforces, and that is the prohibition being written down, not a path being used.
MACHINE_PATH_RES = (
    re.compile(r"/Users/[A-Za-z0-9._-]+/"),
    re.compile(r"/Volumes/[A-Za-z0-9._-]+/"),
    re.compile(r"C:\\Users\\[^\\\s]+\\"),
    re.compile(r"~/Documents/[A-Za-z0-9._-]+"),
)

#: This file has to spell the placeholder URL it forbids.
SELF = {Path(__file__).name}


def _publishable_text_files() -> list[Path]:
    """Exactly the files a commit could carry: tracked plus untracked-not-ignored."""
    import subprocess

    try:
        proc = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=REPO, capture_output=True, text=True, timeout=60, check=True,
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - no git
        return []
    out = []
    for rel in proc.stdout.splitlines():
        path = REPO / rel
        if not path.is_file():
            continue
        try:
            path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # binary asset, not a place a URL hides
        out.append(path)
    return out


def test_no_published_file_references_the_placeholder_organisation() -> None:
    offenders = [
        path.relative_to(REPO).as_posix()
        for path in _publishable_text_files()
        if path.name not in SELF and PLACEHOLDER in path.read_text(encoding="utf-8")
    ]
    assert not offenders, (
        f"'{PLACEHOLDER}' is not a repository anyone can reach; it still appears in: "
        + ", ".join(sorted(offenders))
    )


def test_no_published_file_carries_a_machine_specific_path() -> None:
    offenders = []
    for path in _publishable_text_files():
        if path.name in SELF:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in MACHINE_PATH_RES:
            hit = pattern.search(text)
            if hit:
                offenders.append(f"{path.relative_to(REPO)}: {hit.group(0)}")
    assert not offenders, (
        "these files resolve only on one developer's disk: "
        + ", ".join(sorted(offenders))
    )
