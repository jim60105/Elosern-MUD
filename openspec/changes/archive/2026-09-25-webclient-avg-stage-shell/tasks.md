## 1. Preconditions

- [x] 1.1 Confirm C1 (`webclient-minimap-and-log-quick-fixes`), C2 (`webclient-full-map-fit-view`), and C3 (`webclient-retire-redundant-hud`) are archived, or will be before this change (archive order C1 → C2 → C3 → C4a → C4b → C4c).
  - If C3's text of "Surface visibility is gated by the committed game mode", "The command line is a permanently present bar in the stage's command-line anchor", or `webclient-desktop-shell` "Required desktop surfaces remain visible and usable" changed after this change was written, re-sync this change's blocks to it and keep only this change's edits (design D10).
- [x] 1.2 Confirm these consumers (stop and report if any grep disagrees):
  - `grep -rn -e "--dock-h" -e "--stage-content-bottom" web/webclient-app --include='*.vue' --include='*.css' --include='*.js'` (excluding `dist/`, `node_modules/`) lists only `tokens.css`, `app-shell.css`, `HudFrame.vue`, `AppShell.vue` (comments), `SceneBackdrop.vue`, `ObjectiveTracker.vue`, `LocalMap.vue` (a comment C1 may already have removed), and `stories/Core/HudFrame.stories.js`.
  - `grep -rn "stage-portrait" web/webclient-app --include='*.vue' --include='*.css'` lists only `AppClient.vue` and `app-shell.css`.
  - `grep -rn "anchorHeightBudget\|measureCanvasBudget" web/webclient-app/components` returns nothing (C1 applied).

## 2. Stage frame and tokens

- [x] 2.1 `styles/tokens.css`:
  - add `--band-h: clamp(260px, 27.8vh, 400px)` with a comment naming design §5.1
  - delete `--dock-h`
  - set `--stage-content-bottom: calc(var(--band-h) + var(--command-line-h))` and reword its comment (the edge every surface above the band clears)
- [x] 2.2 `components/HudFrame.vue` (design D1, D3, D4, D7):
  - delete the `feed` and `dock` anchors and their CSS
  - add `div.stage-band` (`data-testid="stage-band"`) holding the `band-message` and `band-command` anchors (testids `anchor-band-message`, `anchor-band-command`; slots of the same names), in a `minmax(0, 2fr) minmax(0, 1fr)` grid of height `var(--band-h)` carrying the draft band chrome
  - add the `actor-left` / `actor-right` anchors (testids `anchor-actor-left`, `anchor-actor-right`; slots of the same names) with the D4 rules
  - give the `command-line` anchor `left: var(--left-column); right: 33.3333%; bottom: var(--band-h)`
  - bound `hud-left` / `hud-right` with `max-height: calc(100% - var(--header-h) - var(--band-h) - 32px)`
  - make the creation rule hide `band-message`, `hud-left`, and `command-line`, and collapse the band grid to one column
  - rewrite the header comment (anchors, layers, band)

  `grep -n 'data-anchor="feed"\|data-anchor="dock"\|dock-h' web/webclient-app/components/HudFrame.vue` returns nothing.
- [x] 2.3 `components/AppShell.vue`:
  - render `NarrativeFeed` in `#band-message` and forward `#action-dock` into `#band-command`
  - add pass-through slots `actor-left` and `actor-right`
  - change `HIDDEN_BY_MODE.creation` to `"[data-anchor='band-message'], [data-anchor='hud-left'], [data-anchor='command-line'], .local-map"`
  - rewrite the header comment and the `.elosern-stage` style comment (no `--dock-h`)
- [x] 2.4 `AppClient.vue`: move `<ReferenceArtwork v-if="store.view.mode !== 'creation'" :portrait="currentPortrait" />` from `#backdrop` into a new `#actor-left` template, and drop `class="stage-portrait"`. `#backdrop` keeps `SceneBackdrop` and, until C4b, `.scene-heading`.

## 3. Styles

