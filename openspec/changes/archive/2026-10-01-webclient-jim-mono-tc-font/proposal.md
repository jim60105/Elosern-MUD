## Why

The monospace type role now draws Latin in the bundled Hack slices and CJK in the bundled
proportional Noto Sans TC. That mix has three problems:

- CJK in monospace surfaces is 1 em wide, while Latin cells are 0.602 em, so a box-drawing grid that
  holds CJK (`│  北面出口：石階  │`) never lines up column for column.
- Local-map labels mix two unrelated faces.
- The CJK in the command line looks like body text.

The project owner builds Jim Mono TC (https://github.com/jim60105/JimMonoTC, SIL OFL 1.1). It merges
Hack 3.003 for Latin and Noto Sans CJK TC 2.004 for CJK, and every CJK character is exactly two Latin
cells wide. That is the monospace behavior the UI wants, from a single family. The owner keeps the
font's programming ligatures.

The v0.1.0 web release slices are too large for the project's small-file rule (87 KB to 1.6 MB each).
The owner re-slices the web build upstream into small, frequency-ordered slices and publishes a new
release. This change imports that release; it does not cut fonts itself.

## What Changes

- Add `tools/import_mono_font.py` (standard library only). It:
  - downloads the pinned Jim Mono TC `-web.zip` release asset and verifies its SHA-256;
  - keeps the Regular and Bold slices of the Latin groups (`latin`, `latin-ext`, `greek-cyrillic`,
    `box`, `symbols`) and the frequency CJK groups (`cjk-<N>`), and drops Nerd Fonts icon slices and
    the rare-CJK remainder;
  - filters the release `JimMonoTC.css` to the kept files, rewrites the URLs to relative project paths,
    and writes `web/webclient-app/styles/fonts-mono.css`;
  - writes `web/webclient-app/fonts/jimmonotc/` (the kept slices, `codepoints.json`, and the release's
    `licenses/` tree);
  - refuses to write when a kept slice exceeds 64 KB, the two weights' CJK sets differ, or the kept
    ranges overlap.
- Wire it in:
  - import `styles/fonts-mono.css` in `web/webclient-app/main.js` and `.storybook/preview.js` in place
    of `fonts-hack.css`;
  - set `--f-mono: "Jim Mono TC", "Noto Sans TC", monospace;`. Noto Sans TC stays only as the fallback
    for CJK outside the shipped coverage.
- Point the map cell table from `webclient-map-label-cell-budget` at the Jim Mono TC manifest's
  one-cell set, and regenerate it.
- Remove Hack: `tools/gen_hack_font_slices.py`, `web/webclient-app/fonts/hack/`,
  `styles/fonts-hack.css`, and the Hack slice tests. The Hack glyphs live on inside Jim Mono TC.
- Update the tests:
  - an import tool test and a committed-file contract test;
  - the rendered-face browser checks require a bundled Jim Mono TC face for Latin and CJK;
  - a new browser check measures CJK at exactly two Latin cells in regular and bold, `…` and `─` at
    one cell, and the ligature `->` at two cells;
  - the offline slice-loading check uses the new slice names;
  - traceability decorators move to the new requirement ID at archive time.
- Re-verify the map and HTML surfaces:
  - focused browser tests, plus agent-browser before/after screenshots;
  - box grids must join, and CJK inside grids must now align column for column;
  - HTML rows that clip 1.204 em CJK get CSS fixes in this change.
- Update the docs.

## Capabilities

### New Capabilities

(none)

### Modified Capabilities

- `webclient-vue-application`: the requirement "The monospace type role is a self-hosted, sliced Hack
  face" is replaced by "The monospace type role is a self-hosted, sliced Jim Mono TC face":
  - one bundled family draws Latin and CJK, with CJK exactly two Latin cells wide in both weights;
  - box-drawing strokes join;
  - ligatures stay enabled without changing cell counts;
  - the slice size bound and the licence files.

## Impact

- **Depends on**:
  - `webclient-map-label-cell-budget`, because map geometry must budget CJK at two cells;
  - an upstream Jim Mono TC release (planned as v0.2.0) whose `-web.zip` meets the slice contract in
    design D0. This is work in the JimMonoTC repository, not an OpenSpec change here.
- **Styles**: `styles/tokens.css`, `web/webclient-app/main.js`, `.storybook/preview.js`, and possibly
  CSS fixes in HTML monospace surfaces:
  - the command line;
  - `DockMenu`;
  - `.local-map` rows (note `letter-spacing: .04em` at `LocalMap.vue:344`, which also disables
    ligatures there);
  - the full log;
  - message map-art headings.
- **Assets**: adds `web/webclient-app/fonts/jimmonotc/` (about 200 slices, roughly 6 MB with bold CJK)
  and `styles/fonts-mono.css`; removes `web/webclient-app/fonts/hack/` (about 152 KB) and
  `styles/fonts-hack.css`.
- **Tooling**: adds `tools/import_mono_font.py`; repoints `tools/gen_mono_cells.py`'s manifest
  constant; deletes `tools/gen_hack_font_slices.py`.
- **Tests**:
  - new: `tests/test_mono_font_import_tool.py` and `tests/test_mono_font_contract.py`;
  - `web/tests/browser/test_vue_typography.py` (plus a new method, already owned by the class's label in
    `.github/browser-shards.json`);
  - `web/tests/browser/test_vue_foundation.py`;
  - `tests/test_mono_cells_table.py`, regenerated;
  - deleted: `tests/test_hack_font_slices_*.py`;
  - at archive, the `@covers_requirement` decorators in `test_browser_local_map_lattice.py`.
- **Docs**: `docs/development/frontend-developer-guide.md`, `docs/development/frontend-vue-architecture.md`.
- **Runtime**: `index.css` grows by about 200 Jim Mono TC `@font-face` rules. Small slices are inlined.
  A page downloads only the slices it draws.
- **Size**: this change is close to the one-day ceiling. If apply overruns, the import tool and its
  tests (design D0–D1, tasks 1.x) split out as their own change ahead of the wiring.
