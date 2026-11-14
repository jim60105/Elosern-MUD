# Tasks

## 1. Shared instrument-panel chrome

- [x] 1.1 Create `web/webclient-app/components/instrument-panel.css` with exactly the design D1 content. Verify: `node --test web/static/webclient/js/tests/ui_contract.test.js` passes (every read without a fallback is a defined token).

## 2. The place card as an instrument panel

- [x] 2.1 In `web/webclient-app/components/PlaceCard.vue`, import the stylesheet, add `instrument-panel` to the root's static class and rewrite the header comment (design D2). Verify: `git diff` of the template touches only the root `class` attribute.
- [x] 2.2 Replace the `<style>` block of `PlaceCard.vue` with the design D3 block. Verify: `grep -nE "border: var|border-radius: var\(--radius\)|var\(--shadow\)|-1 \* var\(--motion-shift-lg" web/webclient-app/components/PlaceCard.vue` prints nothing.
- [x] 2.3 Delete the `.place-card` and `.place-card__time` rules and their comment sentence from the `@media (max-height: 820px)` block of `web/webclient-app/styles/app-shell.css` (design D4). Verify: `grep -n "place-card" web/webclient-app/styles/app-shell.css` prints nothing.
- [x] 2.4 Add the three design D5 tests to `web/webclient-app/tests/place_card.test.js`. Verify: `pnpm vitest run web/webclient-app/tests/place_card.test.js web/webclient-app/tests/app_client_room_actions.test.js web/webclient-app/tests/preserved_contract.test.js` passes.

## 3. Stories

- [ ] 3.1 Update the frame and header comment of `web/webclient-app/stories/Core/PlaceCard.stories.js` (design D6), keeping every export and arg. Verify: `pnpm run build-storybook` and `pnpm run showcase-coverage` pass with `web/webclient-app/component-manifest.json` unchanged.

## 4. Live-client browser acceptance

- [ ] 4.1 Add the `tx > 0` heading-direction assertion to `test_full_motion_place_card_and_clear` in `web/tests/browser/test_browser_scene_transitions.py` (design D5). Verify: the diff adds `tx` to `_HEADING_PAIR` and one assertion.
- [ ] 4.2 Add `test_place_card_is_an_instrument_panel` to `MapColumnInstrumentBrowserTest` in `web/tests/browser/test_browser_map_column_instruments.py` (design D5), then run `uv run --locked python -m tools.shard_register fix`. Verify: `git diff .github/browser-shards.json` adds exactly that method id.
- [ ] 4.3 Run `pnpm run build`, then `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_map_column_instruments.MapColumnInstrumentBrowserTest.test_place_card_is_an_instrument_panel web.tests.browser.test_browser_scene_transitions.SceneTransitionsBrowserTest.test_full_motion_place_card_and_clear web.tests.browser.test_browser_chrome_navigation.ChromeNavigationBrowserTest.test_place_card_sets_heading_rule_and_tabular_time > <scratchpad>/place-card-browser.log 2>&1`. Verify: all three pass.
- [ ] 4.4 Reword the stale compaction comment in `test_browser_proportional_ui_scale.py` (design D5), then run `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_shell_surfaces.ShellAcceptanceTest.test_populated_island_stack_fits_its_anchor_at_both_viewports web.tests.browser.test_browser_map_column_instruments.MapColumnInstrumentBrowserTest.test_map_column_holds_its_width_and_fades_hidden_overflow web.tests.browser.test_browser_proportional_ui_scale.ProportionalUiScaleBrowserTest.test_large_desktop_renders_the_reference_at_the_chrome_cap`. Verify: all pass (the panel still fits the column at 1451x790 and 2560x1440; the place-card ratio holds without compaction).

## 5. Gates and human review material

- [ ] 5.1 Run `pnpm test`, `uv run --locked python -m tools.contract_gate --change place-card-instrument-panel`, `openspec validate place-card-instrument-panel --strict` and `git diff --check`. Verify: all pass.
- [ ] 5.2 Capture the design D7 live-client screenshots with `agent-browser` into the session scratchpad, then `agent-browser close`. Verify: the apply report lists their absolute paths for the human review (no automated judgement).
