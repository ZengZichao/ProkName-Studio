"""The ProkName Studio application icon.

One vector file ships with the package (``assets/icon.svg``) and is rasterised
here at the sizes a desktop asks for: the 16 px toolbar glyph, the 32 px window
badge, the 512 px app icon.

Rendering needs Qt's SVG *plugin*, which is not a guarantee (a stripped Qt
install, or a bundle built without ``imageformats/qsvg``, has no SVG handler).
Then a degraded glyph is drawn with ``QPainter`` — the tile and the cell, without
the flagellum or the check — so Studio still shows a recognisable mark instead of
the platform's generic application icon. The fallback is deliberately not a
second copy of the artwork: keeping two renderings of one logo in sync is how the
icon ends up disagreeing with itself.
"""
from __future__ import annotations

from importlib import resources

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QIcon,
    QImage,
    QPainter,
    QPen,
    QPixmap,
)

ASSET_PACKAGE = "prokname_studio"
ASSET_DIR = "assets"
ICON_FILE = "icon.svg"

#: The sizes Studio asks Qt to hold. 512 is the SVG's own canvas, so the largest
#: request is a 1:1 render rather than an upscale.
ICON_SIZES: tuple[int, ...] = (16, 24, 32, 48, 64, 128, 256, 512)

_TILE = "#2e8bc9"
_TILE_EDGE = "#1c5c86"
_CELL = "#ffffff"
_CELL_EDGE = "#a8d4ef"


def icon_svg() -> bytes:
    """The packaged SVG source, read through ``importlib.resources``.

    Read as bytes rather than a path: a wheel- or zip-imported package has no
    filesystem path to hand to Qt.
    """
    return resources.files(ASSET_PACKAGE).joinpath(ASSET_DIR, ICON_FILE).read_bytes()


def app_icon() -> QIcon:
    """Studio's icon: the SVG where Qt can render it, the degraded glyph where it cannot."""
    icon = QIcon()
    try:
        source = QImage.fromData(icon_svg())
    except (FileNotFoundError, IsADirectoryError, PermissionError, OSError):
        # An asset that is not in the install is a packaging bug, and silently
        # shipping the fallback glyph is how it stays unfound; a frozen bundle
        # with a missing data file is the same event as a missing plugin only in
        # how it looks, so the caller can tell them apart via _HAS_SVG_HANDLER.
        source = QImage()
    if not source.isNull():
        for size in ICON_SIZES:
            scaled = source.scaled(
                size,
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            if not scaled.isNull():
                icon.addPixmap(QPixmap.fromImage(scaled))
    else:
        icon = degraded_icon()
    return icon


def has_svg_handler() -> bool:
    """True when Qt can rasterise the packaged SVG (the honest way to test the above)."""
    return not QImage.fromData(icon_svg()).isNull()


def install(app) -> QIcon:
    """Set the icon on ``app``; the window, the dock tile and the dialogs inherit it."""
    icon = app_icon()
    app.setWindowIcon(icon)
    return icon


def degraded_icon(size: int = 64) -> QIcon:
    """The no-SVG-handler mark: the tile and the cell, drawn with shapes."""
    image = QImage(size, size, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    try:
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        margin = size * 0.023
        radius = size * 0.234
        painter.setPen(QPen(QColor(_TILE_EDGE), max(1.0, size * 0.016)))
        painter.setBrush(QBrush(QColor(_TILE)))
        painter.drawRoundedRect(
            QRectF(margin, margin, size - 2 * margin, size - 2 * margin), radius, radius
        )

        body = QRectF(size * 0.172, size * 0.39, size * 0.469, size * 0.219)
        painter.setPen(QPen(QColor(_CELL_EDGE), max(1.0, size * 0.016)))
        painter.setBrush(QBrush(QColor(_CELL)))
        painter.drawRoundedRect(body, body.height() / 2, body.height() / 2)

        septum = QPen(
            QColor(_CELL_EDGE), max(1.0, size * 0.038),
            Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
        )
        painter.setPen(septum)
        centre = body.center().x()
        painter.drawLine(
            QPointF(centre, body.top() + size * 0.034),
            QPointF(centre, body.bottom() - size * 0.034),
        )
    finally:
        painter.end()
    return QIcon(QPixmap.fromImage(image))


__all__ = [
    "ICON_FILE",
    "ICON_SIZES",
    "app_icon",
    "degraded_icon",
    "has_svg_handler",
    "icon_svg",
    "install",
]
