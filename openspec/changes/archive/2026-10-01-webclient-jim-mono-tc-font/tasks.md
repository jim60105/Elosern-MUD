## 1. Preconditions, import, and baseline

- [x] 1.1 Confirm `web/webclient-app/lib/mono_cells.js` exists on master (`webclient-map-label-cell-budget` merged) and the upstream Jim Mono TC release is published with a `-web.zip` in its `SHA256SUMS.txt`. Download it to the session scratchpad and check it against D0: group names, every file ≤ 65,536 bytes, `licenses/LICENSE` present. Verify: all hold. If the release is missing or breaks D0, stop and report to the owner; do not cut fonts here.
- [x] 1.2 Build the unmodified app and Storybook. Capture the D9 before-set with agent-browser (headless, throwaway Chromium) at 1440×900 and 1280×720 into the session scratchpad, and record CDP's rendered family for a `kbd` and a map-art line. Verify: every D9 surface has a before-shot at both viewports, and `agent-browser close` has run.
- [x] 1.3 Add `tools/import_mono_font.py` per D1 with the release URL and SHA-256 pinned, and `tests/test_mono_font_import_tool.py`. Verify:
  - `uv run --locked python -m unittest tests.test_mono_font_import_tool` passes without network access;
  - flipping one byte of the pinned SHA-256 makes the tool exit non-zero without touching the worktree.
- [x] 1.4 Run the tool and commit `web/webclient-app/fonts/jimmonotc/**` and `web/webclient-app/styles/fonts-mono.css`. Add `tests/test_mono_font_contract.py` per D1 (no `@covers_requirement` yet, D8). Verify:
  - a second run leaves `git status` clean;
  - `uv run --locked python -m unittest tests.test_mono_font_contract` passes;
  - deleting one slice, adding an overlapping range, changing one `cjk.bold` entry, or removing `licenses/LICENSE` makes it fail.

## 2. Wire the face and remove Hack

- [x] 2.1 Replace the `fonts-hack.css` imports in `web/webclient-app/main.js` and `.storybook/preview.js` with `fonts-mono.css`, and set `--f-mono: "Jim Mono TC", "Noto Sans TC", monospace;` with its comment in `styles/tokens.css` (D2). Verify:
  - `pnpm run build` succeeds;
  - `dist/index.css` has Jim Mono TC rules for weights 400 and 700;
  - every non-data URL points at an existing `dist/assets/JimMonoTC-*.woff2`.
- [x] 2.2 Repoint `tools/gen_mono_cells.py` to `fonts/jimmonotc/codepoints.json` (`regular`) and regenerate `mono_cells.js` (D3). Verify:
  - `uv run --locked python -m unittest tests.test_mono_cells_table` passes;
  - `CI=true pnpm exec vitest run web/webclient-app/tests/world` passes;
  - the helper still reports `中` = 2, `…` = 1, `─` = 1.
- [x] 2.3 Delete the Hack pipeline (D4) and add the `--f-mono` exact-stack check to `tests/test_mono_font_contract.py` (D6). Verify:
  - `git grep -n -i "fonts-hack\|gen_hack_font\|fonts/hack"` finds only archived openspec text;
  - `uv run --locked python -m unittest tests.test_mono_font_contract` passes.

## 3. Browser tests

- [x] 3.1 Update `test_keycaps_and_command_input_keep_monospace` and `rendered_fonts` to Jim Mono TC per D5. Verify:
  - as a shell step, `rm -rf .storybook-out` and rebuild;
  - the method passes alone through `web.tests.browser.unittest_driver`;
  - with `--f-mono` temporarily reverted to the Hack stack, it fails.
- [x] 3.2 Add `test_monospace_cells_are_exact` (D5); `.github/browser-shards.json` owns it through the existing `VueTypographyBrowserTest` class label. Verify: it passes alone, and `uv run --locked python -m unittest tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract` passes.
- [x] 3.3 Update `test_vue_foundation` to `_assert_only_needed_mono_slices` with the D5 names and family. Verify: `test_vue_bundle_loads_from_origin_offline` passes alone.
- [x] 3.4 Run `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate` on the branch. The Hack ID stays on the kept tests (D8). Verify: both pass.

## 4. Layout re-verification

- [x] 4.1 Re-run the focused map oracle, one method per command. Verify: all pass, and no assertion is loosened.
  - `test_browser_local_map_lattice`: `test_densely_populated_lattice_scales_down_without_reintroducing_overlap`, `test_crowded_edge_overlay_marker_names_stay_separated_and_outside_canvas`, `test_long_remembered_list_never_resizes_the_island`
  - `test_browser_local_map_geometry`: `test_minimap_content_stays_inside_its_island`, `test_island_type_ladder_stays_under_its_own_chrome_step`
  - `test_browser_map_legibility`: all three methods
  - `test_browser_local_map_layout_variants`: `test_walked_instance_layer_renders_radial_on_both_surfaces`
- [x] 4.2 Re-run the HTML-surface checks as focused methods. Verify: all pass. Any clipping is fixed per D7 and listed.
  - `test_browser_shell_surfaces.ShellAcceptanceTest.test_populated_island_stack_fits_its_anchor_at_both_viewports`
  - `test_browser_shell_command_line`: `test_command_line_field_button_alignment_at_both_viewports`, `test_keyboard_field_focus_send_cancel_and_focus_restoration`, `test_toggle_collapses_and_keeps_focus`
  - `test_browser_contextual_hud_stage`: `test_prose_typesetting_follows_the_measured_column`, `test_command_line_never_overlaps_dock_caption_or_hud`
  - `test_vue_typography`: the remaining methods
