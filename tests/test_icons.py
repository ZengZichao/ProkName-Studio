"""The SVG application icon: it ships, it loads, and it is the window's icon.

An icon is the kind of feature that can pass every glance while doing nothing:
the file can be missing from the wheel, Qt can be handed artwork it cannot
render, and the app opens with the platform's generic tile. So these tests read
the packaged bytes, render them, and check what the running application ends up
wearing.
"""
from __future__ import annotations

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from PySide6.QtWidgets import QWidget

from prokname_studio import appearance, icons

REPO = Path(__file__).resolve().parents[1]


def _svg_root() -> ET.Element:
    return ET.fromstring(icons.icon_svg())


def test_the_svg_is_packaged_and_well_formed():
    root = _svg_root()
    assert root.tag.endswith("svg")
    assert root.get("viewBox"), "no viewBox: the mark cannot scale"
    assert root.get("width") and root.get("height")


def test_the_svg_is_the_square_it_claims_to_be():
    root = _svg_root()
    assert float(root.get("width")) == float(root.get("height")), (
        "a dock tile is square; a non-square mark gets letterboxed"
    )


def test_every_gradient_the_artwork_references_is_defined():
    """A ``url(#id)`` the file does not define renders as black, not as a warning."""
    root = _svg_root()
    defined = {el.get("id") for el in root.iter() if el.get("id")}
    used = {
        attr[4:-1].lstrip("#")
        for element in root.iter()
        for attr in element.attrib.values()
        if attr and attr.startswith("url(#")
    }
    assert used, "the artwork references no gradient at all"
    assert used <= defined, f"referenced but undefined: {sorted(used - defined)}"


def test_qt_can_render_the_packaged_svg_here():
    """The SVG handler is a Qt plugin, and without it the app wears the fallback."""
    assert icons.has_svg_handler(), (
        "no SVG image handler in this environment: check that "
        "imageformats/qsvg shipped with PySide6 (and, for a frozen build, with "
        "the PyInstaller bundle) — see ProkNameStudio.spec"
    )


def test_app_icon_holds_every_size_it_promises():
    icon = icons.app_icon()
    assert not icon.isNull()
    for size in icons.ICON_SIZES:
        pixmap = icon.pixmap(size, size)
        assert not pixmap.isNull(), f"no pixmap for {size}x{size}"
        assert (pixmap.width(), pixmap.height()) == (size, size)


def test_the_degraded_glyph_renders_at_any_size():
    for size in (16, 64, 512):
        pixmap = icons.degraded_icon(size).pixmap(size, size)
        assert (pixmap.width(), pixmap.height()) == (size, size)
        image = pixmap.toImage()
        # a fully transparent square is "not null" and still shows nothing
        assert any(
            image.pixelColor(x, y).alpha() > 0
            for x in range(0, size, max(1, size // 8))
            for y in range(0, size, max(1, size // 8))
        ), f"the {size}px fallback glyph is empty"


def test_install_puts_the_icon_on_the_application(qapp):
    icon = icons.install(qapp)
    assert not icon.isNull()
    assert qapp.windowIcon().availableSizes() == icon.availableSizes()


def test_a_window_inherits_the_application_icon(qapp):
    icons.install(qapp)
    window = QWidget()
    assert not window.windowIcon().isNull()
    window.deleteLater()


def test_run_wires_the_icon_and_the_startup_theme(qapp, monkeypatch, tmp_path):
    """Order matters: the window's switchers read what startup already applied.

    A ``--theme dark`` that reached the window before the palette did would open
    showing "Follow system" while painting dark — a control that reports a state
    it does not own.
    """
    from prokname.storage import ProjectStore

    from prokname_studio import app as app_module
    from prokname_studio.main_window import MainWindow as Real

    observed: dict[str, object] = {}

    def spy(state):
        observed["mode"] = appearance.current_mode()
        observed["has_icon"] = not qapp.windowIcon().isNull()
        return Real(state)

    monkeypatch.setattr(app_module, "MainWindow", spy)
    monkeypatch.setattr(app_module.QApplication, "exec", lambda self: 0)
    monkeypatch.setattr(
        "prokname_studio.views.project_view.ProjectStore",
        lambda: ProjectStore(base_dir=tmp_path / "projects"),
    )

    assert app_module.run(theme=appearance.DARK) == 0
    assert observed["mode"] == appearance.DARK
    assert observed["has_icon"] is True


# --------------------------------------------------------------------------- #
# the release-time derivation: SVG → .icns
# --------------------------------------------------------------------------- #


def _icon_script():
    import importlib.util

    path = REPO / "scripts" / "make_bundle_icon.py"
    spec = importlib.util.spec_from_file_location("make_bundle_icon", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_iconset_holds_every_size_iconutil_wants(tmp_path):
    """One wrong name or dimension and `iconutil` fails — at release time."""
    from PySide6.QtGui import QImage

    script = _icon_script()
    written = script.render(tmp_path)
    assert {p.name for p in written} == {n for n, _ in script.ICONSET_SIZES}
    for name, size in script.ICONSET_SIZES:
        image = QImage(str(tmp_path / name))
        assert not image.isNull(), f"{name} is not a readable PNG"
        assert (image.width(), image.height()) == (size, size), name
        # a blank tile at the right size would pass the above and still ship an
        # invisible icon
        assert any(
            image.pixelColor(x, y).alpha() > 0
            for x in range(0, size, max(1, size // 8))
            for y in range(0, size, max(1, size // 8))
        ), f"{name} rendered empty"


def test_the_check_mode_notices_a_missing_or_stale_shell_icon(tmp_path, monkeypatch,
                                                             capsys):
    """The gate that stops a release shipping yesterday's artwork."""
    script = _icon_script()
    svg = tmp_path / "icon.svg"
    svg.write_bytes(icons.icon_svg())
    icns = tmp_path / "ProknameStudio.icns"
    monkeypatch.setattr(script, "SVG", svg)
    monkeypatch.setattr(script, "ICNS", icns)

    argv = sys.argv
    try:
        sys.argv = ["make_bundle_icon.py", "--check"]
        assert script.main() == 1, "a missing .icns must not pass --check"
        icns.write_bytes(b"icns")
        os.utime(icns, (svg.stat().st_atime - 100, svg.stat().st_mtime - 100))
        assert script.main() == 1, "an .icns older than the SVG must fail --check"
        os.utime(icns, None)
        assert script.main() == 0, "a current .icns must pass --check"
    finally:
        sys.argv = argv
    assert "make_bundle_icon.py" in capsys.readouterr().err