- [x] 3.1 `styles/app-shell.css`: delete the rules listed in design D5:
  - `.elosern-root .elosern-stage { --dock-h … }`
  - the three `:has()` blocks and the two `:has()` dock `left` overrides
  - `.elosern-root .elosern-stage [data-anchor="feed"]` and `[data-anchor="dock"]`, with the `(max-width: 1000px)` / `(max-width: 720px)` dock blocks
  - the dialogue feed height rule
  - the combat `--dock-h` pair and the combat `feed` / `dock` / `hud-left` offset rules
  - the creation dock rule
  - the `.stage-portrait` rules (base, `img`, combat, 1000px)

  Repoint:
  - the `.elosern-root .elosern-stage [data-anchor="hud-left"]` / `[data-anchor="hud-right"]` overrides' `max-height` to `calc(100% - var(--header-h) - var(--band-h) - 32px)` (design D8; they outrank `HudFrame.vue`)
  - the placeholder and caption overrides to `.elosern-root .scene-backdrop .scene-backdrop__…` so they outrank `SceneBackdrop.vue`'s base rules (design D8)

  Add:
  - the `[data-anchor="actor-left"]` image mask rule
  - `.elosern-root .scene-backdrop { bottom: var(--band-h) }`
  - the D8 caption offsets from `--command-line-h` (the captions sit inside the backdrop box, which already ends at the band)
  - the actor-left portrait masks and name-plate figcaption (design D4), the message-region card treatment (D6), and the command-line strip chrome (D1)
  - `.waiting-screen { grid-template-columns: minmax(0, 1fr) }` (fold in the 1000px waiting rule)
  - the D5 detail-pane basis inside `[data-anchor="band-command"]`, the one-row exploration tab bar with the hint on its own row, the `band-command` container and the stacked combat tabs below 560px, and the compact interaction target cells

  `grep -n -e "dock-h" -e 'data-anchor="dock"' -e 'data-anchor="feed"' -e "stage-portrait" web/webclient-app/styles/app-shell.css` returns nothing.
- [x] 3.2 `components/SceneBackdrop.vue`: confirm its five caption offsets still read `--stage-content-bottom` (now band plus command row). They apply only standalone, where the backdrop spans the whole stage; in the shell the `app-shell.css` overrides from 3.1 win.

  `components/ObjectiveTracker.vue`: `bottom: calc(var(--band-h) + 12px)`.

  `components/ToastQueue.vue`: bound the stack's `max-height` by `--stage-content-bottom`. `OverlayHost.vue` and `--workspace-bottom`: comment-only (drawers and overlays keep their inset and cover the band while open, design D8).

  `components/ActionDock.vue` and `components/NarrativeFeed.vue`: comment-only updates that name the band regions instead of the dock anchor and the 32vh caption.
- [x] 3.3 `stories/Core/HudFrame.stories.js`: rewrite the description (band, regions, portrait anchors, no `--dock-h`) and render sample content into the new slots.

  Run `pnpm run build-storybook`; green.

## 4. Vitest

- [x] 4.1 `web/webclient-app/tests/hud_frame.test.js`:
  - dialogue-cockpit case: assert `[data-anchor="band-message"]`, `[data-anchor="band-command"]`, `[data-anchor="actor-left"]`, and `[data-anchor="command-line"]` exist
  - creation-CSS assertion: match `[data-anchor="band-message"]`
  - replace the dock-band ownership guard with a band guard: `.elosern-stage .stage-band` carries the gradient, `border-top`, `box-shadow`, and `height: var(--band-h)`; the `band-command` region paints no background; `ActionDock.vue`'s `.action-dock` paints nothing
  - add a case: `HudFrame` source contains no `--dock-h`, and `tokens.css` defines `--band-h: clamp(260px, 27.8vh, 400px)`

  `web/webclient-app/tests/app.test.js`: the anchor list asserts `anchor-band-message`, `anchor-band-command`, `anchor-actor-left`, `anchor-actor-right`, and `anchor-command-line` (not `anchor-feed` / `anchor-dock`). Add an assertion that `actor-left` holds `[data-testid="reference-artwork"]` outside creation mode.

  Run `pnpm exec vitest run web/webclient-app/tests/hud_frame.test.js web/webclient-app/tests/app.test.js web/webclient-app/tests/core`; green.

## 5. Browser tests

- [x] 5.1 Re-point every anchor reference: `grep -rn "anchor-feed\|anchor-dock\|data-anchor=\\\\\"feed\|data-anchor=\\\\\"dock\|data-anchor=\"feed\|data-anchor=\"dock" web/tests/browser`.
  - `test_browser_contextual_hud_anchors.py`, `test_browser_layout.py`, `test_browser_contextual_hud_drawers.py`, and `test_browser_shell_surfaces.py` anchor-id lists become `anchor-hud-left`, `anchor-hud-right`, `anchor-band-message`, `anchor-band-command`, `anchor-command-line`. Portrait anchors are excluded (non-interactive, design D4).
  - `test_browser_layout.py` line ~539 (`[data-anchor="feed"]`) becomes `band-message`.
  - `test_browser_combat_menu.py::test_dock_and_participant_frame_geometry_at_both_desktop_viewports` measures `anchor-band-command`.
  - `test_browser_shell_dock.py::test_action_dock_renders_the_mockup_command_surface` reads the band chrome from `[data-testid="stage-band"]`.
