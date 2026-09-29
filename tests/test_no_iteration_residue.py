"""No published file may carry internal iteration residue.

Studio is published as a single v0.1.0 release, so a reader sees one state of the
software. Notes from how it was built are defects for different reasons:

* **Review-finding IDs** (`(M16)`, `B5`, `P2-1`, and any ID written as a citation
  such as `defect M4` or `review B1`) cite numbered findings in reports that are
  not distributed with this repository, so the citation delegates the reasoning to
  a document nobody can open. The comment has to carry the reasoning, which these
  comments already do. A path may not cite one either.
* **Design-document citations** (`plan v1.3 §2.4`, `review report §2 M5`,
  `附录 A4`) are the
  same failure: an external fact belongs in `docs/provenance/` of the engine
  repository with a commit pin, never in a comment here.
* **Superseded counts and `## [Unreleased]`** describe a state that does not exist:
  a changelog that restamps history with today's test totals, or still carries an
  unreleased heading next to a `date-released`.

Milestones (M0..M5) and the engine's benchmark sets (A / B1 / B2 / C / D) are shared
vocabulary and stay: the bare-ID regex below stops at M6 and skips B1..B3 and
C1..C3. A milestone or suite cited *as if* it were a review finding is still
residue, which is what the citation regex is for.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

FINDING_ID = re.compile(
    r"\b(?:N\d{1,2}|M(?:[6-9]|1[0-9])[a-z]?|B[4-6]|C[4-9]|G\d{1,2}|P[1-3]-\d+)\b")

#: An ID preceded by a citation word is a report pointer even when the letters
#: alone would read as a milestone (M0..M5) or a benchmark set (B1..B3, C1..C3).
CITATION_PHRASE = re.compile(
    r"\b(?:defects?|reviews?|findings?|bugs?|issues?|rounds?)\s+"
    r"(?:item\s+)?[A-Z]\d{1,2}[a-z]?\b", re.I)

#: A file named after a review round says so in its own path. B and C are left out
#: because the engine's benchmark suites really are called B1-set and C-set.
RESIDUE_IN_PATH = re.compile(r"(?:^|_)(?:m|n|g)\d+(?:$|_|\.)", re.I)

DESIGN_DOC_CITATION = re.compile(
    r"plan v\d|plan §|engineering plan|benchmark (design )?draft v|review report|"
    r"审阅报告|工程方案|基准测试集设计草案|code review|review round|review item|"
    r"review finding|复核项|审阅项|评审项|附录\s*[A-Z]\d", re.I)

UNRELEASED_HEADING = re.compile(r"^## \[Unreleased\]", re.M)

#: Counts that were true of an older tree. `[gui]`-tier totals belonged to the
#: engine repository before the front end was its own project.
SUPERSEDED_COUNTS = ("1152", "1061", "954", "104 Studio")

#: A guard must spell out what it forbids.
ALLOWED_FILES = {"tests/test_no_iteration_residue.py"}

NEGATIVE_CONTROLS = [
    "# version handling (review item N18)",
    "# LPSN (ICNP authority; plan v1.3, sections 6.1 / 6.4)",
    "## [Unreleased]",
    "# the guard is wrong here — defect M4, over-blocking half",
]


def _publishable_text_files() -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO, capture_output=True, text=True, timeout=60, check=True,
    )
    out = []
    for rel in proc.stdout.splitlines():
        path = REPO / rel
        if not path.is_file() or rel in ALLOWED_FILES:
            continue
        if Path(rel).suffix.lower() in {".svg", ".png", ".icns", ".dmp", ".so", ".pyc"}:
            continue
        try:
            path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        out.append(path)
    return out


def _publishable_paths() -> list[str]:
    proc = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=REPO, capture_output=True, text=True, timeout=60, check=True,
    )
    return [r for r in proc.stdout.splitlines() if r not in ALLOWED_FILES]


def test_the_guard_detects_the_shapes_it_forbids() -> None:
    text = "\n".join(NEGATIVE_CONTROLS)
    assert FINDING_ID.search(text), "the ID regex does not match a review ID"
    assert CITATION_PHRASE.search(text), "the citation regex does not match 'defect M4'"
    assert DESIGN_DOC_CITATION.search(text), "the citation regex does not match a plan reference"
    assert UNRELEASED_HEADING.search(text), "the changelog regex does not match [Unreleased]"
    assert RESIDUE_IN_PATH.search("tests/test_engine_m9_verification.py"), (
        "the path regex does not match a test named after a review round")


def test_no_review_finding_ids() -> None:
    offenders = []
    for path in _publishable_text_files():
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            hit = FINDING_ID.search(line) or CITATION_PHRASE.search(line)
            if hit:
                offenders.append(f"{path.relative_to(REPO)}:{n} {hit.group(0)}")
    assert not offenders, (
        "these lines cite a numbered finding no reader can open (state the "
        "guarantee in the comment instead):\n  " + "\n  ".join(offenders[:25])
    )


def test_no_file_is_named_after_a_review_round() -> None:
    offenders = [rel for rel in _publishable_paths()
                 if RESIDUE_IN_PATH.search(Path(rel).stem)]
    assert not offenders, (
        "these paths carry a review-round number no reader can resolve:\n  "
        + "\n  ".join(offenders)
    )


def test_no_citations_to_undistributed_design_documents() -> None:
    offenders = []
    for path in _publishable_text_files():
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            hit = DESIGN_DOC_CITATION.search(line)
            if hit:
                offenders.append(f"{path.relative_to(REPO)}:{n} {hit.group(0)}")
    assert not offenders, (
        "these lines cite a document that is not distributed with this source:\n  "
        + "\n  ".join(offenders[:25])
    )


def test_changelog_is_cut_and_carries_no_superseded_counts() -> None:
    problems = []
    for name in ("CHANGELOG.md", "CHANGELOG.zh.md"):
        path = REPO / name
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if UNRELEASED_HEADING.search(text):
            problems.append(f"{name} still has a ## [Unreleased] heading")
        for stale in SUPERSEDED_COUNTS:
            if stale in text:
                problems.append(f"{name} restates the superseded figure {stale!r}")
    assert not problems, (
        "the changelog describes a state that does not exist:\n  "
        + "\n  ".join(problems)
    )
