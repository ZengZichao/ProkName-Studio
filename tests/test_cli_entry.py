"""The command-line surface, and the fact that the frozen bundle shares it.

``prokname-studio --version`` has to answer from a terminal *and* from inside the
`.app`, because that is how a smoke test checks a bundle without opening a window
on someone's desktop. Both paths only work if the PyInstaller launcher goes
through the same argument-parsing entry point the console script does — an earlier
launcher called ``run()`` directly, so the bundle silently ignored ``--version``
and popped a window instead of reporting its version.
"""
from __future__ import annotations

import pytest

from prokname_studio import __version__, app, launcher


def test_version_reports_both_versions(monkeypatch, capsys):
    """Studio's version, and the engine it is running against."""
    import prokname

    with pytest.raises(SystemExit) as exit_info:
        app.main(["--version"])
    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    assert __version__ in out and prokname.__version__ in out


def test_help_lists_the_switches_without_starting_qt(monkeypatch, capsys):
    def no_run(**_kwargs):  # pragma: no cover - the assertion is that this is unused
        raise AssertionError("--help must not launch the window")

    monkeypatch.setattr(app, "run", no_run)
    with pytest.raises(SystemExit) as exit_info:
        app.main(["--help"])
    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    assert "--lang" in out and "--theme" in out


def test_the_switches_reach_run(monkeypatch):
    seen: dict[str, object] = {}

    def fake_run(**kwargs):
        seen.update(kwargs)
        return 0

    monkeypatch.setattr(app, "run", fake_run)
    assert app.main(["--lang", "zh", "--theme", "dark", "--debug"]) == 0
    assert seen == {"lang": "zh", "theme": "dark", "debug": True}


def test_an_unrecognised_argument_is_reported_not_swallowed(monkeypatch, capsys):
    """A desktop launcher's extra argument must not stop the window opening."""
    started: list[bool] = []
    monkeypatch.setattr(app, "run", lambda **kwargs: started.append(True) or 0)

    assert app.main(["-psn_0_123456"]) == 0
    assert started, "the app refused to start over an argument it did not know"
    err = capsys.readouterr().err
    assert "-psn_0_123456" in err, f"the ignored argument was never mentioned: {err!r}"


def test_the_frozen_launcher_uses_the_parsing_entry_point(monkeypatch):
    """The bundle's bootstrap must be `app.main`, not a bare `run()`."""
    called: list[tuple] = []
    monkeypatch.setattr(app, "main", lambda *a: called.append(a) or 0)
    assert launcher.main() == 0
    assert called == [()], "launcher.py bypassed the argument parser again"
