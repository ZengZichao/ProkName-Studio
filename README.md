<p align="center">
  <img src="src/prokname_studio/assets/icon.svg" width="128" height="128" alt="ProkName Studio">
</p>

# ProkName Studio

[English](README.md) | [中文](README.zh.md)

[![DOI: 10.5281/zenodo.23052800](https://zenodo.org/badge/DOI/10.5281/zenodo.23052800.svg)](https://doi.org/10.5281/zenodo.23052800)

The native desktop front end for **[prokname](https://github.com/ZengZichao/ProkName)**,
the prokaryotic nomenclature assistant: deterministic etymology-driven name
generation, gender-agreement validation, dual-code (ICNP / SeqCode) routing and a
two-tier dedup check — in a window instead of a terminal.

**Bilingual and two-tone by design**: the interface switches between Chinese and
English at runtime, and between a light and a dark appearance, with no restart.

Studio is a *front end*. It re-implements no naming rule: every number, verdict
and badge on screen comes from `prokname`'s public API. The dependency runs one
way — Studio needs the engine, the engine never needs Qt.

---

## Contents

1. [Install](#install)
2. [Run](#run)
3. [What the window does](#what-the-window-does)
4. [Language and appearance](#language-and-appearance)
5. [The icon](#the-icon)
6. [Development](#development)
7. [How Studio relates to prokname](#how-studio-relates-to-prokname)
8. [Cite](#cite)
9. [Licence](#licence)

## Install

Studio depends on the `prokname` distribution. It is not on PyPI yet, so install
the engine from its source repository first, then Studio:

```bash
# 1. the engine (also installs its own runtime deps: typer + rich)
pip install "git+https://github.com/ZengZichao/ProkName.git"

# 2. this front end (pulls PySide6, the Qt binding)
pip install "git+https://github.com/ZengZichao/ProkName-Studio.git"
```

From a checkout of this repository, step 2 becomes `pip install -e .` — the
`prokname` requirement is resolved from wherever it is published, exactly as for
any other dependency. Nothing in this project reads the engine's source tree.

Requirements: Python ≥ 3.11 (3.11–3.14 tested), Qt 6.7+ via PySide6, and a
desktop session (macOS, Windows or Linux/X11/Wayland).

## Run

```bash
prokname-studio                 # UI language and appearance both follow the system
prokname-studio --lang zh       # force the Chinese interface
prokname-studio --lang en       # force the English interface
prokname-studio --theme dark    # this run only; a toolbar choice is remembered
prokname-studio --help
prokname-studio --version       # Studio's version and the engine's
```

`python -m prokname_studio` is the same command. `--debug` echoes the
third-party client output the engine normally swallows; it changes no verdict and
no exit code.

## What the window does

Five panels, each a thin front end over one part of the engine:

| Panel | Engine call | What you get |
|---|---|---|
| **生成 / Generate** | `generate()` | candidate names for a stem, with grammatical category, gender, compliance and the derivation that produced each one |
| **路由 / Route** | `route()` | the viable publication paths (ICNP, SeqCode, both) for a source type, with roles and trade-offs |
| **查重 / Check** | `check_name()` | the dedup verdict, per-authority results and near matches |
| **项目 / Project** | `ProjectStore` | create projects, collect candidates, rate them, export JSON / CSV / Markdown |
| **数据资产 / Data assets** | `engine.data.asset_status()` | which rule assets the engine is running, their version and their review state |

Two honesty guarantees carried over from the CLI, because they are the point of
the tool:

- **A check that could not be made is never reported as a clean name.** Studio
  checks offline: LPSN needs credentials and a network, and the SeqCode Registry
  has no lookup-by-name. A verdict of "no clear conflict" therefore means
  "absent from what I could reach", and the window says so where it is shown.
  Run `prokname check --online` in a terminal for the reachable answer.
- **A compliance tick that rests on inference is labelled as one.** If a genus
  gender came from an ending heuristic rather than the lexicon or an expert
  override, the "compliant" cell reads as review-needed, not as a green tick.

## Language and appearance

Both are toolbar switches in the top bar, and both apply immediately.

**Language** — `自动 / Auto` follows the system locale; `中文` and `English` pin
it. Every label is translated, including the values the engine returns
(`adjective` → 形容词, `only-viable` → 唯一可行), and a parity test fails if a key
exists in one language only or a view references a key nobody translated.

**Appearance** — `跟随系统 / Follow system` (default), `亮色 / Light`, `暗色 / Dark`.
`auto` re-reads the desktop colour scheme when the OS switches between light and
dark, so Studio follows along without a restart. An explicit choice is stored in
the OS-native preference store (macOS: a plist under `~/Library/Preferences`,
Windows: the registry) and survives the next launch; `--theme` overrides it for
one run without writing anything.

The two are independent: switching to dark does not switch language, and neither
restarts the window or loses the session's candidates.

## The icon

`src/prokname_studio/assets/icon.svg` is the artwork and the source of truth: one
vector file, packaged with the application and rasterised at runtime for the
16 px toolbar glyph through the 512 px window badge. If Qt's SVG plugin is absent
(a stripped Qt install, a bundle built without `imageformats/qsvg`), a degraded
glyph drawn from the same geometry is used rather than the platform's generic
application tile.

A *bundle* shell icon is a separate artifact — macOS wants `.icns`, Windows
`.ico` — and it is derived from the SVG, never hand-made alongside it:

```bash
python scripts/make_bundle_icon.py          # writes ProkNameStudio.icns
python scripts/make_bundle_icon.py --check   # missing, or older than the SVG?
```

The script rasterises the SVG with PySide6 (no `rsvg-convert`/Inkscape to install)
and packs the sizes `iconutil` requires. The `.icns` is a build product, so it is
not committed; `ProkNameStudio.spec` embeds it when it is present and builds
without it — with a printed warning — when it is not. CI generates it before the
bundle job, so a released `.app` never ships the platform's generic tile.

## Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install "git+https://github.com/ZengZichao/ProkName.git"   # the engine
pip install -e ".[dev]"                                        # Studio + pytest, pytest-qt, ruff

pytest                         # the whole suite, offscreen Qt
QT_QPA_PLATFORM=offscreen pytest
ruff check src tests conftest.py
```

Layout: `src/prokname_studio/` — `app.py` (entry point and argument parsing),
`appearance.py` (light / dark palettes and stylesheets), `i18n.py` (the zh / en
string tables and the language signal), `icons.py` (SVG loading and the fallback
glyph), `main_window.py` (navigation and the switcher bar), `state.py` (the
session state shared by the views), `views/` (the five panels) and `components/`
(the widgets they compose).

Contributing rules — the import boundary, the bilingual string-parity rule, the
thread rule and the packaging conventions — are in
[CONTRIBUTING.md](CONTRIBUTING.md) ([中文](CONTRIBUTING.zh.md)).

Tests worth knowing about before you change something:

- `tests/test_appearance.py` — mode resolution, every semantic token's dark
  spelling and its contrast on the dark surface, live switching reaching badges,
  table foregrounds and placeholder text, and what is persisted versus what is
  per-run.
- `tests/test_i18n_parity.py` — reads the string tables out of the source, so a
  key in one language only, an untranslated key referenced by a view, or an empty
  translation fails without a Qt session.
- `tests/test_icons.py` — the packaged SVG is well-formed, Qt can render it here,
  every promised size exists, and the fallback glyph is not an empty square.
- `tests/test_spec.py` — `exec()`s the PyInstaller spec against stubs to check
  that it derives its version, collects both packages' data, and refuses to build
  when an asset tree is missing.

There is no `pytest.importorskip("PySide6")` anywhere in this suite. PySide6 is a
runtime dependency of this package, so a run that cannot import Qt has an install
to fix — reporting that as green-by-skipping is the failure mode this repository
refuses.

Freezing the desktop app (macOS `.app`, Windows `.exe`) is a release-time step:

```bash
pip install -e ".[build]"
pyinstaller ProkNameStudio.spec --noconfirm
```

## How Studio relates to prokname

| | |
|---|---|
| Depends on | [`prokname`](https://github.com/ZengZichao/ProkName) — declared in `pyproject.toml` as `prokname>=0.1.0` |
| Imports | the engine's public API: `engine.generate`, `engine.gender`, `engine.orthography`, `dedup.check_name`, `routing.route`, `storage.ProjectStore`, `presentation.decision`, `presentation.theme` |
| Never imports | `prokname.cli` (a command-line entry point is not an API), and nothing in this project reads the engine's source tree |
| Owns | the window, the zh / en strings, the light / dark palettes, the icon, the PyInstaller bundle |
| Reports | both versions: `prokname-studio --version` prints Studio's own version and the engine version it is running against |

Engine bugs — a wrong gender, an unreachable authority, a rule asset that needs
expert review — belong in the [engine's issue tracker](https://github.com/ZengZichao/ProkName/issues).
Interface bugs, translations, theming and packaging belong [here](https://github.com/ZengZichao/ProkName-Studio/issues).

## Cite

If you use ProkName Studio, please cite the software ([`CITATION.cff`](CITATION.cff)):

- **Zichao Zeng** (ORCID [0000-0001-6553-970X](https://orcid.org/0000-0001-6553-970X))
- **Zenodo**: concept DOI [10.5281/zenodo.23052800](https://doi.org/10.5281/zenodo.23052800), which always resolves to the latest archived release; this version is [10.5281/zenodo.23052801](https://doi.org/10.5281/zenodo.23052801)

Studio is the front end; the nomenclature work it displays is the engine's, so a
methods citation should point at
[prokname](https://github.com/ZengZichao/ProkName) and its
[`CITATION.cff`](https://github.com/ZengZichao/ProkName/blob/main/CITATION.cff) too.
`prokname-studio --version` prints both versions, which is what a reader needs to
reproduce a screenshot.

## Licence

MIT — see [LICENSE](LICENSE). The rule assets Studio displays are the engine's and
carry the engine's data terms.