- [x] 5.2 `test_browser_contextual_hud_dock.py::test_action_dock_floating_panel_persists_across_modes`: rename it `test_action_dock_fills_the_band_command_region_across_modes` and re-anchor its annotation to `webclient-contextual-hud::the-action-dock-fills-the-band-s-command-region-at-a-fixed-size`. At 1280x720, 1600x900, and 1920x1080, assert:
  - `stage-band` height equals `clamp(260, 0.278 × vh, 400)` ±1
  - the command region's left edge is `2/3 × viewport width` ±1 and its right edge the viewport's right edge
  - `#action-dock` lies inside the region and paints no background, border, or shadow
  - the band paints the gradient, the 1px top border, and the shadow
  - the region's box is unchanged after opening Interact (a target selected) and Wait
  - the persistence-across-modes half is unchanged

  `test_browser_contextual_hud_stage.py`:
  - re-anchor `test_command_line_never_overlaps_dock_caption_or_hud` to the new ID
  - add 1920x1080 to its viewports
  - add assertions that the command line's bottom equals the band's top ±1 and that it intersects neither `stage-band` nor `anchor-hud-left` / `anchor-hud-right`
  - in `test_narrative_caption_bounded_full_log_one_action`, assert the feed's box equals the `band-message` region's content box and stays equal after appending 40 lines

  Add `test_band_height_is_fixed_across_frames_and_modes` in `test_browser_contextual_hud_stage.py`, annotated `webclient-contextual-hud::the-webclient-renders-a-full-bleed-cinematic-stage-with-anchored-hud-surfaces`. At 1920x1080, walk the exploration root, Interact with a target selected, Wait, an empty pane host, a combat skill target frame (via the `_combat_panel()` injection helper), and a dialogue snapshot with four choices. Assert the band is 300px ±1 and both region boxes are unchanged. Then assert the portrait anchor's bottom equals the band top, its height is `min(0.62 × 1080, 680)` ±1, and its left edge is `0.06 × 1920` ±1. At 1280x720, assert its top is not above the header's bottom.
- [x] 5.3 Run `test_browser_shell_surfaces.py::test_populated_island_stack_fits_its_anchor_at_both_viewports` first. If the populated stack does not fit at 1280x720, apply the design's Risks mitigation (stack gap 8px, compact party cells in `app-shell.css`) and re-run. (It fits; no mitigation was needed.)

  `test_browser_exploration_tiles.py::test_outlet_last_row_never_leaves_blank_space_at_a_narrower_viewport` moves from 400x720 to 1280x720 (design D5), with its docstring reworded. `test_outlet_and_nav_tiles_stay_within_the_pane_at_a_narrow_viewport` is unchanged.

  Run on a local server and get green:
  - `uv run --locked python -m web.tests.browser.unittest_driver web.tests.browser.test_browser_contextual_hud_anchors web.tests.browser.test_browser_layout web.tests.browser.test_browser_contextual_hud_stage web.tests.browser.test_browser_contextual_hud_dock web.tests.browser.test_browser_contextual_hud_drawers web.tests.browser.test_browser_shell_dock web.tests.browser.test_browser_shell_surfaces web.tests.browser.test_browser_combat_menu web.tests.browser.test_browser_combat_scales web.tests.browser.test_browser_exploration_tiles web.tests.browser.test_browser_exploration_nav web.tests.browser.test_browser_exploration_dialogue`
- [x] 5.4 `.github/browser-shards.json`: replace the renamed test label (`test_action_dock_floating_panel_persists_across_modes`) and add `test_band_height_is_fixed_across_frames_and_modes` to the shard holding `test_browser_contextual_hud_stage`.

## 6. Specs and traceability

- [x] 6.1 Sync this change's deltas (`openspec archive` at the end, or `openspec-sync-specs` first to get the new ID).
  - Edit the `webclient-contextual-hud` Purpose paragraph in `openspec/specs/webclient-contextual-hud/spec.md`: "the centred floating dock panel" becomes "the fixed bottom band's command region".
  - Run `uv run --locked python -m tools.spec_traceability list | grep the-action-dock-fills` and use that exact ID in 5.2.
- [x] 6.2 `grep -rn "the-action-dock-renders-as-a-floating-panel" web tests tools --include='*.py' --include='*.js'` returns nothing. Then run `uv run --locked python -m tools.spec_traceability check`; green.

## 7. Validation

- [x] 7.1 Run every gate from the repository root, all green:
  - `node --test web/static/webclient/js/tests/*.test.js`
  - `pnpm test`
  - `pnpm run build`
  - `pnpm run build-storybook`
  - `pnpm run showcase-coverage`
  - `uv run --locked python -m tools.test_data_lint check`
  - `uv run --locked python -m tools.spec_traceability check`
- [x] 7.2 Run `agent-browser` against the running client (the Storybook `Core/AppShell` player stories mount the real `AppClient`; combat is injected through the story's store) at 1920x1080, then 1280x720:
  - The band is fixed at the bottom: the message window on the left two thirds, the dock on the right third.
  - Opening Interact, Wait, and a combat skill frame does not move or resize the band.
  - The player portrait stands on the band's top edge.
  - The command line sits on the message window's top edge.
  - No scene caption intersects the band.

  Close the browser when done.
- [x] 7.3 Run `openspec validate webclient-avg-stage-shell --strict` and `git diff --check`; both clean.
