## 1. Baseline capture (before any edit)

- [x] 1.1 On an unmodified checkout, in the environment that will also run the after-set, run `pnpm run build`. Capture the D8 surface set with agent-browser (headless, throwaway Chromium) at 1440×900 and 1280×720 into the session scratchpad, and note which monospace family CDP reports for a `kbd` today. Verify: every D8 surface has a before-screenshot at both viewports, the old rendered family is recorded, and `agent-browser close` has been run.

## 2. Slice generator and vendored assets

- [x] 2.1 Add `tools/gen_hack_font_slices.py` as described in D6. Verify: `uv run --script tools/gen_hack_font_slices.py` exits 0 and prints 10 slices, each ≤ 40960 bytes.
  - PEP 723 inline metadata pinning `fonttools==4.66.1` and `brotli==1.2.0`.
  - Pure helpers, importable without fontTools:
    - the D2 claim-window table;
    - first-claim assignment;
    - collapsing code points into runs;
    - `@font-face` CSS rendering: header, family `'Hack'`, weights 400/700, `font-display: swap`, relative `url(../fonts/hack/hack-<weight>.<slice>.woff2)`, declared ranges built from the claimed sets.
  - Entry point steps:
    1. Download `Hack-v3.003-ttf.tar.xz` and the tag's `LICENSE.md` and verify both D1 SHA-256 values.
    2. Open the TTFs with `TTFont(..., recalcTimestamp=False)`.
    3. Subset with hints kept, `TTFA` dropped, name IDs 0–6/13/14, and `font.flavor = "woff2"` before save.
    4. Slice twice and fail if the bytes differ.
    5. Write the slices, `LICENSE.md`, and a code-point manifest (`fonts/hack/codepoints.json`: Hack's cmap code points minus the exclusion set U+0000/U+000D/U+FEFF, per weight). Fail if any manifest code point is unclaimed or if the declared ranges of one weight overlap.
    6. Print a size table and fail if any slice exceeds 40960 bytes or is under 4096 bytes.
- [x] 2.2 Add `tests/test_hack_font_slices_tool.py`. Verify: `uv run --locked python -m unittest tests.test_hack_font_slices_tool` passes in the project env, which does not have fontTools. It covers:
  - run collapsing (adjacent, single, gapped);
  - first-claim assignment: U+2190–2193 land in `latin` only; code points outside every window are dropped;
  - CSS rendering: declared ranges come only from claimed code points, stay disjoint, and never include U+2328 or U+2715.
- [x] 2.3 Run the generator and commit its outputs:
  - `web/webclient-app/fonts/hack/hack-{regular,bold}.{latin,latin-ext,greek-cyrillic,box,symbols}.woff2`
  - `web/webclient-app/fonts/hack/LICENSE.md`
  - `web/webclient-app/fonts/hack/codepoints.json`
  - `web/webclient-app/styles/fonts-hack.css`

  Verify:
  - a second generator run leaves `git status` clean (byte-reproducible);
  - each slice starts with `wOF2` (`head -c4`);
  - every slice is ≤ 40 KB.

## 3. Wire the face into the app

- [x] 3.1 Import `./styles/fonts-hack.css` in `web/webclient-app/main.js` right after `fonts.css`. In `.storybook/preview.js`, import `../web/webclient-app/styles/fonts-hack.css` right after its `fonts.css` import. Verify: `pnpm run build` succeeds, and `web/static/webclient/app/dist/index.css` has 10 Hack `@font-face` rules whose URLs point at existing `/static/webclient/app/dist/assets/hack-*.woff2` files.
- [x] 3.2 In `web/webclient-app/styles/tokens.css`, set `--f-mono: "Hack", "Noto Sans TC", monospace;` and update the neighbouring comment: a bundled Latin/box face plus a bundled CJK fallback, with no machine font ahead of them. Verify: `grep -- '--f-mono' web/webclient-app/styles/tokens.css` shows exactly that stack.
- [x] 3.3 Update the comments that describe the monospace token as full-width CJK only, so they state that CJK is drawn by Noto Sans TC at 1 em, ASCII by Hack at 0.602 em, and the one-em-per-code-point bound still holds. No numbers change. Verify: `git diff` on these files changes comments only. Files and comments:
  - `composables/use-map-lattice-geometry.js`: the label-clearance note;
  - `components/MapLattice.vue`: the `markerNameFont` note;
  - `composables/use-map-lattice-render.js`: the marker-ascent note;
  - `tests/world/map_lattice_renderer.test.js`: the "11px monospace line box" note;
  - `tests/world/map_lattice_edge_names.test.js`: the "full-width CJK in a monospace token" note.

## 4. Tests

- [x] 4.1 Add `tests/test_hack_font_slices_contract.py` for the D7 slice contract. It checks:
  - every URL resolves, and every file is referenced;
  - each file has the `wOF2` magic and is between 4096 and 40960 bytes;
  - declared ranges are pairwise disjoint per weight;
  - their union equals `codepoints.json`;
  - arrows appear only in `latin`;
  - no range reaches into CJK;
  - both weights are declared;
  - `LICENSE.md` is present;
  - `--f-mono` equals the D5 stack.

  Verify: `uv run --locked python -m unittest tests.test_hack_font_slices_contract` passes. Temporarily deleting one slice or adding an overlapping range makes it fail.
- [ ] 4.2 Extend `web/tests/browser/test_vue_typography.py::VueTypographyBrowserTest::test_keycaps_and_command_input_keep_monospace` with the D7 CDP check:
  - run after `document.fonts.ready`, then `DOM.enable`, `CSS.enable`, `DOM.getDocument`, `DOM.querySelector`, `CSS.getPlatformFontsForNode`;
  - the first `kbd`, `.cmdfield__prompt`, and `#inputfield` report a font whose `familyName` starts with `Hack` and has `isCustomFont`. For `#inputfield` (a `<textarea>`), type `look 42 看看`, take a fresh `DOM.getDocument({depth: -1, pierce: true})`, and read its user-agent shadow `DIV` and that DIV's text child;
  - the same shadow `DIV` also reports a custom font whose `familyName` starts with `Noto Sans TC` (the CJK scenario);
  - a missing CDP method fails the test rather than skipping it;
  - confirm the reported `familyName` string once;
  
  Verify: as a shell step before the run (not inside the test), `rm -rf .storybook-out`; then run the method alone with `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_vue_typography.VueTypographyBrowserTest.test_keycaps_and_command_input_keep_monospace`. It passes. Temporarily reverting `--f-mono` to the old stack, rebuilding Storybook, and re-running makes it fail.
- [ ] 4.3 Extend `web/tests/browser/test_vue_foundation.py::VueFoundationBrowserTest::test_vue_bundle_loads_from_origin_offline` with the D7 ordering:
  1. make monospace ASCII text visible: the dock legend `kbd` if it is rendered, otherwise open the command line;
  2. wait for `document.fonts.ready` and for a loaded `FontFace` whose family is Hack;
  3. assert the positive case: an origin response whose slice name, with Vite's `-<hash>` suffix stripped, is exactly `hack-regular.latin`;
  4. assert the negative case: no response whose slice name is `hack-*.greek-cyrillic` or `hack-*.latin-ext`. On failure, list the Hack-styled code points outside `latin`.

  Verify: running the method alone through the unittest driver passes.
- [ ] 4.4 If 4.2 or 4.3 added a new browser test method or class instead of extending an existing one, register it in `.github/browser-shards.json` in the same commit. Do not add the new requirement ID to any `@covers_requirement` decorator yet (see group 7). Verify: `uv run --locked python -m tools.contract_gate manifests contracts` passes.
- [ ] 4.5 Run `openspec validate webclient-hack-mono-font --strict` now that tests reference the requirement. Verify: valid.

## 5. Map and layout re-verification (no 跑版)

- [ ] 5.1 Re-run the map geometry oracle as focused methods, one method per command (never a whole file; each within the 10-minute cap). Verify: every method passes and no assertion was loosened.
  - `test_browser_local_map_lattice`:
    - `test_densely_populated_lattice_scales_down_without_reintroducing_overlap`
    - `test_crowded_edge_overlay_marker_names_stay_separated_and_outside_canvas`
    - `test_long_remembered_list_never_resizes_the_island`
  - `test_browser_local_map_geometry`:
    - `test_minimap_content_stays_inside_its_island`
    - `test_island_type_ladder_stays_under_its_own_chrome_step`
  - `test_browser_map_legibility`: each of its three methods.
  - `test_browser_local_map_layout_variants.test_walked_instance_layer_renders_radial_on_both_surfaces`
- [ ] 5.2 Re-run the text-height-sensitive tests as focused single methods. Verify: all pass.
  - `test_browser_shell_surfaces.ShellAcceptanceTest.test_populated_island_stack_fits_its_anchor_at_both_viewports`
  - the command-line tests in `test_browser_shell_command_line`
  - the `test_browser_contextual_hud_stage` method that renders the `┌───┬───┐` grid
  - the remaining `test_vue_typography` methods, after a fresh Storybook build. This covers the stories that set `--f-mono` directly: `ActionDock.stories.js`, `HudDrawer.stories.js`, `MessageWindow.stories.js`.
- [ ] 5.3 Update the docs:
  - `docs/development/frontend-developer-guide.md`: the tree lists `fonts/{iansui,notosans,notoserif,hack}/*.woff2` and `styles/fonts-hack.css`, and the guide explains how to regenerate the fonts with `uv run --script tools/gen_hack_font_slices.py`.
  - `docs/development/frontend-vue-architecture.md`: the self-hosted-font sentence names Hack as the monospace face.

  Verify: `git grep -n -i "hack" docs/development` shows both updates.
- [ ] 5.4 Capture the D8 after-screenshots with agent-browser at both viewports, plus the cold-cache box-grid load, and compare each against its 1.1 baseline. Surfaces:
  - keycaps and the dock legend;
  - the command line with `look north 看看 42`;
  - the help overlay, including the arrow rows;
  - the dialogue choice numbers;
  - the bold party-strip badges;
  - the island map and full-map overlay labels and edge-marker names;
  - the message page box grid (vertical strokes must join) and the `── 稱號冊 ──` heading.

  Verify, and record the findings in the apply summary:
  - no clipping, overlap, or unexplained height jump;
  - CDP reports Hack (custom) for each surface's Latin text;
  - whether the cold-cache swap flash is acceptable. If it is not, apply the D-risk fallback (`font-display: block` on the `box` slice only via the generator), regenerate, and re-verify.

  Run `agent-browser close` afterwards.

## 6. Gates

- [ ] 6.1 Run the full gates. Verify: all green.
  - `CI=true pnpm test`
  - `uv run --locked python -m unittest discover -s tests -t .`
  - `uv run --locked python -m tools.contract_gate manifests contracts`
  - `openspec validate webclient-hack-mono-font --strict`

## 7. Requirement traceability (lands with archive)

`tools.spec_traceability` only knows requirement IDs from `openspec/specs/*/spec.md`. A decorator that
names the new ID before the delta is synced fails CI with `unknown-requirement-id`. So this group runs
when the user asks for archive, in the same commit as the spec sync.

- [ ] 7.1 After `openspec archive` (or `openspec-sync-specs`) has merged the delta into `openspec/specs/webclient-vue-application/spec.md`, confirm the ID with `uv run --locked python -m tools.spec_traceability list`: it must be `webclient-vue-application::the-monospace-type-role-is-a-self-hosted-sliced-hack-face`. Add the ID to `@covers_requirement` on every test in the D9 table:
  - `tests/test_hack_font_slices_contract.py`, on its test method(s);
  - `test_vue_typography.VueTypographyBrowserTest.test_keycaps_and_command_input_keep_monospace`, which gets a new decorator;
  - `test_vue_foundation.VueFoundationBrowserTest.test_vue_bundle_loads_from_origin_offline`, appended to its existing list;
  - `test_browser_local_map_lattice`'s `test_densely_populated_lattice_scales_down_without_reintroducing_overlap` and `test_crowded_edge_overlay_marker_names_stay_separated_and_outside_canvas`.

  Verify: `uv run --locked python -m tools.spec_traceability check` and `uv run --locked python -m tools.contract_gate manifests contracts` pass, and the spec sync and decorators are in one commit.
