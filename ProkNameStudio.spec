# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for ProkName Studio (macOS .app, onedir mode).

Build:
    cd ProkName-Studio
    .venv/bin/pip install -e ".[build]"
    .venv/bin/pyinstaller ProkNameStudio.spec --noconfirm

Output:
    dist/ProkName Studio.app  — double-click to launch (no Python needed)

Notes:
- onedir mode: the .app bundle contains a proper MacOS/ directory with the
  executable plus a Frameworks/ directory with shared libraries. This is the
  recommended structure for macOS .app bundles (onefile is deprecated for .app).
- --windowed (console=False): no terminal/console window (native macOS app).
- Version: read out of src/prokname_studio/__init__.py — the single source of
  truth for Studio's own version — instead of repeating the literal here. The
  *engine's* version is not stamped into the bundle: Studio reports it at runtime
  from the installed ``prokname`` distribution, so a frozen app can never claim
  an engine version it does not actually carry.
- Data assets: collected with
  PyInstaller.utils.hooks.collect_data_files() for both packages, so any new JSON
  under prokname/data/ or prokname/benchmark/data/, and any new file under
  prokname_studio/assets/, ships automatically. A hand-maintained list silently
  dropped new assets, and CI's bundle job only compares module sets, never datas.
- The SVG icon is packaged as data (the app rasterises it at runtime through
  importlib.resources). A *bundle* icon is a different artifact: macOS wants
  .icns, Windows wants .ico, and neither can be the SVG itself. See
  :func:`_bundle_icon` for how it is produced and what happens when it is absent.
"""

import os
import re

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None

# --- version: single source of truth ----------------------------------------
# PyInstaller injects SPECPATH (directory holding this file); os.getcwd() is a
# fallback for tooling that exec()s the spec outside a build (e.g. the
# consistency test). The regex is the same `__version__` literal the build
# backend reads via [tool.hatch.version].
_SPECPATH = globals().get("SPECPATH") or os.getcwd()
_VERSION_FILE = os.path.join(_SPECPATH, "src", "prokname_studio", "__init__.py")
_VERSION_RE = re.compile(r'''^__version__\s*=\s*["']([^"']+)["']''', re.MULTILINE)


def _read_version(path: str) -> str:
    """Return the version declared by ``src/prokname_studio/__init__.py``."""
    with open(path, encoding="utf-8") as fh:
        match = _VERSION_RE.search(fh.read())
    if match is None:
        raise SystemExit(
            f"prokname-studio: cannot find the `__version__` literal in {path} — "
            "refusing to freeze a bundle whose Info.plist version could drift "
            "from the version the About box and `--version` report."
        )
    return match.group(1)


_version = _read_version(_VERSION_FILE)


def _bundle_icon():
    """The platform shell icon, if the release tree carries one.

    Generated from ``src/prokname_studio/assets/icon.svg`` — the artwork is the
    source of truth — by the documented release step::

        rsvg-convert -w 1024 -h 1024 icon.svg -o icon.png   # or Inkscape/Qt
        iconutil -c icns icon.iconset -o ProkNameStudio.icns     # macOS
        pyinstaller --icon …                                  # Windows: .ico

    ``iconutil`` and ``rsvg-convert`` are platform tooling that CI's bundle job
    does not have, so an absent file is not a build error: the app still installs
    its own SVG window icon at runtime. What would be a lie is pointing
    ``icon=`` at a file that does not exist, so PyInstaller silently drops it.
    """
    for candidate in ("ProkNameStudio.icns", "ProkNameStudio.ico"):
        path = os.path.join(_SPECPATH, candidate)
        if os.path.exists(path):
            return path
    print(
        "prokname-studio: no ProkNameStudio.icns/.ico next to the spec — the "
        "bundle will use the platform's generic shell icon (the window icon is "
        "still the packaged SVG). Generate one from assets/icon.svg; see "
        "_bundle_icon()."
    )
    return None


# Collect both packages' submodules so nothing is missed by static analysis:
# the app imports the engine through its public API, and PyInstaller's graph
# only sees what launcher.py reaches directly.
hiddenimports = collect_submodules("prokname_studio") + collect_submodules("prokname")

# Data assets: the engine's JSON rule files + benchmark sets, and Studio's own
# assets (the SVG icon). Collected from the *installed* packages (an editable
# install points back at src/).
_datas = collect_data_files("prokname") + collect_data_files("prokname_studio")

# Guard the thing a hand-written list used to get wrong: if a hook ever stops
# returning a whole asset tree, fail the build instead of shipping an app that
# dies on its first importlib.resources lookup.
for _required_dir in ("prokname/data", "prokname/benchmark/data", "prokname_studio/assets"):
    if not any(
        dest.replace(os.sep, "/").rstrip("/").endswith(_required_dir) for _src, dest in _datas
    ):
        raise SystemExit(
            f"prokname-studio: collect_data_files() returned no files under "
            f"{_required_dir!r} — the package was probably installed without its "
            f"data assets; refusing to build a broken bundle."
        )

a = Analysis(
    # Absolute, SPECPATH-relative paths: the hand-written "src/..." form only
    # worked when pyinstaller happened to be invoked from the repository root.
    [os.path.join(_SPECPATH, "src", "prokname_studio", "launcher.py")],
    pathex=[os.path.join(_SPECPATH, "src")],
    binaries=[],
    datas=_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # trim test/dev tooling that shouldn't ship in the frozen app.
        # NOTE: these are *import* names — the vcrpy distribution is imported as
        # `vcr`, so a "vcrpy" entry would exclude nothing.
        "pytest",
        "pytestqt",
        "hypothesis",
        "vcr",
        "ruff",
        "PyInstaller",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# --- onedir mode: EXE contains only scripts, COLLECT handles binaries/data ---
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,   # <-- onedir: binaries go in COLLECT, not EXE
    name="ProkNameStudio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,           # --windowed: no terminal window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,        # build for current arch (arm64 on Apple Silicon)
    codesign_identity=None,
    entitlements_file=None,
    icon=_bundle_icon(),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name="ProkNameStudio",
)

app = BUNDLE(
    coll,
    name="ProkName Studio.app",
    icon=_bundle_icon(),
    bundle_identifier="io.github.prokname.studio",
    info_plist={
        "CFBundleDisplayName": "ProkName Studio",
        # Derived from src/prokname_studio/__init__.py, never repeated here.
        "CFBundleShortVersionString": _version,
        "CFBundleVersion": "1",  # build number, not a version string
        "NSHumanReadableCopyright": "© 2026 Zichao Zeng",
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
    },
)
