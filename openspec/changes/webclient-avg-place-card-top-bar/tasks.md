## 1. Preconditions

- [ ] 1.1 Confirm C4a (`webclient-avg-stage-shell`) is archived, or will be before this change (archive order C1 → C2 → C3 → C4a → C4b → C4c).
  - If C4a's text of the stage requirement, the visibility matrix, or `webclient-desktop-shell` "Required desktop surfaces remain visible and usable" changed after this change was written, re-sync this change's blocks to it and keep only this change's edits (design D7).
  - Also re-sync this change's showcase block if C3's showcase text changed.
- [ ] 1.2 Confirm these consumers (stop and report if any grep disagrees):
  - `grep -rn "onNavigateHome\|@home" web/webclient-app --include='*.vue' --include='*.js'` (excluding `dist/`) lists only `composables/use-dock.js` and `AppClient.vue`.
  - `grep -rn "scene-heading" web/webclient-app web/tests openspec/specs --include='*.vue' --include='*.css' --include='*.js' --include='*.py' --include='*.md'` lists only `AppClient.vue` and `styles/app-shell.css`.
  - `grep -rn "topbar-location\|topbar-clock\|meta-loc\|meta-clock" web --include='*.vue' --include='*.css' --include='*.js' --include='*.py'` (excluding `dist/`) lists only `TopBar.vue`, `app-shell.css`, `tests/top_bar.test.js`, and `web/tests/browser/test_browser_shell_surfaces.py`.

## 2. Top bar

- [ ] 2.1 `styles/tokens.css`: `--header-h: 48px`, and add `--place-h: 68px` with a comment naming design D3.

  `styles/app-shell.css`:
  - drop `--header-h` from the `(max-width: 1350px)` `:root` rule
  - make `.topbar-brand` a single row (design D1): wordmark 20px, tagline 12px serif
  - delete the `.topbar-meta .meta-clock` / `.meta-loc` rules in the base, 1350px, and 1000px blocks

  `stories/Core/DesktopNavigation.stories.js`: the template's `--header-h` becomes `48px`.
- [ ] 2.2 `components/TopBar.vue`:
  - delete the `locationLabel` / `timeLabel` props, the `meta-loc` and `meta-clock` spans, and both `sep` spans
  - change the tagline text to `伊洛瑟恩`
  - rewrite the header comment (48px band; the meta pill carries the connection state only)

  `stories/Core/TopBar.stories.js`: drop the location / time args and comments; keep the `Connected`, `Disconnected`, and `PossessionBannerActive` story IDs.
- [ ] 2.3 `components/DesktopNavigation.vue`:
  - delete the home button and the `home` emit
  - switch the buttons to the row layout of design D1

  `composables/use-dock.js`: delete `onNavigateHome` and its return entry.

  `AppClient.vue`: drop `onNavigateHome` from the destructure and `@home` from `<DesktopNavigation>`.

  `grep -rn "onNavigateHome\|'home'\|\"home\"" web/webclient-app --include='*.vue' --include='*.js'` (excluding `dist/`) returns nothing that belongs to navigation.

## 3. Place card and anchor

- [ ] 3.1 Add `web/webclient-app/components/PlaceCard.vue` per design D3:
  - props `locationLabel`, `timeLabel`
  - testids `place-card`, `place-card__location`, `place-card__time`
  - placeholders `位置：--` / `時間：--`
  - `h1` heading with `title` carrying the full label, ellipsis truncation, island chrome from tokens
  - no focusable element

  Add `stories/Core/PlaceCard.stories.js` with deterministic args: `Default` (`測試起點`, `春季 3 日 · 12:00`), `WildernessRegion` (`西部丘陵與谷地`), `Placeholders` (both null), `LongLabel`.

  Add `"Core/PlaceCard"` to `component-manifest.json` (keep `"frozen": true`).
- [ ] 3.2 `components/HudFrame.vue`:
  - add the `place` anchor (`data-anchor="place"`, `data-testid="anchor-place"`, slot `place`) with the design D4 geometry, hidden in creation
  - move `hud-left`'s `top` and `max-height` per D4
  - update the header comment

  `components/AppShell.vue`:
  - import `PlaceCard` and render it in `#place` with `:location-label` / `:time-label`
  - stop passing both to `TopBar`
  - add `[data-anchor='place']` to `HIDDEN_BY_MODE.creation`
- [ ] 3.3 `AppClient.vue`: delete the `.scene-heading` block from `#backdrop`.

  `styles/app-shell.css`: delete every `.scene-heading` rule (base, `__eyebrow`, `h1`, `p`, the two combat rules, and the 1350px and 1000px overrides).

  `grep -rn "scene-heading" web/webclient-app --include='*.vue' --include='*.css'` returns nothing.
- [ ] 3.4 `stories/Core/HudFrame.stories.js`: render sample place-card content in the new slot.

  Update the manifest snapshots to include `Core/PlaceCard`, and fix any comment that states a manifest count:
  - `web/webclient-app/tests/overlays/deferred_surfaces_absent.test.js`
  - `web/webclient/tests/test_vue_showcase_action_evidence.py`
  - `test_vue_showcase_data_evidence.py`
  - `test_vue_showcase_world_evidence.py`
  - `test_vue_showcase_overlays_evidence.py`

  Run `pnpm run build-storybook` and `pnpm run showcase-coverage`; green.

## 4. Vitest

- [ ] 4.1 Add `web/webclient-app/tests/place_card.test.js`:
  - both labels render
  - both placeholders render for null props
  - a long label keeps the full text in the heading's text and `title` and the root has no focusable descendant
  - mounted inside `AppShell` in `creation` mode, `[data-anchor="place"]` carries the creation-hidden rule, and in exploration the card states the `statusSlice` labels passed to `AppShell`
