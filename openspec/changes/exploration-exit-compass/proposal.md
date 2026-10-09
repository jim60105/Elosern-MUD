# Proposal

## Why

The exploration command panel lists exits as wrapping chips whose only spatial cue is an arrow glyph; in the wilderness most chips repeat the same destination name, so a player reads every chip to find the right one. The approved scene overview redesign (`docs/superpowers/specs/2026-10-10-scene-overview-redesign-design.md`, §3 and §10; visual reference `docs/design/scene-overview-redesign/`) replaces the 出口 row with an exit compass that encodes bearing as position. This is change 1 of 3 and is the highest-frequency decision (where to go), so it ships first.

## What Changes

- New pure `components/compass-model.js`: exit resolution into angled or portal targets (map bearing, direction word, portal), portal slot assignment, ±30° snap with its tie rule, pointer and key aim, cycle order, and the continuous-movement step rules with every stop reason.
- New `components/ExitCompass.vue`: the circular pad (pips, aim wedge, portal track, knob, walking rim, shake), hover-aim, click, hold-to-walk, rapid-click queue, and the one-tab-stop keyboard composite.
- A shared readout line in the exploration command panel that explains the compass aim (and, until change 3, shows the idle summary).
- The exploration root pane in `ActionDock.vue` / `AppClient.vue` hosts the compass on the left and the readout on the right; the 人物 / 物件 / footer rows of `SceneOverview.vue` stay temporarily below the readout in the right column, and the 出口 row is removed from `SceneOverview` and from the router's root frame.
- Compass move activation goes through the store's existing submission gate so the `explore.move` payload stays byte-identical.
- The aimed destination lights on the minimap.
- The exploration panel no longer shows the permanent key-hint legend; `lib/controls-reference.js` gains the compass bindings.
- **BREAKING** (UI contract): exit chips (`exploration-row` exit items, `exit-<exit_ref>` keys in the router root) no longer exist; tests and browser helpers that activate an exit chip use the compass.

## Capabilities

### New Capabilities

- `webclient-exit-compass`: exit resolution, portal slots, snap, pointer and keyboard operation, continuous movement, the shared readout feed, honest degradation, controls reference, and live-client verification.

### Modified Capabilities

- `webclient-exploration-menu`: the exploration dock root requirement now roots at the exit compass beside an overview that carries no 出口 row.

## Impact

New `web/webclient-app/components/compass-model.js`, `ExitCompass.vue`, `ExplorationReadout.vue`; edited `ActionDock.vue`, `AppClient.vue`, `composables/use-dock.js`, `SceneOverview.vue` (exit row removed), `components/LocalMap.vue` (aimed-node highlight), `lib/controls-reference.js`, `stores/frame-resolvers.js`, `stores/elosern*.js` (one exit-submission method), `styles/app-shell.css` (grep `.elosern-root` duplicates for restyled dock classes), `component-manifest.json`; `web/static/webclient/js/elosern/exploration_menu.js` (`overviewMenu` drops the exits section, adds an exit-target builder); Vitest `tests/action/*`, `app_client_scene_overview.test.js`, `dialogue_dock.test.js`, `store/*`; Storybook `stories/Action/ExitCompass.stories.js` and fixtures; browser tests under `web/tests/browser/` and `browser_helpers.py` that activate an exit chip.

## Non-goals

No server or protocol change, no new action identifier, no touch or controller input, no minimap click-to-travel, no change to the verb popover, the 人物 / 物件 / footer rows, the place card, or combat.

## Batch:

```text
depends-on: (none)
code-conflicts: exploration-presence-rail (ActionDock.vue, AppClient.vue, SceneOverview.vue, exploration_menu.js, use-dock.js, component-manifest.json); exploration-room-actions (same files, plus keyboard_router.js, controls-reference.js, styles/app-shell.css)
```

Batch 1. Archive strictly in this order: `exploration-exit-compass` → `exploration-presence-rail` → `exploration-room-actions`. The three changes touch the same exploration pane and `webclient-exploration-menu` requirement text, so they must never run in parallel.

## Worker profile

**Visual.** Assign a worker that can read screenshots and drive `agent-browser`: pad geometry, pip and track styling, and the hold-to-walk feel are judged against `Design/SceneOverviewRedesign` in Storybook and in the live client at 1451×790 and 1920×1080.

## Size and standalone delivery

About 8 hours: compass-model and unit tests (2h), ExitCompass with stories (2.5h), readout, pane wiring and store gate (1.5h), router/controls-reference/test migration (1.5h), live-client verification (0.5h). The client works fully on its own afterwards: movement through the compass, everything else through the remaining overview rows.
