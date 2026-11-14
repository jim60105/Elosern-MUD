# Tasks

## 1. The minimap inside its own instrument panel

- [x] 1.1 In `web/webclient-app/components/LocalMap.vue`, wrap the `<aside>` in the `instrument-panel local-map-panel` div, delete the orientation span, the `showsOrientation` computed and their comments, import `./instrument-panel.css`, and update the header comments (design D1). Verify: `grep -nE "orientation|北↑|showsOrientation" web/webclient-app/components/LocalMap.vue` prints nothing.
- [x] 1.2 Apply the design D2 style edits to `LocalMap.vue` (new `.local-map-panel` rule; card declarations, `.local-map:hover` and `.local-map__orientation` removed; square affordance; text shadows; footer padding; glyph opacity and hover rule). Verify: `grep -nE "border: var\(--line\)|var\(--shadow\)|padding: var\(--sp-1\)" web/webclient-app/components/LocalMap.vue` prints nothing.
- [x] 1.3 Delete the two `.elosern-root .local-map` lines from `web/webclient-app/styles/app-shell.css` (design D3). Verify: `grep -n "local-map" web/webclient-app/styles/app-shell.css` prints nothing.
- [x] 1.4 Add the two new design D4 tests and delete/rewrite the listed existing ones (root-class test, both legend tests, the ~435 header assertion, the ~591 font-size loop entry, the legend comments) in `tests/world/local_map.test.js`, then update `tests/world/map_layout_variants.test.js` and `tests/overlays/objective_tracker_integration.test.js`. Verify: `grep -n "local-map__orientation" web/webclient-app/tests/world/local_map.test.js` shows only absence assertions (`toBe(false)` or the new no-legend test), and `pnpm vitest run web/webclient-app/tests/world web/webclient-app/tests/overlays/objective_tracker_integration.test.js web/webclient-app/tests/hud_frame.test.js` passes.
- [x] 1.5 Run the Node gate `node --test web/static/webclient/js/tests/ui_contract.test.js`. Verify: it passes.

## 2. Stories

- [ ] 2.1 Update `web/webclient-app/stories/World/LocalMap.stories.js` frames and comments and the legend comments in `web/webclient-app/stories/fixtures/local_map.js` (design D6). Verify: `grep -n "orientation legend" web/webclient-app/stories/World/LocalMap.stories.js web/webclient-app/stories/fixtures/local_map.js` prints nothing, and `pnpm run build-storybook` and `pnpm run showcase-coverage` pass with `web/webclient-app/component-manifest.json` unchanged.

## 3. Browser tests

- [ ] 3.1 Update the orientation probes in `test_browser_contextual_hud_stage.py`, `test_browser_local_map_layout_variants.py`, `test_browser_map_legibility.py` and the comments in `test_browser_local_map_geometry.py` (design D5). Verify: `grep -n "local-map__orientation" web/tests/browser/*.py` shows only count-of-zero assertions and the `legend` key in `_surface`.
- [ ] 3.2 Add `test_minimap_is_a_card_free_instrument_panel` to `MapColumnInstrumentBrowserTest` in `web/tests/browser/test_browser_map_column_instruments.py` (design D5), then run `uv run --locked python -m tools.shard_register fix`. Verify: `git diff .github/browser-shards.json` adds exactly that method id.
- [ ] 3.3 Run `pnpm run build`, then in two short commands with output captured to the scratchpad: `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_map_column_instruments.MapColumnInstrumentBrowserTest.test_minimap_is_a_card_free_instrument_panel web.tests.browser.test_browser_contextual_hud_stage.ContextualHudBrowserTest.test_minimap_island_single_affordance_keyboard_and_movement` and `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_local_map_layout_variants web.tests.browser.test_browser_map_legibility`. Verify: all pass.
- [ ] 3.4 Run `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_local_map_geometry.LocalMapBrowserTest web.tests.browser.test_browser_shell_surfaces.ShellAcceptanceTest.test_populated_island_stack_fits_its_anchor_at_both_viewports`. Verify: all pass (canvas size, island box stability and the column fit hold).

## 4. Gates and human review material

- [ ] 4.1 Run `pnpm test`, `uv run --locked python -m tools.contract_gate --change local-map-instrument-panel`, `openspec validate local-map-instrument-panel --strict` and `git diff --check`. Verify: all pass.
- [ ] 4.2 Capture the design D7 live-client screenshots with `agent-browser` into the session scratchpad, then `agent-browser close`. Verify: the apply report lists their absolute paths for the human review (no automated judgement).
