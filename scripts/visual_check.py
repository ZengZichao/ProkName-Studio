"""One-off visual verification: run the real UI, capture every page + the guide.

Run from the project root with the project venv:
    .venv/bin/python scripts/visual_check.py
Writes PNGs to /tmp and prints their paths. Not part of the test suite.
"""
import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

app = QApplication(sys.argv[:1])
from prokname_studio import appearance, i18n  # noqa: E402

appearance.install(app, "light")
i18n.install(app, "zh")

from prokname_studio.main_window import MainWindow  # noqa: E402
from prokname_studio.state import StudioState  # noqa: E402

w = MainWindow(StudioState())
w.resize(1280, 860)
w.show()

shots = []


def grab(name, widget):
    path = f"/tmp/pn_{name}.png"
    widget.grab().save(path)
    shots.append(path)


def step1():
    assert w._guide_dialog is None, "guide must be closed by default"
    grab("main_generate_default", w)
    w.go_to_page("route")
    QTimer.singleShot(300, step2)


def step2():
    v = w._views["route"]
    v._on_route()
    QTimer.singleShot(300, step3)


def step3():
    grab("route", w)
    w.go_to_page("project")
    QTimer.singleShot(300, step4)


def step4():
    grab("project", w)
    w.guide_btn.click()
    QTimer.singleShot(300, step5)


def step5():
    d = w._guide_dialog
    assert d is not None
    d.step_list.setCurrentRow(3)  # route step
    grab("guide", d)
    w.go_to_page("generate")
    g = w._views["generate"]
    g.stem.setText("Wukong")
    g.genus.setText("Bacillus")
    g._on_generate()
    QTimer.singleShot(1500, step6)


def step6():
    g = w._views["generate"]
    g.table.selectRow(0)
    grab("generate_results", w)
    print("SHOTS:", shots)
    app.quit()


QTimer.singleShot(400, step1)
app.exec()
