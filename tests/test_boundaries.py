"""The boundary between Studio and the engine, and how the docs describe it.

Studio is a consumer of `prokname`, not a layer inside it. Two things have to stay
true for that to mean something:

* the import graph — Studio calls the engine's public API and never reaches into
  its CLI or its internals;
* the documentation — the dependency is described by what is published (a package
  name, a repository URL), never by a path on one developer's disk. A doc that
  says "install the folder next to this one" is true on exactly one machine and
  wrong on every other, including the CI runner and the release build.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src" / "prokname_studio"

#: Engine modules Studio is allowed to import. Add to this list on purpose: every
#: entry is a contract the engine has to keep for Studio to work.
ALLOWED_ENGINE_IMPORTS = {
    "prokname",
    "prokname._atomic",
    "prokname.dedup",
    "prokname.dedup.model",
    "prokname.diagnostics",
    "prokname.engine",
    "prokname.engine.data",
    "prokname.engine.gender",
    "prokname.engine.generate",
    "prokname.engine.orthography",
    "prokname.presentation",
    "prokname.presentation.decision",
    "prokname.presentation.theme",
    "prokname.routing",
    "prokname.storage",
    "prokname.storage.model",
}

#: A path that only resolves on somebody's disk. Repository URLs and package
#: names are how the two projects refer to each other.
LOCAL_PATH_PATTERNS = (
    re.compile(r"\.\./ProkName"),
    re.compile(r"ProkName-项目代码"),
    re.compile(r"ProkName-Studio-项目代码"),
    re.compile(r"(?:^|[\s\"'`(])~/Documents"),
    re.compile(r"(?:^|[\s\"'`(])/Users/"),
    re.compile(r"file://"),
)

#: Every document a reader acts on, design specification included. None of them may
#: name a path that resolves on one machine: the front end is published, installed and
#: frozen on computers it has never met, and a doc that says "install the folder next
#: to this one" is true on exactly one machine and wrong on every other.
LIVING_DOCS = (
    "README.md", "README.zh.md", "CHANGELOG.md", "CHANGELOG.zh.md",
    "CONTRIBUTING.md", "CONTRIBUTING.zh.md",
    "docs/STUDIO_PLAN.md", "docs/STUDIO_PLAN.zh.md",
)


def _prokname_imports(path: Path) -> list[str]:
    found: list[str] = []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative: inside this package, not the engine
                continue
            names = [node.module or ""]
        else:
            continue
        found.extend(n for n in names if n.split(".")[0] == "prokname")
    return found


def test_studio_only_imports_the_engines_public_api():
    offenders = sorted({
        module
        for path in sorted(SRC.rglob("*.py"))
        for module in _prokname_imports(path)
        if module not in ALLOWED_ENGINE_IMPORTS
    })
    assert not offenders, (
        f"Studio reached into an engine module outside the contract: {offenders}"
    )


def test_studio_never_imports_the_engine_cli():
    """A command-line entry point is not an API to depend on.

    The engine's CLI is free to change argument parsing, output and exit codes; a
    GUI that imported it would inherit those changes as bugs.
    """
    offenders = [
        f"{path.relative_to(REPO)}: {module}"
        for path in sorted(SRC.rglob("*.py"))
        for module in _prokname_imports(path)
        if module == "prokname.cli" or module.startswith("prokname.cli.")
    ]
    assert not offenders, f"Studio reaches into the engine's CLI: {offenders}"


def test_nothing_still_imports_prokname_studio():
    """The old in-engine location is gone: importing it is an AttributeError.

    Only import statements are checked. ``io.github.prokname.studio`` is a bundle
    identifier and the CHANGELOG records what the package used to be called; both
    spell the retired name without reaching for it.
    """
    offenders = []
    for path in list(sorted(SRC.rglob("*.py"))) + list(sorted((REPO / "tests").rglob("*.py"))):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                names = [node.module]
            offenders += [f"{path.relative_to(REPO)}: {n}" for n in names
                          if n == "prokname.studio" or n.startswith("prokname.studio.")]
    assert not offenders, f"still importing the retired module: {offenders}"


def test_the_readmes_do_not_advertise_the_retired_entry_point():
    """A reader must not be told to run something that no longer exists."""
    offenders = []
    for name in ("README.md", "README.zh.md"):
        text = (REPO / name).read_text(encoding="utf-8")
        for pattern in (r"prokname\.studio\b", r"prokname\s+studio\b", r"\[gui\]"):
            if re.search(pattern, text):
                offenders.append(f"{name}: {pattern}")
    assert not offenders, f"the retired GUI entry point survived in the READMEs: {offenders}"


def test_the_living_docs_describe_the_dependency_by_what_is_published():
    """The engine is named as a package and a repository, never as a folder."""
    for name in LIVING_DOCS:
        text = (REPO / name).read_text(encoding="utf-8")
        for pattern in LOCAL_PATH_PATTERNS:
            assert not pattern.search(text), f"{name} quotes a local path: {pattern.pattern}"


def test_the_readme_states_the_dependency_the_package_declares():
    """A README whose install steps contradict pyproject is the bug, not the fix."""
    import tomllib

    declared = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    engine = [d for d in declared["project"]["dependencies"]
              if re.split(r"[\[><=! ]", d, maxsplit=1)[0] == "prokname"]
    assert engine, "pyproject.toml no longer declares prokname as a dependency"

    for name in ("README.md", "README.zh.md"):
        text = (REPO / name).read_text(encoding="utf-8")
        assert "prokname>=" in text or "github.com/ZengZichao/ProkName" in text, (
            f"{name} does not tell a reader where the engine comes from")
        assert "pip install" in text, f"{name} has no install step"


def test_the_engine_is_not_a_runtime_path_dependency():
    """No path/source-directive may quietly turn the sibling checkout into a dep."""
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    assert "tool.uv.sources" not in text and "tool.pipenv" not in text
    assert not re.search(r"prokname\s*=\s*\{[^}]*path", text), (
        "pyproject pins prokname to a local path; declare the published "
        "requirement and let the resolver find it")
