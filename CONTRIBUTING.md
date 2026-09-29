# Contributing to ProkName Studio

[English](CONTRIBUTING.md) | [中文](CONTRIBUTING.zh.md)

## Core principle

**Studio adds no naming logic.** Every verdict, candidate, badge and colour on
screen must come from a call into `prokname`'s public API. A rule that is
re-implemented here is a rule that can disagree with the terminal — and the two
surfaces render the same map precisely so they cannot.

If you believe a view needs a new computation, the change belongs in the
[engine repository](https://github.com/ZengZichao/ProkName), not in `views/`.

## Boundaries

- `tests/test_boundaries.py` pins the set of engine modules Studio may import.
  Adding an entry is a deliberate act: it is a contract the engine then has to
  keep for Studio to work.
- `prokname.cli` is **never** importable from Studio. A command-line entry point
  is not an API.
- Nothing reads the engine's source tree. The dependency is expressed as a package
  name (`prokname>=0.1.0`) and a repository URL — never as a folder path that
  resolves on one machine only.

## Interface rules

- **Every string is translated.** New UI text means a new key in *both* tables in
  `i18n.py`; `tests/test_i18n_parity.py` fails on a key that exists in one
  language only, on an untranslated reference, or on an empty translation.
- **Verdict colours are the engine's tokens, not Studio's.** The semantic tokens
  and the verdict / role mapping come from `prokname.presentation.decision`.
  Studio decides only how a token looks on a light versus a dark surface
  (`appearance.py`), and every lifted dark-surface colour must clear 4.5:1
  contrast against the dark base.
- **One thread rule.** Engine work runs on a worker `QThread`; a `QThread` never
  touches a widget. Re-entry is guarded in `worker.py`, so a second Run press
  cannot start a second scan.

## Language of the documentation

**English is the primary document; Chinese is its companion.** Every prose file
ships as `NAME.md` (English) plus `NAME.zh.md` (Chinese), with
`[English](…) | [中文](…)` at the top and English listed first. Where a document
quotes an upstream source — a licence footer, an API response — the quote stays
verbatim in its original language in both copies, and the English file is the
authoritative one.

`docs/STUDIO_PLAN.md` is the design specification: it explains why the front end is
shaped as it is. The documents a reader acts on are `README` and `CHANGELOG`, and
neither points at a folder next to this one.

## Testing

```bash
pip install -e ".[dev]"
QT_QPA_PLATFORM=offscreen python -m pytest            # the whole suite
QT_QPA_PLATFORM=offscreen python -m pytest -v tests/test_appearance.py
```

- **PySide6 is a runtime dependency, so no test may skip for a missing Qt.**
  A run that cannot import Qt has a broken install, and a skipped gate is not a
  gate. CI parses the JUnit XML and goes red if anything skipped for a Qt reason.
- On a headless runner use `QT_QPA_PLATFORM=offscreen`; without it `QApplication`
  cannot start.
- `tests/test_asset_freshness.py` and `tests/test_spec.py` guard the icon asset
  and the bundle description; `tests/test_citation_metadata.py` guards
  `CITATION.cff` as a mirror of `__version__`.

## Packaging

`ProkNameStudio.icns` is **not** committed. It is derived from
`src/prokname_studio/assets/icon.svg` by `scripts/make_bundle_icon.py`; a second
copy of the artwork under version control is a second thing to keep in step. The
CI `bundle` job generates it, builds the `.app`, and then verifies that the frozen
PYZ module set matches `src/` and that the icon and engine rule assets actually
reached the bundle.

## Versioning

The version is declared exactly once, in `src/prokname_studio/__init__.py`.
`pyproject.toml` keeps `dynamic = ["version"]`, the PyInstaller spec reads the
literal, and `CITATION.cff` mirrors it. Bump the one line, then update the two
CFF mirrors — the tests above fail if they drift. Studio's version is its own; the
engine's is reported at runtime, never hard-coded here except as the
`MIN_PROKNAME_VERSION` floor.

## Where issues belong

Engine problems — a wrong gender, an unreachable authority, a rule asset needing
expert review — go to the
[engine's issue tracker](https://github.com/ZengZichao/ProkName/issues).
Interface, translation, appearance and packaging problems go
[here](https://github.com/ZengZichao/ProkName-Studio/issues).

## Never

Commit API credentials, passwords or tokens. Studio stores nothing of the kind:
it is local-first and the engine owns credential handling.
