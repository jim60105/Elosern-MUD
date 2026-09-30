## 1. Preconditions, import, and baseline

- [ ] 1.1 Confirm `web/webclient-app/lib/mono_cells.js` exists on master (`webclient-map-label-cell-budget` merged) and the upstream Jim Mono TC release is published with a `-web.zip` in its `SHA256SUMS.txt`. Download it to the session scratchpad and check it against D0: group names, every file ≤ 65,536 bytes, `licenses/LICENSE` present. Verify: all hold. If the release is missing or breaks D0, stop and report to the owner; do not cut fonts here.
- [ ] 1.2 Build the unmodified app and Storybook. Capture the D9 before-set with agent-browser (headless, throwaway Chromium) at 1440×900 and 1280×720 into the session scratchpad, and record CDP's rendered family for a `kbd` and a map-art line. Verify: every D9 surface has a before-shot at both viewports, and `agent-browser close` has run.
- [ ] 1.3 Add `tools/import_mono_font.py` per D1 with the release URL and SHA-256 pinned, and `tests/test_mono_font_import_tool.py`. Verify:
  - `uv run --locked python -m unittest tests.test_mono_font_import_tool` passes without network access;
  - flipping one byte of the pinned SHA-256 makes the tool exit non-zero without touching the worktree.
- [ ] 1.4 Run the tool and commit `web/webclient-app/fonts/jimmonotc/**` and `web/webclient-app/styles/fonts-mono.css`. Add `tests/test_mono_font_contract.py` per D1 (no `@covers_requirement` yet, D8). Verify:
  - a second run leaves `git status` clean;
  - `uv run --locked python -m unittest tests.test_mono_font_contract` passes;
  - deleting one slice, adding an overlapping range, changing one `cjk.bold` entry, or removing `licenses/LICENSE` makes it fail.

## 2. Wire the face and remove Hack

- [ ] 2.1 Replace the `fonts-hack.css` imports in `web/webclient-app/main.js` and `.storybook/preview.js` with `fonts-mono.css`, and set `--f-mono: "Jim Mono TC", "Noto Sans TC", monospace;` with its comment in `styles/tokens.css` (D2). Verify:
  - `pnpm run build` succeeds;
  - `dist/index.css` has Jim Mono TC rules for weights 400 and 700;
  - every non-data URL points at an existing `dist/assets/JimMonoTC-*.woff2`.
- [ ] 2.2 Repoint `tools/gen_mono_cells.py` to `fonts/jimmonotc/codepoints.json` (`regular`) and regenerate `mono_cells.js` (D3). Verify:
  - `uv run --locked python -m unittest tests.test_mono_cells_table` passes;
  - `CI=true pnpm exec vitest run web/webclient-app/tests/world` passes;
  - the helper still reports `中` = 2, `…` = 1, `─` = 1.
- [ ] 2.3 Delete the Hack pipeline (D4) and add the `--f-mono` exact-stack check to `tests/test_mono_font_contract.py` (D6). Verify:
  - `git grep -n -i "fonts-hack\|gen_hack_font\|fonts/hack"` finds only archived openspec text;
  - `uv run --locked python -m unittest tests.test_mono_font_contract` passes.

## 3. Browser tests

- [ ] 3.1 Update `test_keycaps_and_command_input_keep_monospace` and `rendered_fonts` to Jim Mono TC per D5. Verify:
  - as a shell step, `rm -rf .storybook-out` and rebuild;
  - the method passes alone through `web.tests.browser.unittest_driver`;
  - with `--f-mono` temporarily reverted to the Hack stack, it fails.
- [ ] 3.2 Add `test_monospace_cells_are_exact` (D5) and register it in `.github/browser-shards.json`. Verify: it passes alone, and `uv run --locked python -m unittest tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract` passes.
- [ ] 3.3 Update `test_vue_foundation` to `_assert_only_needed_mono_slices` with the D5 names and family. Verify: `test_vue_bundle_loads_from_origin_offline` passes alone.
- [ ] 3.4 Run `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate` on the branch. The Hack ID stays on the kept tests (D8). Verify: both pass.

## 4. Layout re-verification

- [ ] 4.1 Re-run the focused map oracle, one method per command. Verify: all pass, and no assertion is loosened.
  - `test_browser_local_map_lattice`: `test_densely_populated_lattice_scales_down_without_reintroducing_overlap`, `test_crowded_edge_overlay_marker_names_stay_separated_and_outside_canvas`, `test_long_remembered_list_never_resizes_the_island`
  - `test_browser_local_map_geometry`: `test_minimap_content_stays_inside_its_island`, `test_island_type_ladder_stays_under_its_own_chrome_step`
  - `test_browser_map_legibility`: all three methods
  - `test_browser_local_map_layout_variants`: `test_walked_instance_layer_renders_radial_on_both_surfaces`
- [ ] 4.2 Re-run the HTML-surface checks as focused methods. Verify: all pass. Any clipping is fixed per D7 and listed.
  - `test_browser_shell_surfaces.ShellAcceptanceTest.test_populated_island_stack_fits_its_anchor_at_both_viewports`
  - `test_browser_shell_command_line`: `test_command_line_field_button_alignment_at_both_viewports`, `test_keyboard_field_focus_send_cancel_and_focus_restoration`, `test_toggle_collapses_and_keeps_focus`
  - `test_browser_contextual_hud_stage`: `test_prose_typesetting_follows_the_measured_column`, `test_command_line_never_overlaps_dock_caption_or_hud`
  - `test_vue_typography`: the remaining methods
- [ ] 4.3 Capture the D9 after-set with agent-browser, plus the CJK grid probe and the headless-shell warm and cold box-grid renders, and compare each against 1.2. Verify, and record the findings in the apply summary:
  - grid strokes join;
  - the probe's CJK columns align;
  - no clipping or overlap;
  - CDP reports Jim Mono TC (custom) for Latin and CJK monospace text;
  - ligatures look right;
  - the cold-cache swap is acceptable.

  Run `agent-browser close` afterwards.

## 5. Docs

- [ ] 5.1 Update `docs/development/frontend-developer-guide.md`:
  - the tree lists `fonts/jimmonotc/` and `styles/fonts-mono.css`;
  - the 等寬字體 section describes Jim Mono TC, two-cell CJK, ligatures, the slice groups, and the upstream release as the source, and the regeneration commands for both `tools.import_mono_font` and `gen_mono_cells.py`;
  - the Hack text is removed.

  Update `docs/development/frontend-vue-architecture.md` to name Jim Mono TC. Verify: `git grep -n -i "hack" docs/development` shows only the note that Jim Mono TC's Latin comes from Hack.

## 6. Gates

- [ ] 6.1 Run the gates. Verify: all green.
  - `CI=true pnpm test`
  - `node --test web/static/webclient/js/tests/*.test.js`
  - `uv run --locked python -m unittest discover -s tests -t .`
  - `uv run --locked python -m tools.contract_gate`
  - `pnpm run showcase-coverage`
  - `openspec validate webclient-jim-mono-tc-font --strict`

## 7. Requirement traceability (lands with archive)

- [ ] 7.1 After the spec sync (archive), confirm with `uv run --locked python -m tools.spec_traceability list` that `webclient-vue-application::the-monospace-type-role-is-a-self-hosted-sliced-jim-mono-tc-face` exists and the Hack ID is gone. Apply D8 (IDs as string literals). Verify: `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate` pass, and the sync and decorators land in one commit.
