# Tasks

## 1. One width token for the column and its neighbours

- [x] 1.1 Add the `--map-column-w` declaration and comment from design D1 to `web/webclient-app/styles/tokens.css`, directly after the `--right-column` line. Verify: `grep -n "map-column-w" web/webclient-app/styles/tokens.css` prints the D1 line.
- [x] 1.2 In `web/webclient-app/components/HudFrame.vue`, rewrite the `.elosern-stage [data-anchor="map"]` rule exactly as design D2 shows (width token, 10px gap, `scrollbar-width: none`; every other declaration unchanged) and change the `presence` rule's `right` to `calc(var(--map-column-w) + 40px * var(--ui-scale))` with its comment updated (design D3). Verify: `grep -n "right-column" web/webclient-app/components/HudFrame.vue` prints only comment lines.
- [x] 1.3 In `web/webclient-app/styles/app-shell.css`: set the `.elosern-root .elosern-stage [data-anchor="map"]` rule's `width: var(--map-column-w);` and `gap: calc(10px * var(--ui-scale));`; drop the `map` arm from the scrollbar rule (keep the vitals arm); delete the `map` gap line inside `@media (max-height: 820px)` and reword that comment (keep the `.place-card` lines); set the `.scene-backdrop__placeholder` `right` to `calc(var(--map-column-w) + 40px * var(--ui-scale))` (design D2, D3). Verify: `grep -n 'data-anchor="map"' web/webclient-app/styles/app-shell.css` shows no `scrollbar` and no `14px`.
- [x] 1.4 Add the D6 source-level test to `web/webclient-app/tests/hud_frame.test.js` and update its presence assertion to the token. Verify: `pnpm vitest run web/webclient-app/tests/hud_frame.test.js` passes.

## 2. Scrollbar-free column with an edge fade

- [x] 2.1 Create `web/webclient-app/composables/use-scroll-edge-fade.js` with `scrollEdges` and `useScrollEdgeFade` exactly as design D5 specifies (scroll listener, ResizeObserver on the element and its children, MutationObserver `childList` re-observation, guards for missing observers, cleanup on unmount). Verify: the file exports exactly those two names.
- [x] 2.2 Create `web/webclient-app/tests/use_scroll_edge_fade.test.js` covering the D6 `scrollEdges` table and the composable's scroll, child-mount re-observation and cleanup paths with a fake `ResizeObserver`. Verify: `pnpm vitest run web/webclient-app/tests/use_scroll_edge_fade.test.js` passes.
- [x] 2.3 Wire the composable into `HudFrame.vue` (import, `mapAnchorRef`, `ref="mapAnchorRef"`, `:data-more-above="mapMoreAbove || null"`, `:data-more-below="mapMoreBelow || null"` on the `map` anchor) and add the D4 CSS block after the `map` rule. Verify: `pnpm vitest run web/webclient-app/tests/hud_frame.test.js` passes, including the jsdom no-attribute assertion.
- [x] 2.4 Run the Node gate `node --test web/static/webclient/js/tests/ui_contract.test.js`. Verify: it passes (both `--map-fade-*` reads carry fallbacks; `--map-column-w` is defined).

## 3. Live-client browser acceptance

- [x] 3.1 Create `web/tests/browser/test_browser_map_column_instruments.py` with `MapColumnInstrumentBrowserTest.test_map_column_holds_its_width_and_fades_hidden_overflow` (decorators, viewports, expected widths and probe-driven overflow steps from design D6), then run `uv run --locked python -m tools.shard_register fix`. Verify: `git diff .github/browser-shards.json` adds exactly that one method id and `uv run --locked python -m tools.contract_gate manifests contracts` passes.
- [x] 3.2 Rebuild the client bundle (`pnpm run build`), then run the new method alone plus the existing fit check: `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_map_column_instruments.MapColumnInstrumentBrowserTest.test_map_column_holds_its_width_and_fades_hidden_overflow web.tests.browser.test_browser_shell_surfaces.ShellAcceptanceTest.test_populated_island_stack_fits_its_anchor_at_both_viewports > <scratchpad>/browser-geometry.log 2>&1`. Verify: both pass.
- [x] 3.3 Run `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_contextual_hud_stage.ContextualHudBrowserTest.test_command_line_never_overlaps_dock_caption_or_hud` (the presence/column neighbour geometry). Verify: it passes.

## 4. Gates and human review material

- [x] 4.1 Run `pnpm test`, `uv run --locked python -m tools.contract_gate --change map-column-instrument-geometry`, `openspec validate map-column-instrument-geometry --strict` and `git diff --check`. Verify: all pass.
- [x] 4.2 Run `pnpm run build-storybook` and `pnpm run showcase-coverage`. Verify: both pass with `web/webclient-app/component-manifest.json` unchanged.
- [ ] 4.3 Capture live-client screenshots with `agent-browser` at 1280x720 (populated column scrolled to top, and scrolled to bottom), 1451x790 and 2560x1440 into the session scratchpad, then `agent-browser close`. Verify: the apply report lists the four absolute paths for the design D7 human review (no automated judgement).
