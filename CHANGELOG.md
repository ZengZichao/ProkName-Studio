# Changelog

[English](CHANGELOG.md) | [中文](CHANGELOG.zh.md)

All notable changes to ProkName Studio are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-09-29

First public release of **ProkName Studio**, the native desktop front end for
[prokname](https://github.com/ZengZichao/ProkName), the prokaryotic nomenclature
assistant. Studio puts the engine's terminal capability into a window: deterministic
etymology-driven name generation, gender-agreement validation, dual-code (ICNP / SeqCode)
routing and the two-tier dedup check.

Studio is a *front end*. It re-implements no naming rule: every number, verdict and badge
on screen is returned by `prokname`'s public API. The dependency runs one way — Studio
needs the engine, the engine never needs Qt — and it is expressed as a package name and a
repository URL, never as a path on one machine's disk.

### Added — the window

- **Five panels**: Generate, Route, Check, Project and Data assets. Each is a form, one
  call into the engine, and a rendering of the structured result — `engine.generate`,
  `engine.gender`, `engine.orthography`, `dedup.check_name`, `routing.route`,
  `storage.ProjectStore`, `presentation.decision`, `presentation.theme`.
- **The derivation tree.** The engine's `derivation` renders as a nested step tree
  (name → compliance / rank / category / gender / derivation / warnings) so the *why* of a
  candidate is visible, not just the string. Compliance shows in the tri-colour scheme and
  warnings render one per line.
- **The dedup verdict and its sources** are rendered as a centred pill plus a per-authority
  table and the near-match list, with the scan caliber labelled. "Unable to verify" and
  "nothing found" look different on screen, because they mean different things.
- **Route paths** appear as path cards carrying each code, its role and its trade-offs,
  with ICNP preemption and the GTDB boundary surfaced rather than buried.
- **Project work continues across surfaces**: candidates are written through the same
  `ProjectStore` as `prokname project`, ratings are entered inline, and exports reuse the
  engine's JSON / CSV / Markdown writers, so the disclaimer and the LPSN / SeqCode
  attribution travel with the file.
- **The data-asset panel** reports each rule file's version, gating status and consumer,
  including which assets still await expert sign-off — so the engine's current coverage
  boundary is visible without reading source.

### Added — language and appearance

- **Live Chinese / English switching** with no restart and nothing lost: the palette,
  stylesheet, verdict pills, table foregrounds, placeholder text, headers and tooltips all
  follow, and the session's candidates and current selection survive. `auto` follows the
  desktop locale, an explicit choice is remembered across launches, and `--lang` overrides
  for one run without writing anything.
- **A light / dark appearance switch** with the same three modes. Every semantic colour
  from the engine has a dark spelling, each lifted to clear 4.5:1 against the dark base,
  and a verdict pill becomes a tinted, bordered pill rather than a solid bright block.
  Appearance and language are independent: switching one never switches the other, and
  neither restarts the window.
- **Every string is translated**, including engine vocabulary surfaced in the UI
  (`adjective` → 形容词, `only-viable` → 唯一可行). A parity test reads the string tables
  from source and fails on a key present in one language only, an untranslated reference,
  or an empty translation.
- **An SVG application icon**: one vector file shipped with the app, rasterised at runtime
  from 16 px to 512 px and set as the window icon. If Qt's SVG plugin is missing, a
  degraded glyph drawn from the same geometry replaces it instead of the platform's
  generic tile.

### Added — versioning and packaging

- **Its own version number.** `prokname-studio --version` reports the Studio version and
  the engine version it is running against, and the About box shows both. The version is
  declared once, in `src/prokname_studio/__init__.py`; the build backend reads it
  dynamically, the PyInstaller spec re-reads that literal rather than duplicating it, and
  `CITATION.cff` mirrors it — so a released build cannot carry three different numbers.
- **A frozen macOS application** built from `ProkNameStudio.spec`: onedir bundle,
  frozen for the architecture of the machine that built it (`target_arch=None`, so
  arm64 on Apple Silicon), no console window, the icon generated from the SVG by
  `scripts/make_bundle_icon.py`, and the engine's rule assets collected into the bundle
  rather than hand-listed. The generated `.icns` is deliberately not committed: one piece
  of artwork, everything else derived.
- `prokname-studio` as the console entry point, with `python -m prokname_studio`
  equivalent.

### Behaviour and guarantees

- **One thread rule.** Engine work runs on a worker `QThread` that never touches a widget;
  re-entry is guarded so a second press cannot start a second scan; the "give the button
  back" reset exists once. An engine refusal is reported with its exception type attached,
  because a bare `str(KeyError)` is an empty string.
- **Local-first, zero network.** Studio starts no HTTP service and holds no server.
  Candidates stay on the user's disk, no input is collected or uploaded, and no credential
  is stored. The online switch is shown disabled with the actual reason next to it — LPSN
  needs credentials, and the SeqCode Registry publishes no lookup-by-name — rather than a
  stale excuse or a silent grey box.
- **Verdict colours are the engine's tokens.** `prokname.presentation.decision` and
  `.theme` stay in the engine as the shared verdict-and-colour map, so a verdict cannot
  look urgent in the terminal and calm in the window. How those tokens render on a light or
  a dark surface is Studio's decision, and lives here.
- **`--debug`** forwards to `prokname.diagnostics.configure()`, the same call the engine's
  CLI makes: it echoes third-party client output the engine normally swallows, and changes
  no verdict and no exit code.
- Read paths go through the installed `prokname` distribution — the project store, the rule
  assets, the dedup cache — never through a sibling source tree.

### Quality gates

- `tests/test_appearance.py` — mode resolution, every semantic token's dark spelling, and
  its measured contrast on the dark surface.
- `tests/test_icons.py` — SVG loading and the fallback glyph.
- `tests/test_spec.py` — the bundle description resolves the version literal, refuses to
  freeze a bundle whose declared version could drift, and ships the assets.
- `tests/test_i18n_parity.py` — string parity between the two languages, read from source,
  so it runs without a Qt session.
- `tests/test_boundaries.py` — the engine modules Studio may import are a pinned contract;
  `prokname.cli` is never one of them; no document may name a path that resolves on one
  machine only.
- `tests/test_doc_language_pairs.py` and `tests/test_doc_links.py` — every document ships in
  both languages with English first, and no link or anchor resolves to nothing.
- `tests/test_citation_metadata.py` — `CITATION.cff` stays a mirror of the version literal,
  the author, the repository URL and the cut release date.
- View smoke tests and a worker-contract test run **unconditionally**: PySide6 is a runtime
  dependency, so no test may skip for a missing Qt. A run that cannot import Qt has a broken
  install, and a skipped gate is not a gate. CI asserts this from the JUnit XML rather than
  scraping stdout.
- The CI `bundle` job builds the `.app` on macOS, verifies the frozen PYZ module set equals
  `src/`, checks that the icon, the engine rule assets and the Qt SVG plugin reached the
  bundle, and then starts the frozen window and requires it to still be alive.

### Known limitations

- Studio inherits every engine limitation listed in the
  [engine changelog](https://github.com/ZengZichao/ProkName/blob/main/CHANGELOG.md),
  above all that rule assets still await expert sign-off and `check` cannot yet clear a
  name in the field. The window does not soften those facts.
- The engine's free-text output (derivation and warning sentences) is translated by the
  engine, not by Studio; a string the engine has not localised appears as the engine wrote
  it.
- Bundled distribution is built and verified for macOS, for the architecture of the
  machine that builds it — the released `.app` is arm64. Intel Macs are covered by
  installing from source. Windows and Linux are exercised in
  CI as install-and-test targets, not as frozen bundles.
