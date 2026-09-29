# ProkName Studio — Design Specification

[English](STUDIO_PLAN.md) | [中文](STUDIO_PLAN.zh.md)

> Scope: the design of the native desktop front end for
> [prokname](https://github.com/ZengZichao/ProkName). The facts a user acts on are in
> [README](../README.md) and [CHANGELOG](../CHANGELOG.md); contributing rules are in
> [CONTRIBUTING](../CONTRIBUTING.md). This document explains *why* the front end is
> shaped the way it is, so that a change to it can be argued rather than guessed.
>
> Rendering layer: **PySide6 (Qt)** — a standalone desktop application, no browser
> dependency. Platforms: **macOS guaranteed** — installing from source works on Apple
> Silicon and on Intel, while the frozen `.app` is built for the architecture of the
> machine that builds it (arm64 today). Windows and
> Linux run as install-and-test targets. Interface: **live Chinese / English
> switching** and a **light / dark appearance switch**.

---

## 1. Positioning

| Dimension | Decision | Reason |
|---|---|---|
| Role | **adoption lever**, not a separate research contribution | Gets the engine in front of microbiologists and taxonomists who do not live in a terminal |
| Form | **standalone native desktop application** | Double-click, one window, frozen with PyInstaller so no Python install is needed |
| Capability | **none of its own** | Every number, verdict and badge on screen comes from `prokname`'s public API |
| Dependency direction | **one way** | Studio needs the engine; the engine never needs Qt. Expressed as a package requirement and a repository URL, never a path |
| Technology stack | **Python + PySide6 (Qt)** | Native widgets, cross-platform, LGPL is friendly to an MIT project, freezes cleanly into a macOS `.app` |
| Privacy | **fully local, zero network** | Nomenclatural priority is sensitive; a desktop app with no server cannot leak a candidate name |
| Platforms | **macOS guaranteed** | The user base works mainly on macOS; other platforms are supported in CI, not frozen |
| Interface language | **live zh / en switching** | Follows the desktop locale by default; serves users at home and abroad |
| Appearance | **live light / dark switching** | A verdict must stay readable on either surface |

**Why Qt rather than a web UI.** A browser-rendered UI fails the "no browser
dependency" requirement, and a WebView inside a window (Tauri, Electron) is still a
browser engine underneath. Qt draws the operating system's native widgets, so the
result is a desktop application in the strict sense — and `QTableWidget`,
`QTreeWidget` and `QTextBrowser` are exactly the shapes the candidate table, the
derivation tree and the dedup verdict need. The cost is more layout and event code
than a web framework would need; that is the price of software that can be distributed
on its own.

---

## 2. Design principles

1. **The engine is the only truth.** Studio calls `prokname`'s public API and renders
   what comes back. A rule change happens in the engine and is inherited here
   automatically; a rule re-implemented here is a rule that can disagree with the
   terminal.
2. **Auditability is the visible product.** The engine's `derivation`, `warnings` and
   `compliant` fields are drawn — a step tree and a tri-colour compliance badge —
   because making the *why* legible is the front end's entire added value over the CLI.
3. **A verdict is never softened.** `unavailable` renders differently from
   `not_found`; the disclaimer travels with the result; the data-asset panel shows
   which rules still await expert sign-off.
4. **Progressive disclosure.** Ordinary users see a form and an answer. The derivation
   tree, the scan caliber switch and the gender override are reachable, not shouted.
5. **Local-first, zero network.** No HTTP service, no server, no telemetry. The
   `ProjectStore` JSON files are the only place data lands.
6. **Two languages, one string source.** Every UI string exists in both tables or the
   suite fails. The same rule applies to the documentation.
7. **One thread rule.** Engine work runs on a worker `QThread`; a `QThread` never
   touches a widget.

---

## 3. Layout

```
src/prokname_studio/
├── __init__.py            # __version__ (single source), MIN_PROKNAME_VERSION
├── __main__.py            # python -m prokname_studio
├── app.py                 # argument parsing, QApplication bootstrap
├── launcher.py            # PyInstaller entry point
├── main_window.py         # navigation, the switcher bar, the About box
├── state.py               # StudioState: the session the views share
├── i18n.py                # the zh / en string tables and the language signal
├── appearance.py          # light / dark palettes and the application stylesheet
├── icons.py               # SVG loading, runtime rasterisation, fallback glyph
├── worker.py              # the QThread contract and the re-entry guard
├── assets/icon.svg        # the one piece of artwork everything else derives from
├── views/                 # gen_view · route_view · check_view · project_view · data_view
└── components/            # derivation_view · verdict_view · project_table
```

Engine modules this project may import are a **pinned contract**
(`tests/test_boundaries.py`). `prokname.cli` is not in it: a command-line entry point
is not an API. Nothing reads the engine's source tree.

**Session state** (`state.py`) holds the current candidates, the selected project and
the last verdict. All of it is derived data — re-reading the engine rebuilds it — and
no rule is persisted here. `projects_changed` is the signal that keeps the Project
view honest after another view writes to the store.

---

## 4. The five views

### 4.1 Generate

`generate(stem, type, rank, genus=None, person_gender=None, gender_override=None,
genus_suffix=None, adjective_formation=None)`.

- Inputs: stem (required), etymology type, rank, genus when the rank needs it;
  `person_gender` appears only for `type=person`, and the genus-gender override only
  once a genus is filled. Advanced fields live in a collapsible group.
- Output: a candidate table (name, category, gender, compliance, derivation) plus the
  **derivation tree**, which is the point of the panel: *Beijing → place adjective →
  declines with the genus gender → neuter Rhizobium ⇒ -ense ⇒ Rhizobium beijingense*.
  Compliance renders green / amber / red; warnings render one per line.
- "Add to project" writes the selected candidate through `ProjectStore`.

### 4.2 Route

`route(source, candidatus=False, icnp_occupied=None)`.

Path cards, one per viable code path, each showing the code, its role and its
trade-offs. Warnings and notes — ICNP preemption, the GTDB boundary — appear as
statements, not as a tooltip. In the occupied case the guidance is highlighted rather
than presented as a dead end.

### 4.3 Check

`check_name(name, online=False, near_match=True, max_distance=2, near_match_mode="whole")`.

- Inputs: the name, the scan caliber (whole / stem / both), the maximum distance, and
  the online switch.
- Output: the verdict pill, a per-authority table (`found*` and `not_found` are
  distinguishable at a glance), and the near-match list labelled with the caliber used.
- The online switch is rendered disabled with the reason next to it — LPSN needs
  credentials, and the SeqCode Registry publishes no lookup-by-name — not as a grey
  box with no explanation.

### 4.4 Project

`ProjectStore` create / load / list / add_candidate / rate_candidate / export / delete.

Project list, candidate table with inline 0–5 scoring, and one-click export. Exports
reuse the engine's writers, so the disclaimer and the LPSN / SeqCode attribution are
in the file before Studio ever sees it.

### 4.5 Data assets

`data_assets.asset_status()` — version, gating status and consumer for each rule
asset, with the count of assertions still awaiting expert verification. This panel
exists so the engine's current coverage boundary is legible without reading source.

---

## 5. Internationalisation

- `i18n.py` holds `STRINGS = {"zh": {...}, "en": {...}}` as the **single source** for
  every UI-visible string. Views build text through `tr(key)`.
- `install(app, lang)` resolves `auto` from the desktop `QLocale`; Chinese locales map
  to `zh`, everything else to `en`.
- `set_language(lang)` emits `languageChanged`; the main window re-translates every
  widget in place. The switch is live: no restart, no lost candidates, no lost
  selection.
- Scope boundary: the engine's free-text output is the engine's to localise. A string
  the engine has not translated is shown as the engine wrote it rather than re-worded
  here.
- `tests/test_i18n_parity.py` reads the tables from source and fails on a key present
  in one language only, an untranslated reference, or an empty translation — so a
  half-translated screen cannot ship.

---

## 6. Appearance

- Three modes: follow the desktop, pin light, pin dark. `auto` re-applies the moment
  the OS changes scheme; an explicit choice is stored; `--theme` overrides for one run
  without writing anything.
- The engine's semantic colour tokens are specified against a light surface. On a dark
  surface each is **lifted** (`appearance.py`), and every lifted value must clear 4.5:1
  contrast against the dark base — a test, not an eyeball.
- A verdict pill on dark becomes a tinted, bordered pill rather than a solid bright
  block; table foregrounds and muted placeholder text follow the same mapping.
- Appearance and language are independent switches that never disturb each other or
  the session.

---

## 7. Threading

`worker.py` owns the contract: engine calls run on a `QThread`, results are delivered
back to the UI through signals, and the worker never touches a widget. Re-entry is
guarded, so a second press cannot start a second scan, and the "give the button back"
reset exists exactly once. An engine refusal is reported with its exception type
attached, because a bare `str(KeyError)` is an empty string and an empty error box
teaches the user nothing.

---

## 8. Icon and packaging

- **One vector file**, `assets/icon.svg`, ships in the wheel. `icons.py` rasterises it
  at runtime from 16 px to 512 px and sets it as the window icon; if Qt's SVG plugin is
  missing, a degraded glyph drawn from the same geometry is used instead of the
  platform's generic tile.
- The shell icon `ProkNameStudio.icns` is a **build product**, generated from the SVG
  by `scripts/make_bundle_icon.py`. Committing it would put a second copy of the
  artwork under version control with nothing to keep the two in step.
- `ProkNameStudio.spec` builds a onedir `.app`, `windowed`, for the architecture of the
  build machine (`target_arch=None`). It reads the
  version out of `__init__.py` rather than repeating it, so `Info.plist`, `--version`
  and the About box cannot disagree, and it refuses to freeze a bundle whose data
  assets did not resolve.
- The engine's rule assets travel with the bundle through `collect_data_files`, not a
  hand-written list: an asset added to `src/prokname/data/` must not need a matching
  edit here to appear in the app.
- CI builds the bundle, then checks that the frozen module set equals `src/`, that the
  icon and the engine assets and the Qt SVG plugin are physically inside it, and
  finally that the frozen window starts and is still alive seconds later.

---

## 9. Distribution

The `.app` is offered through GitHub Releases; a non-technical user drags it into
Applications. A read-only hosted web demo is explicitly **not** built: it would put
candidate names on a server, which is the one thing this front end exists to avoid.
Notarisation is optional and only removes the "unknown developer" prompt.

---

## 10. Testing

The front end re-implements no rules, so it does not duplicate the engine's tests. It
tests the shell:

- **View smoke** (`test_views_smoke.py`, `test_ui_polish.py`) — every view constructs
  under offscreen Qt, the key widgets exist, generation yields candidates, an engine
  call awaits without blocking the thread.
- **State** (`test_state.py`) — the shared session reads, writes and resets.
- **Contract** (`test_worker_contract.py`, `test_decision.py`) — the fields Studio
  reads from the engine must match what the engine publishes; a verdict is persisted
  only onto the name it was obtained for.
- **Presentation** (`test_appearance.py`, `test_icons.py`, `test_i18n.py`,
  `test_i18n_parity.py`) — mode resolution, contrast, the fallback glyph, string parity.
- **Structure** (`test_boundaries.py`, `test_spec.py`, `test_asset_freshness.py`,
  `test_citation_metadata.py`, `test_doc_language_pairs.py`, `test_doc_links.py`,
  `test_no_iteration_residue.py`) — the import contract, the bundle description,
  document language pairing, links that resolve, and iteration residue.

**No test may skip for a missing Qt.** PySide6 is a runtime dependency, so a run that
cannot import Qt has a broken install; CI parses the JUnit XML and fails if anything
skipped for a Qt reason. A skipped gate is not a gate.

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| Native GUI code is heavier than a web UI | The views are thin: form → one call → render. Interaction stays inside five panels. |
| An engine API change breaks the window | The contract tests and the CI smoke run go red before a user does. |
| Two string tables drift | The parity test reads the source and fails; CI runs it unconditionally. |
| A dark surface makes a verdict unreadable | Every token has a measured dark spelling with a contrast assertion. |
| A frozen bundle ships without an asset | The bundle job compares the frozen module set with `src/` and checks the files on disk. |
| Over-investing in the GUI ahead of the engine's expert sign-off | Studio adds no rules. The panels display what the engine already decides, including what it refuses to decide. |

---

## 12. Decisions held

1. **Language**: both, live, system default.
2. **Project storage**: the engine's `ProjectStore` default directory; Studio sets no
   custom path.
3. **Scope**: no naming logic in this repository, ever.
4. **Platforms**: macOS frozen and smoke-tested; Windows and Linux installed and tested.
5. **Theme**: light and dark, following the desktop by default.

---

## Appendix — the engine API this front end calls

```python
from prokname.engine.generate import generate          # candidates from an etymology
from prokname.engine.gender import get_genus_gender    # lexicon lookup + inference
from prokname.engine.orthography import validate_agreement
from prokname.dedup import check_name, Verdict         # two-tier dedup report
from prokname.routing import route, RouteSource        # dual-code paths + trade-offs
from prokname.storage import ProjectStore, Candidate   # the project a session edits
from prokname.engine import data as data_assets        # asset version and gating
from prokname.presentation import decision, theme      # verdict → colour contract
from prokname import __version__, DISCLAIMER           # what the About box reports
```

Every signature here is checked against the installed `prokname` distribution at test
time; if the engine refactors, the contract tests report it first.
