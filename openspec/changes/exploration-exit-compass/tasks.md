# Tasks

## 1. Compass model

- [ ] 1.1 Create `web/webclient-app/components/compass-model.js` per design D1, using `docs/design/scene-overview-redesign/compass-model.js` as the reference for §3.1 and §3.5 (the spec wins on any disagreement). Extract or share the `LocalMap.remoteDirection` bearing formula so both use one helper. Add `tests/action/compass_model.test.js` covering: each of the three angle sources including a cross-layer exit and same-coordinate stairs; the ±30° snap and its clockwise tie rule; the dead zone and the ring zone; portal slots (pinned up and down, even spread, nearest free slot with clockwise ties, the 24-slot switch above ten); the cycle order; `aimFromKeys` for all eight directions and for cancelling keys; every `nextStep` stop reason (dead end, disabled with server reason, none); and bearing equality with the minimap over a coordinate grid. Verify with `pnpm test -- tests/action/compass_model.test.js`.

## 2. ExitCompass component

- [ ] 2.1 Implement `components/ExitCompass.vue`: pad, cardinal ticks, dead-zone ring, current-position dot, angled pips (hollow dashed when disabled), aim wedge, portal track and beads, knob lean (48%, 62%, 30% unlit), walking rim, horizontal 260 ms shake, `role="application"` with `aria-label="出口羅盤"`, hover aim, click, rapid-click queue of one, hold-to-walk with steering, keyboard aim, `[`/`]` cycle, Enter/Space (repeat ignored), hold-to-walk by key, blur and pointer-leave stop, the `off` motion level (no animation, static flash signal). It emits `aim`, `blocked`, and `move(item)`; it sends nothing itself. Add `tests/action/exit_compass.test.js`: click, no-target click, disabled click, hold, rapid-click queue, keyboard aim and cycle, key-repeat ignore, blur stopping a walk, commit-driven stepping with a mocked arrival, and each stop reason. Verify with `pnpm test -- tests/action/exit_compass.test.js`.
- [ ] 2.2 Add `stories/Action/ExitCompass.stories.js` with the stories Wilderness8Way, GridIrregular, InteriorPortals, Stairs, DisabledExit, TenPortals, and an interactive Walking story, each bound to real reducer-derived fixtures (extend `stories/fixtures/scene_overview.js` and `local_map.js` rather than hand-built shapes). Register them in `component-manifest.json`. Verify with `node scripts/component-coverage.mjs`.

## 3. Pane wiring

- [ ] 3.1 In `web/static/webclient/js/elosern/exploration_menu.js`, drop the exits section from `overviewMenu` and add a builder exposing the `moveItems` rows to the compass; read `stores/elosern*.js` to find the submission gate behind `focusConfirm`, factor it, and add one store method that activates an exit row through that gate with the row re-resolved at activation time. Add store tests under `tests/store/` proving: the payload is byte-identical to the one the old exit chip produced, a disabled exit submits nothing, and in-flight or awaiting-revision input is suppressed. Update tests that assert `exit-<exit_ref>` router keys.
- [ ] 3.2 Add `components/ExplorationReadout.vue` and a pure priority helper (flash, aim, idle `出口 N · 在場 M`) with `tests/action/exploration_readout.test.js` (live region, tones, lead and text, flash timing about 1.6 s, `off` motion level).
- [ ] 3.3 Remove the 出口 row from `SceneOverview.vue` (and its exit-only glyph and label code if unused), and compose the exploration root pane in `ActionDock.vue` / `AppClient.vue`: compass on the left filling the panel height, readout then `SceneOverview` in the right column, panel box unchanged. Focus the compass on entering exploration. Update `tests/app_client_scene_overview.test.js`, `tests/action/scene_overview.test.js`, `tests/action/action_dock.test.js`, and `tests/dialogue_dock.test.js` for the new composition. Verify with `pnpm test`.
- [ ] 3.4 Add an optional `aimedNode` highlight to `LocalMap.vue`, fed from the compass aim in `AppClient.vue`, with a test that the highlight appears and clears.
- [ ] 3.5 Grep `styles/app-shell.css` for `.elosern-root` duplicates of every restyled `.action-dock*` and `.scene-overview*` class and update or remove them; add no new duplicate. Verify with `grep -n "elosern-root" web/webclient-app/styles/app-shell.css` and the live client in 7.2.

