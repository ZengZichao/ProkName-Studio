#!/usr/bin/env python3
"""Generate the macOS bundle icon (``ProkNameStudio.icns``) from the SVG.

The repository carries one piece of artwork — ``src/prokname_studio/assets/icon.svg``
— and everything else is derived from it. The window icon is rasterised at
runtime; the *shell* icon (Finder, Dock, ⌘-Tab) is a different artifact, because
macOS wants an ``.icns`` container and cannot use the SVG itself.

    python scripts/make_bundle_icon.py            # writes ProkNameStudio.icns
    python scripts/make_bundle_icon.py --check    # is it present and current?

Rasterising uses PySide6, which the project already depends on, rather than
``rsvg-convert`` or Inkscape: one fewer tool that a release machine has to have
and that CI does not have. ``iconutil`` is macOS-only, so that step is reported
and skipped elsewhere — the app still ships its runtime SVG window icon either way.

``ProkNameStudio.spec`` picks the file up when it sits next to the spec, and says
so when it does not.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SVG = REPO / "src" / "prokname_studio" / "assets" / "icon.svg"
ICNS = REPO / "ProkNameStudio.icns"
ICONSET = REPO / "ProkNameStudio.iconset"

#: The names ``iconutil`` requires, and the pixel size each one must hold.
ICONSET_SIZES: tuple[tuple[str, int], ...] = (
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024),
)


def render(png_dir: Path) -> list[Path]:
    """Rasterise the SVG into ``png_dir`` at every size the iconset needs."""
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QGuiApplication, QImage

    app = QGuiApplication.instance() or QGuiApplication(["make_bundle_icon"])
    source = QImage.fromData(SVG.read_bytes())
    if source.isNull():
        raise SystemExit(
            f"{SVG} could not be rasterised: Qt has no SVG image handler here. "
            "Install PySide6 (the plugin ships with it) — do not hand-edit an icon in."
        )
    png_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, size in ICONSET_SIZES:
        image = source.scaled(
            size, size,
            Qt.AspectRatioMode.KeepAspectRatioByExpanding,
            Qt.TransformationMode.SmoothTransformation,
        )
        target = png_dir / name
        if not image.save(str(target)):
            raise SystemExit(f"could not write {target}")
        written.append(target)
    del app
    return written


def build() -> Path:
    """Produce ``ProkNameStudio.icns`` next to the spec."""
    if sys.platform != "darwin":
        raise SystemExit(
            f"iconutil is macOS-only and this is {sys.platform}; the .icns was not "
            "generated. Build the release on macOS — or ship without a shell icon, "
            "which ProkNameStudio.spec handles by printing a warning."
        )
    if shutil.which("iconutil") is None:
        raise SystemExit("iconutil not found on PATH (it ships with the Xcode tools)")

    if ICONSET.exists():
        shutil.rmtree(ICONSET)
    try:
        render(ICONSET)
        subprocess.run(
            ["iconutil", "-c", "icns", str(ICONSET), "-o", str(ICNS)],
            check=True, capture_output=True, text=True)
    finally:
        shutil.rmtree(ICONSET, ignore_errors=True)
    return ICNS


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true",
                        help="exit non-zero if ProkNameStudio.icns is missing or older "
                             "than the SVG it was generated from")
    args = parser.parse_args()

    if args.check:
        if not ICNS.exists():
            print(f"{ICNS.name} is missing — run: python scripts/make_bundle_icon.py",
                  file=sys.stderr)
            return 1
        if ICNS.stat().st_mtime < SVG.stat().st_mtime:
            print(f"{ICNS.name} is older than {SVG.name} — regenerate it, or the "
                  "bundle will ship an icon the artwork has moved past", file=sys.stderr)
            return 1
        print(f"{ICNS.name} is present and newer than the SVG")
        return 0

    path = build()
    print(f"wrote {path.name} ({path.stat().st_size // 1024} KiB) from {SVG.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
