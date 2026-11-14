# Tasks

## 1. The objective line as an instrument panel

- [x] 1.1 In `web/webclient-app/components/ObjectiveTracker.vue`, add the design D1 import, constant and computeds and rewrite the header comment. Verify: the file defines `TICK_LIMIT = 12` and imports `./instrument-panel.css`.
- [x] 1.2 Replace the template with the design D2 template. Verify: `grep -oE 'data-testid="[^"]+"|:data-testid="[^"]+"' web/webclient-app/components/ObjectiveTracker.vue` lists `objective-tracker`, the `__box--`, `__text--`, `__progress--`, `__reward--` bindings, `objective-tracker__more`, `__ticks`, `__tick`, `__stroke` and `__stroke-fill`, and `grep -n "obj__label" web/webclient-app/components/ObjectiveTracker.vue` prints nothing.
- [x] 1.3 Replace the scoped style block with the design D3 block. Verify: `grep -nE "height: calc\(32px|border: var\(--line\)|var\(--shadow\)" web/webclient-app/components/ObjectiveTracker.vue` prints nothing.
- [x] 1.4 Update and add the design D4 tests in `tests/overlays/objective_tracker.test.js` and re-run `tests/overlays/objective_tracker_integration.test.js`, fixing only text expectations the D2 markup changes. Verify: `pnpm vitest run web/webclient-app/tests/overlays` passes.
- [x] 1.5 Run the Node gate `node --test web/static/webclient/js/tests/ui_contract.test.js`. Verify: it passes.

## 2. Stories

- [ ] 2.1 Update the frame and header comment of `web/webclient-app/stories/Overlays/ObjectiveTracker.stories.js` and add the `CountReached` and `LongCount` stories (design D6). Verify: `pnpm run build-storybook` and `pnpm run showcase-coverage` pass with `web/webclient-app/component-manifest.json` unchanged.

## 3. Browser tests

- [ ] 3.1 Update `test_objective_line_shows_only_in_exploration` in `web/tests/browser/test_browser_contextual_hud_stage.py` (design D5). Verify: the test no longer asserts a 34px height, `+1` or `1/3`.
- [ ] 3.2 Add `test_objective_line_is_an_instrument_panel_with_quantity_strokes` to `MapColumnInstrumentBrowserTest` in `web/tests/browser/test_browser_map_column_instruments.py` (design D5), then run `uv run --locked python -m tools.shard_register fix`. Verify: `git diff .github/browser-shards.json` adds exactly that method id.
- [ ] 3.3 Run `pnpm run build`, then `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_map_column_instruments web.tests.browser.test_browser_contextual_hud_stage.ContextualHudBrowserTest.test_objective_line_shows_only_in_exploration web.tests.browser.test_browser_shell_surfaces.ShellAcceptanceTest.test_populated_island_stack_fits_its_anchor_at_both_viewports > <scratchpad>/objective-browser.log 2>&1`. Verify: every method passes (the whole new file covers all four instrument-panel methods of the batch).

## 4. Gates and human review material

- [ ] 4.1 Run `pnpm test`, `uv run --locked python -m tools.contract_gate --change objective-tracker-instrument-panel`, `openspec validate objective-tracker-instrument-panel --strict` and `git diff --check`. Verify: all pass.
- [ ] 4.2 Capture the design D7 live-client screenshots with `agent-browser` into the session scratchpad, then `agent-browser close`. Verify: the apply report lists their absolute paths for the human review (no automated judgement).