## 4. Controls reference and legend

- [ ] 4.1 Add compass entries to `lib/controls-reference.js` (arrow aim, `[`/`]` cycle, Enter/Space move, hold to walk, Escape) and update its test. Hide `action-dock__legend` in exploration only (dialogue and combat keep theirs) and update the `action-dock-description` expectations in `tests/action/action_dock.test.js`, `tests/dialogue_dock.test.js`, and `tests/app_client_scene_overview.test.js`. Verify with `pnpm test`.

## 5. Test migration

- [ ] 5.1 Update the browser tests and helpers under `web/tests/browser/` that activate an exit chip (`browser_helpers.py` "activate the scene overview's first exit chip", `test_browser_exploration_nav.py`, `test_browser_exploration_frame.py`, `test_browser_exploration_tiles.py`, `test_browser_exploration_state.py`, `test_browser_exploration_dialogue.py`, `test_browser_pointer.py`, `test_browser_local_map_interaction.py`, `test_browser_contextual_hud_dock.py`, plus any other hit of `grep -l "exit-" web/tests/browser`) to move through the compass (keyboard aim and Enter, or a click at the pip). Register any new or renamed method in `.github/browser-shards.json`, and run each touched class with the browser unittest driver documented in the repository AGENTS.md.
- [ ] 5.2 Add a browser journey that holds a direction in a wilderness room, observes at least two arrivals and a stop with the dead-end readout, and a journey where a disabled exit's reason is read from the readout.

## 6. Specs and docs

- [ ] 6.1 In `docs/development/webclient-vue-frozen-contract-audit.md`, restate the exploration dock family (compass plus overview rows) and add a change note.
- [ ] 6.2 Author the remaining MODIFIED deltas for requirements outside `webclient-exploration-menu` that name the exit chips, the all-mode shortcut legend, or the 出口 row: in `webclient-desktop-shell` the requirements "Required desktop surfaces remain visible and usable", "Keyboard routing is menu-first and submission-safe", and "The action dock's row region and detail panes are direct children of its pane host", and in `webclient-pointer-activation` "Every action-dock surface renders exactly the keyboard router's current menu frame" and "Pointer activation traverses the identical path as keyboard confirmation". Copy each full block from `openspec/specs/`, edit only the exit-chip, root-composition, and legend scenarios, and keep every scenario name. Verify with `openspec validate exploration-exit-compass --strict`.

## 7. Integration acceptance

- [ ] 7.1 Run `pnpm test`, `node scripts/component-coverage.mjs`, the touched browser classes, the contract gate (`tools.contract_gate`), the frozen-contract test (`tests.test_webclient_frozen_contract`), and `openspec validate exploration-exit-compass --strict`.
- [ ] 7.2 Build the client (`pnpm run build`) and with `agent-browser` capture the live exploration screen at 1451×790 and 1920×1080 for a wilderness room, a town grid room, an interior room with portals, a room with a disabled exit, and a room with no exits; hover, click, and hold-to-walk in the wilderness; confirm the pad fits the band, the panel does not scroll beyond the right column, and compare with `Design/SceneOverviewRedesign` in Storybook. Fix deviations or record intentional ones in this change's design.md.

## Workflow follow-up

- At archive sync, annotate the Python and Vitest evidence carriers with the new `webclient-exit-compass` requirement IDs and re-point annotations of the modified requirements; run `tools.spec_traceability check`.
- Do not apply, archive, or merge until the user asks. `exploration-presence-rail` must wait for this change to archive.