- [x] 4.3 Capture the D9 after-set with agent-browser, plus the CJK grid probe and the headless-shell warm and cold box-grid renders, and compare each against 1.2. Verify, and record the findings in the apply summary:
  - grid strokes join;
  - the probe's CJK columns align;
  - no clipping or overlap;
  - CDP reports Jim Mono TC (custom) for Latin and CJK monospace text;
  - ligatures look right;
  - the cold-cache swap is acceptable.

  Run `agent-browser close` afterwards.

## 5. Docs

- [x] 5.1 Update `docs/development/frontend-developer-guide.md`:
  - the tree lists `fonts/jimmonotc/` and `styles/fonts-mono.css`;
  - the 等寬字體 section describes Jim Mono TC, two-cell CJK, ligatures, the slice groups, and the upstream release as the source, and the regeneration commands for both `tools.import_mono_font` and `gen_mono_cells.py`;
  - the Hack text is removed.

  Update `docs/development/frontend-vue-architecture.md` to name Jim Mono TC. Verify: `git grep -n -i "hack" docs/development` shows only the note that Jim Mono TC's Latin comes from Hack.

## 6. Gates

- [x] 6.1 Run the gates. Verify: all green.
  - `CI=true pnpm test`
  - `node --test web/static/webclient/js/tests/*.test.js`
  - `uv run --locked python -m unittest discover -s tests -t .`
  - `uv run --locked python -m tools.contract_gate`
  - `pnpm run showcase-coverage`
  - `openspec validate webclient-jim-mono-tc-font --strict`

## 7. Requirement traceability (lands with archive)

- [x] 7.1 After the spec sync (archive), confirm with `uv run --locked python -m tools.spec_traceability list` that `webclient-vue-application::the-monospace-type-role-is-a-self-hosted-sliced-jim-mono-tc-face` exists and the Hack ID is gone. Apply D8 (IDs as string literals). Verify: `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate` pass, and the sync and decorators land in one commit.

## Apply notes

- **Release (1.1).** `JimMonoTC-0.2.0-web.zip`, SHA-256 `ac2c3382…8dab` (from `SHA256SUMS.txt`), meets D0. Kept: 196 slices, 5,945,920 bytes, 1,804–48,920 bytes each. Regular one-cell 1,543 code points, Bold 1,619; CJK 13,283 in both weights, all inside the Noto Sans TC 400 East Asian Wide/Fullwidth coverage; `noto_wide_missing` 213 (emoji-like symbols such as ⌚ ⏩ ☔ ♈). The `box` and `cjk-87` slices sit under Vite's 4 KB inline limit and ship as data URIs.
- **Import tool.** Beyond D1, it rejects symlinks and licence member names outside a safe pattern (no `..`), stages the font tree beside `fonts/jimmonotc/` and swaps it in, then writes `fonts-mono.css` last. `.gitattributes` marks `fonts/jimmonotc/licenses/**` as `-text`, so the two CRLF licence texts stay byte-identical to the release.
- **Map cell table (D3).** It keeps the Regular one-cell set. Map labels never render at weight 700, and any code point outside the set counts as two cells, which is the conservative side. The table loses the Nerd Fonts powerline code points (U+E0A0–E0B3) and U+25FD/25FE (now wide) and gains U+23FB–23FE, U+2630, U+2665, U+2B58.
- **Shards (3.2).** `.github/browser-shards.json` already owns `VueTypographyBrowserTest` by class label, so no edit was needed.
- **Probe (3.2).** The probe spans go on `document.body`. The frozen-contract scan flags a `#storybook-root` literal.
- **Rendered faces (1.2 / 4.3).** CDP reported `Hack` for `kbd` and the map art before the change, with `Noto Sans TC` drawing CJK. After the change it reports `Jim Mono TC` (custom) for `kbd`, the map art, the CJK grid probe, and the typed command input.
- **CJK grid probe (4.3).** The x positions of `│` in the probe (`┌────┐ / │北門│ / └────┘` plus a 4-row CJK/ASCII grid at 20 px) were 116/104/108 per row before. After, every row is at 32/116/200, so the columns align and the strokes join.
- **D7 surfaces.** No CSS fix was needed.
  - All focused oracle methods in 4.1 and 4.2 pass unchanged.
  - The after-shots at 1440×900 and 1280×720 show no clipping or overlap on 11 surfaces: HUD keycaps, command line with `look north 看看 42`, help overlay arrow rows, dialogue numbers, bold party badges, island map, full-map overlay, box-grid message, mixed-scripts message, full log, and DockMenu.
  - Island map labels (`碼頭 霧骨渡口 南門`) now sit closer together because CJK is 20% wider, but they stay separated. The geometry tests pin this.
  - The full-log fixture's CJK box rows still do not line up. Their cell counts differ (see D9), so this is not a font issue.
- **Ligatures.** `->` draws as a ligature only where ASCII forms it (`a->b` in the probe). The run keeps its two cells.
- **Cold cache (throttled at 200 KB/s, cache disabled).** Box strokes join on first paint because the `box` slice is inlined. Latin and CJK swap in with `font-display: swap`. This is acceptable.
- **Task 7.1** lands with the archive (D8), so it stays open on this branch.
- **Post-implementation review.**
  - The write path now renames the old font tree aside, swaps the staged one in, and replaces the sheet through a temporary file. A failure leaves the old outputs and no staging leftovers, and a test covers it.
  - The tool now rejects duplicate zip members.
  - The contract test pins the Regular-only one-cell code points (U+03F6, U+2215, U+2219), so a release that drops more from Bold gets reviewed.
  - The two-cell overestimate for fallback glyphs is already documented in the header of `mono_cells.js`.