- [ ] 4.2 `tests/top_bar.test.js`:
  - the first case asserts the meta pill states only `● 已連線` and no `topbar-location` / `topbar-clock` exists
  - delete the placeholder case, which moves to 4.1
  - assert `[data-testid="topbar-title"]` text contains `伊洛瑟恩`
  - keep the switcher, maximum-length-name, and possession cases
- [ ] 4.3 Add `tests/desktop_navigation.test.js`: in exploration and combat modes, no button's text is `探索` or `戰鬥`; the component declares no `home` emit; activating 任務 emits `navigate` with `quests`; the map button is absent in combat.

  `tests/app.test.js`: the anchor list includes `anchor-place`, and `[data-testid="place-card"]` renders inside it.

  Run `pnpm exec vitest run web/webclient-app/tests/place_card.test.js web/webclient-app/tests/top_bar.test.js web/webclient-app/tests/desktop_navigation.test.js web/webclient-app/tests/app.test.js web/webclient-app/tests/overlays/deferred_surfaces_absent.test.js web/webclient-app/tests/preserved_contract.test.js web/webclient-app/tests/app_client_drawers.test.js web/webclient-app/tests/app_client_frameless_bag.test.js`; green.
- [ ] 4.4 `web/webclient/tests/test_node_suite_evidence.py`: add `test_place_card_node_suite_passes` running `web/webclient-app/tests/place_card.test.js`, in the same shape as `test_party_strip_node_suite_passes`, annotated `webclient-contextual-hud::the-place-card-names-the-current-location-and-the-world-time` (confirm the ID with `uv run --locked python -m tools.spec_traceability list` after 6.1).

## 5. Browser tests

- [ ] 5.1 `web/tests/browser/test_browser_shell_surfaces.py::test_header_shows_location_time_and_connection_dot`:
  - read the location from `[data-testid="place-card__location"]` and the clock from `[data-testid="place-card__time"]`
  - assert `[data-testid="topbar"]` contains neither string
  - keep the wilderness-region half against the place card
  - add the place-card ID to its `covers_requirement` list

  Add `anchor-place` to the anchor-id lists in:
  - `test_browser_shell_surfaces.py::test_stage_anchors_do_not_intersect_at_both_viewports`
  - `test_browser_contextual_hud_anchors.py`
  - `test_browser_layout.py`
  - `test_browser_contextual_hud_drawers.py`
- [ ] 5.2 Add `test_stage_box_is_at_least_65_percent_at_the_reference_viewport` to `test_browser_contextual_hud_stage.py`, annotated `webclient-contextual-hud::the-webclient-renders-a-full-bleed-cinematic-stage-with-anchored-hud-surfaces`. At 1920x1080 in exploration, assert:
  - the header strip's height is 48 ±1
  - `stage-band`'s height is 300 ±1
  - the stage box (the band's top minus 48) is ≥ 702
  - no element inside `.topbar-right`, `.topbar-brand`, or `.desktop-navigation` contains the committed location label
  - `.desktop-navigation` has no button with text `探索`

  Run `test_browser_shell_surfaces.py::test_populated_island_stack_fits_its_anchor_at_both_viewports` and apply the design's Risks fallback if 1280x720 fails.

  Run on a local server and get green:
  - `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_shell_surfaces web.tests.browser.test_browser_contextual_hud_stage web.tests.browser.test_browser_contextual_hud_anchors web.tests.browser.test_browser_layout web.tests.browser.test_browser_contextual_hud_drawers web.tests.browser.test_browser_exploration_nav web.tests.browser.test_browser_exploration_state web.tests.browser.test_browser_inventory_grid web.tests.browser.test_vue_foundation`
- [ ] 5.3 `.github/browser-shards.json`: add `test_stage_box_is_at_least_65_percent_at_the_reference_viewport` to the shard that holds `test_browser_contextual_hud_stage`.

## 6. Specs and traceability

- [ ] 6.1 Sync this change's deltas (`openspec archive` at the end, or `openspec-sync-specs` first), then run `uv run --locked python -m tools.spec_traceability list | grep the-place-card` and use that exact ID in 4.4 and 5.1.
- [ ] 6.2 Run `uv run --locked python -m tools.spec_traceability check`; green.

## 7. Validation

- [ ] 7.1 Run every gate from the repository root, all green:
  - `node --test web/static/webclient/js/tests/*.test.js`
  - `pnpm test`
  - `pnpm run build`
  - `pnpm run build-storybook`
  - `pnpm run showcase-coverage`
  - `uv run --locked python -m tools.test_data_lint check`
  - `uv run --locked python -m tools.spec_traceability check`
  - `uv run --locked evennia test --settings test_settings.py --keepdb web.webclient.tests.test_vue_showcase_action_evidence web.webclient.tests.test_vue_showcase_data_evidence web.webclient.tests.test_vue_showcase_world_evidence web.webclient.tests.test_vue_showcase_overlays_evidence web.webclient.tests.test_node_suite_evidence`
- [ ] 7.2 Run `agent-browser` against the running client at 1920x1080:
  - The top bar is 48px with no 探索 entry, no location, and no time.
  - The character switcher shows the full name.
  - The place card at the top-left shows the location and time and changes after a move.
  - No `.scene-heading` text floats over the scene.

  Close the browser when done.
- [ ] 7.3 Run `openspec validate webclient-avg-place-card-top-bar --strict` and `git diff --check`; both clean.
