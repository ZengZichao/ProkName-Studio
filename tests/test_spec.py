"""The PyInstaller spec: version, data assets and hidden imports it hands over.

PyInstaller is a release-time tool (the ``build`` extra), not a test dependency,
so the spec is not driven by PyInstaller here: these tests ``exec()`` it against
small pure-Python stubs that mirror the documented ``(source, dest)`` contract of
``collect_data_files`` and the recursive behaviour of ``collect_submodules``. That
validates the *spec's own logic* — which files it asks for, which excludes and
hidden imports and which version it hands to ``Analysis``/``BUNDLE`` — not
PyInstaller's internals. A real ``pyinstaller ProkNameStudio.spec`` run stays a
release-time step (and CI's ``bundle`` job).

Why it is worth testing at all: the failure this guards against is a bundle that
builds green and then dies on the user's machine at its first
``importlib.resources`` lookup, or an ``Info.plist`` that ships a version the
About box contradicts.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = REPO_ROOT / "src" / "prokname_studio"
INIT_FILE = PACKAGE_DIR / "__init__.py"
PYPROJECT_FILE = REPO_ROOT / "pyproject.toml"
SPEC_FILE = REPO_ROOT / "ProkNameStudio.spec"

#: Same regex hatchling ([tool.hatch.version]) and the spec use. Line-anchored,
#: so nothing further down the module can become the build-time declaration.
VERSION_LITERAL_RE = re.compile(r'''^__version__\s*=\s*["']([^"']+)["']''', re.MULTILINE)
#: Any quoted three-part number — a version pasted in by hand.
SEMVER_LITERAL_RE = re.compile(r"""["']\d+\.\d+\.\d+["']""")

#: Data trees the frozen app loads through ``importlib.resources``. The Studio
#: asset is the icon: without it the window opens with the platform's tile.
BUNDLED_DATA_DIRS = ("prokname/data", "prokname/benchmark/data", "prokname_studio/assets")


def _source_version() -> str:
    """The version declared by the single source of truth."""
    matches = VERSION_LITERAL_RE.findall(INIT_FILE.read_text(encoding="utf-8"))
    assert matches, f"no `__version__ = \"...\"` literal found in {INIT_FILE}"
    assert len(matches) == 1, (
        f"{INIT_FILE} has more than one line matching `__version__ = ...` "
        f"({len(matches)}). The build backend and the spec take the first match, "
        "so a second one silently forks the single source of truth."
    )
    return matches[0]


def _package_dir(package: str) -> Path:
    """Where an installed (or editable-installed, or ``src``-on-path) package lives."""
    spec = importlib.util.find_spec(package)
    assert spec and spec.submodule_search_locations, f"{package} is not importable"
    return Path(list(spec.submodule_search_locations)[0])


def _collect_data_files(package: str) -> list[tuple[str, str]]:
    """Pure-Python stand-in for ``PyInstaller.utils.hooks.collect_data_files``.

    One ``(absolute source path, destination directory inside the bundle)`` tuple
    per non-Python file, recursively, with ``__pycache__`` dropped.
    """
    root = _package_dir(package)
    found: list[tuple[str, str]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if "__pycache__" in rel.parts or path.suffix == ".py":
            continue
        found.append((str(path), "/".join((package, *rel.parts[:-1]))))
    return found


def _walk_submodules(package: str) -> list[str]:
    """Stand-in for the recursive ``collect_submodules`` (``*.py`` → module)."""
    root = _package_dir(package)
    names = {package}
    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if "__pycache__" in rel.parts:
            continue
        module = ".".join((package, *rel.with_suffix("").parts))
        names.add(module[: -len(".__init__")] if module.endswith(".__init__") else module)
    return sorted(names)


class _SpecRun:
    """What the spec handed to PyInstaller's build objects."""

    def __init__(self) -> None:
        self.analysis_kwargs: dict = {}
        self.bundle_kwargs: dict = {}
        self.exe_kwargs: dict = {}
        self.collect_submodules_calls: list[str] = []
        self.read_version = None


def _exec_spec(*, datas: list[tuple[str, str]] | None = None) -> _SpecRun:
    """exec() ProkNameStudio.spec against pure-Python PyInstaller stubs.

    ``datas`` overrides what ``collect_data_files`` reports (used to prove the
    spec's own build-time guard fires); ``None`` means the real stub walk.
    """
    run = _SpecRun()

    def _submodules_stub(package: str) -> list[str]:
        run.collect_submodules_calls.append(package)
        return _walk_submodules(package)

    def _data_files_stub(package: str, **_kwargs):
        return _collect_data_files(package) if datas is None else list(datas)

    hooks = types.ModuleType("PyInstaller.utils.hooks")
    hooks.collect_submodules = _submodules_stub
    hooks.collect_data_files = _data_files_stub
    utils = types.ModuleType("PyInstaller.utils")
    utils.hooks = hooks
    root = types.ModuleType("PyInstaller")
    root.utils = utils
    injected = {
        "PyInstaller": root,
        "PyInstaller.utils": utils,
        "PyInstaller.utils.hooks": hooks,
    }

    def _analysis(*args, **kwargs):
        run.analysis_kwargs = kwargs
        return types.SimpleNamespace(
            pure=[],
            zipped_data=[],
            scripts=[],
            binaries=[],
            zipfiles=[],
            datas=kwargs.get("datas", []),
        )

    def _exe(*args, **kwargs):
        run.exe_kwargs = kwargs
        return object()

    def _bundle(*args, **kwargs):
        run.bundle_kwargs = kwargs
        return object()

    namespace = {
        "__name__": "prokname_studio_spec",
        "__file__": str(SPEC_FILE),
        # PyInstaller injects SPECPATH (the directory holding this spec) when it
        # builds; the spec falls back to os.getcwd() for other harnesses.
        "SPECPATH": str(REPO_ROOT),
        "Analysis": _analysis,
        "PYZ": lambda *args, **kwargs: object(),
        "EXE": _exe,
        "COLLECT": lambda *args, **kwargs: object(),
        "BUNDLE": _bundle,
    }

    saved = {name: sys.modules.get(name) for name in injected}
    sys.modules.update(injected)
    try:
        code = compile(SPEC_FILE.read_text(encoding="utf-8"), str(SPEC_FILE), "exec")
        exec(code, namespace)
        run.read_version = namespace["_read_version"]
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:  # pragma: no cover - only when PyInstaller is installed
                sys.modules[name] = previous
    return run


_RUN: _SpecRun | None = None


def _run_spec() -> _SpecRun:
    """The spec, exec()ed once per session (evaluating it is pure computation)."""
    global _RUN
    if _RUN is None:
        try:
            _RUN = _exec_spec()
        except SystemExit as exc:  # the spec's own build-time guards
            pytest.fail(f"ProkNameStudio.spec refused to build: {exc}")
    return _RUN


# --------------------------------------------------------------------------- #
# the version the bundle reports
# --------------------------------------------------------------------------- #


def test_pyproject_derives_the_version_instead_of_repeating_it():
    tomllib = pytest.importorskip("tomllib")
    text = PYPROJECT_FILE.read_text(encoding="utf-8")
    data = tomllib.loads(text)

    assert "version" not in data["project"], (
        "pyproject.toml re-declares [project].version: make it dynamic again so "
        "a wheel's metadata cannot drift from prokname_studio.__version__"
    )
    assert "version" in data["project"].get("dynamic", []), (
        '[project].dynamic must list "version", otherwise the hatchling source '
        "below is inert and the build fails"
    )
    hatch_version = data.get("tool", {}).get("hatch", {}).get("version", {})
    assert hatch_version.get("path") == "src/prokname_studio/__init__.py", (
        f"[tool.hatch.version].path is {hatch_version.get('path')!r}; it must "
        "point at the single source of truth"
    )
    assert not re.search(r'^\s*version\s*=\s*["\']', text, re.MULTILINE), (
        "a hard-coded `version = \"...\"` assignment reappeared in pyproject.toml"
    )


def test_spec_derives_the_version_instead_of_repeating_it():
    text = SPEC_FILE.read_text(encoding="utf-8")
    assert not SEMVER_LITERAL_RE.search(text), (
        "ProkNameStudio.spec carries a literal version again; it must read "
        "src/prokname_studio/__init__.py through _read_version()"
    )
    assert "_read_version" in text and "CFBundleShortVersionString" in text
    plist = _run_spec().bundle_kwargs["info_plist"]
    assert plist["CFBundleShortVersionString"] == _source_version()


def test_spec_version_reader_tracks_a_bump(tmp_path):
    """The spec's own parser, exercised against a *different* version."""
    reader = _run_spec().read_version
    bumped = f"{_source_version()}.99"
    moved = tmp_path / "__init__.py"
    moved.write_text(f'__version__ = "{bumped}"\n', encoding="utf-8")
    assert reader(str(moved)) == bumped, "the spec stopped reading the source"
    assert reader(str(INIT_FILE)) == _source_version()

    silent = tmp_path / "no_version.py"
    silent.write_text('DISCLAIMER = "nothing to see"\n', encoding="utf-8")
    with pytest.raises(SystemExit):
        reader(str(silent))


# --------------------------------------------------------------------------- #
# what reaches the bundle
# --------------------------------------------------------------------------- #


def test_spec_ships_every_file_in_bundled_data_dirs():
    """A new ``data/*.json`` or ``assets/*`` must reach the app without an edit."""
    datas = _run_spec().analysis_kwargs.get("datas")
    assert datas, "Analysis() received an empty/absent datas list"

    missing = []
    for expected_dest in BUNDLED_DATA_DIRS:
        package, _, rel = expected_dest.partition("/")
        source_dir = _package_dir(package) / rel
        assert source_dir.is_dir(), f"expected {source_dir} to exist"
        on_disk = sorted(p.name for p in source_dir.iterdir() if p.is_file())
        assert on_disk, f"{source_dir} holds no files — this guard would be vacuous"
        for name in on_disk:
            shipped = any(
                Path(src).name == name
                and dest.replace("\\", "/").rstrip("/").endswith(expected_dest)
                for src, dest in datas
            )
            if not shipped:
                missing.append(f"{expected_dest}/{name}")
    assert not missing, (
        f"these on-disk assets would NOT be in the frozen bundle: {missing}. The "
        "spec collects them through collect_data_files; a hand-listed entry "
        "nobody updated is the failure mode this guards."
    )


def test_the_packaged_icon_is_the_one_the_app_loads():
    """The spec ships assets/icon.svg, and ``icons.icon_svg()`` reads that name."""
    from prokname_studio import icons

    shipped = {
        Path(src).name
        for src, dest in _run_spec().analysis_kwargs["datas"]
        if dest.replace("\\", "/").rstrip("/").endswith("prokname_studio/assets")
    }
    assert icons.ICON_FILE in shipped, f"{icons.ICON_FILE} is not collected: {shipped}"
    # and the runtime loader finds real bytes, not just a filename in a list
    assert icons.icon_svg().startswith(b"<?xml")


def test_spec_collects_both_packages():
    """The app imports the engine through its public API; the graph must not miss it."""
    run = _run_spec()
    assert run.collect_submodules_calls == ["prokname_studio", "prokname"], (
        f"collect_submodules was called for {run.collect_submodules_calls}; both "
        "this package and the engine it drives have to be walked recursively"
    )
    modules = run.analysis_kwargs["hiddenimports"]
    assert len(modules) == len(set(modules)), "duplicate hiddenimports"
    for expected in ("prokname_studio", "prokname_studio.views", "prokname",
                     "prokname.engine", "prokname.presentation"):
        assert expected in modules, f"{expected} would be missing from the bundle"


def test_spec_excludes_use_import_names():
    excludes = _run_spec().analysis_kwargs["excludes"]
    assert "vcr" in excludes, (
        "the engine's dev dependency `vcrpy` is imported as `vcr`, so excluding "
        "`vcrpy` excludes nothing"
    )
    assert "vcrpy" not in excludes
    for name in ("pytest", "pytestqt", "hypothesis", "ruff"):
        assert name in excludes


def test_spec_refuses_to_build_if_an_asset_tree_is_missing():
    """The build-time guard, exercised by making the hooks report nothing."""
    with pytest.raises(SystemExit) as excinfo:
        _exec_spec(datas=[])
    assert "collect_data_files" in str(excinfo.value), (
        "the spec should fail loudly rather than freeze an app that dies on its "
        "first importlib.resources lookup"
    )


def test_the_windowed_bundle_carries_no_console():
    kwargs = _run_spec().exe_kwargs
    assert kwargs["console"] is False, "a console window behind a desktop app"
    assert kwargs["exclude_binaries"] is True, "onedir is the supported .app layout"


def test_bundle_icon_is_either_a_real_file_or_none():
    """``icon=`` pointing at a missing file is how a bundle ships a generic tile.

    The .icns/.ico is generated from the SVG at release time by platform tooling
    CI does not have, so the spec may not name a file that is not there; it must
    say ``None`` and let the runtime SVG window icon carry the mark.
    """
    icon = _run_spec().bundle_kwargs["icon"]
    assert icon is None or Path(icon).is_file(), icon
