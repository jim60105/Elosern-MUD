# Proposal

## Why

After the compass and the presence rail, the command panel still holds a footer chip row (查看房間, 等待／休息, 建議) inside `SceneOverview`, and the wait and suggestions screens are router frames that replace the panel. Those are low-frequency room actions that belong beside the values they act on. The approved scene overview redesign (`docs/superpowers/specs/2026-10-10-scene-overview-redesign-design.md`, §5 and §10; visual reference `docs/design/scene-overview-redesign/`) puts them on the place card, a centred card, and a 建議 pill, explained by one readout. This is change 3 of 3 and retires the old overview.

## What Changes

- `PlaceCard` gains a 查看房間 icon button beside the location and a 等待 button beside the world time, rendered only in exploration while the exploration panel is available.
- The wait menu and the suggestions list open as centred `ChoiceCard`s (local state, no router frame), including the bounded `RestForm`; the old `exploration.wait` and `exploration.suggestions` router frames and the waiting-screen cards are removed.
- A 建議 pill (top right of the command panel, hidden while suggestions are `unavailable`) opens the suggestions card.
- The shared readout gets its final priority rules: blocked-move flash, then aimed or hovered source (compass, rail entry, place-card button, pill), then the idle summary.
- Remove the footer row and `SceneOverview.vue` with its story and tests, `geometry: "sections"` from the router and `overviewMenu` when nothing else uses it, the `.elosern-root` duplicates for removed and restyled classes in `styles/app-shell.css`, and the exploration root's router items: the exploration root frame resolves to an empty menu.
- Update the controls reference and `component-manifest.json`.
- **BREAKING** (UI contract): the footer chips and the wait / suggestions router frames no longer exist; tests and browser helpers that reach them use the place card and the pill.

## Capabilities

### New Capabilities

- `webclient-room-actions`: the final exploration screen composition, the place-card buttons, the wait card, the 建議 pill, the readout priority, the controls reference, and live-client verification.

### Modified Capabilities

- `webclient-exploration-menu`: "The waiting surface offers exactly three operations" now describes the wait card.
- `webclient-context-actions-suggestions`: "The dock suggestion pane is the single suggestion surface" is renamed "The suggestions card is the single suggestion surface" and describes the card opened from the pill.

## Impact

Edited `PlaceCard.vue`, `AppClient.vue`, `ActionDock.vue`, `composables/use-dock.js`, `composables/*` that hold `waitOpen`/`restFormOpen`, `stores/frame-resolvers.js` (`exploration.root` resolves to an empty menu; `exploration.wait` and `exploration.suggestions` removed), `ExplorationReadout.vue`, `ChoiceCard.vue` (an optional per-row hint), `OptionCard.vue` (envelope helper shared), `lib/controls-reference.js`, `styles/app-shell.css`, `component-manifest.json`, `web/static/webclient/js/elosern/exploration_menu.js` (footer, `waitItems`, `suggestionsMenu` router menus), `web/static/webclient/js/elosern/keyboard_router.js` (`sections` geometry); removed `SceneOverview.vue`, `stories/Action/SceneOverview.stories.js`, `tests/action/scene_overview.test.js`, `tests/app_client_scene_overview.test.js` (replaced), `tests/waiting_surface.test.js` (migrated), and Node router tests for `sections`; browser tests under `web/tests/browser/` that open wait or suggestions or click footer chips.

## Non-goals

No server or protocol change, no new action identifier, no change to the dialogue screen, combat, the skill dock, or the top navigation bar, and no change to the suggestion payload or the wait payload vocabulary.

## Batch:

```text
depends-on: exploration-presence-rail
code-conflicts: exploration-presence-rail (ActionDock.vue, AppClient.vue, SceneOverview.vue, exploration_menu.js, use-dock.js, controls-reference.js, component-manifest.json); exploration-exit-compass (same pane, resolved by ordering)
```

Batch 3, after `exploration-presence-rail` is archived. Archive strictly in order: `exploration-exit-compass` → `exploration-presence-rail` → `exploration-room-actions`. At apply time the worker must add a REMOVED block to this change's `webclient-exploration-menu` delta for the requirement "The exploration dock roots at the compass and the presence rail and keeps the footer overview" (it exists in main only after `exploration-presence-rail` archives; see tasks 1.1), or `openspec archive` leaves a stale footer requirement.

## Worker profile

**Visual.** Assign a worker that can read screenshots and drive `agent-browser`: the place-card buttons, the pill, and the centred cards are judged against `Design/SceneOverviewRedesign` and in the live client at 1451×790 and 1920×1080.

## Size and standalone delivery

About 7 hours: place-card buttons (1h), wait and suggestions cards with local state (2h), pill and readout priority (1h), removals and the empty root (1.5h), test and spec migration (1h), live-client verification (0.5h). The client works fully on its own afterwards, and it is the final shape of the exploration screen.
