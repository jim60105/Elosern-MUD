# Proposal

## Why

The quest drawer stacks a text-heavy quest book above the guild counter, groups every state into one long scroll, and repeats each quest's facts several times. The approved redesign (`docs/superpowers/specs/2026-10-09-quest-drawer-redesign-design.md`; visual reference `docs/design/quest-drawer-redesign/`) replaces it with a two-level icon-tabbed master/detail drawer. This change ships the drawer shell and the complete quest book tab as real, Storybook-documented components wired into the live client.

## What Changes

- New `QuestDrawer.vue` replaces the inline `.quest-drawer` block in `AppClient.vue`. It provides first-level icon tabs (quest book, guild counter) with session tab memory, a disabled counter tab with its reason, and the rail-list-detail grid.
- The quest book tab: a vertical state rail (in progress, completed, failed) with counts and the hot completed badge, `QuestList.vue` (a listbox with per-tab selection memory), and `QuestDetail.vue` (hero, one-based progress, rationale and deadline pair, issuer letter, reward cells, and the action bar mirroring server descriptors).
- New pure `quest-drawer-model.js`: state grouping, counts, the hot flag, the `quest_id` counter merge, the action-bar resolution, and the book-row detail view model.
- The guild counter tab hosts the existing `GuildCounter.vue` unchanged until `quest-drawer-guild-board-tab` replaces it.
- `QuestLog.vue`, its story, and its Vitest file are deleted. The `.elosern-root .quest-log*` rules in `styles/app-shell.css` are removed. Stories `World/QuestDrawer`, `World/QuestList`, and `World/QuestDetail` replace `World/QuestLog` in the manifest.
- **BREAKING** (UI contract): completed and failed rows no longer show a disabled tracking control, and counter actions move from rows to the detail action bar.

## Capabilities

### New Capabilities

- `webclient-quest-drawer`: the tabbed quest drawer, the quest book's state tabs, master/detail selection, the descriptor-mirroring action bar, honest degradation, and the counter tab's scope.

### Modified Capabilities

- `webclient-service-menus`: removes the four quest-drawer requirements that `webclient-quest-drawer` now owns.

## Impact

New `web/webclient-app/components/QuestDrawer.vue`, `QuestList.vue`, `QuestDetail.vue`, and `quest-drawer-model.js`; `AppClient.vue` (and its composable that exposes `questGuildAvailable` / `questServicesPanel`); deleted `QuestLog.vue`, `stories/World/QuestLog.stories.js`, and `tests/world/quest_log.test.js`; `styles/app-shell.css`; `component-manifest.json` and the showcase evidence key sets; Vitest `app_client_drawers.test.js` and `drawer_content_polish.test.js`; browser tests `test_browser_services_quest_drawer.py`, `test_browser_services_guild.py` (book-side journeys), `test_browser_drawer_content.py`, and `test_browser_contextual_hud_drawers.py`.

## Non-goals

No guild board redesign (next change), no payload change, no new action identifiers, and no change to the HudDrawer frame, focus trap, or close behavior.

## Batch:

```text
depends-on: quest-log-structured-rows, quest-drawer-ui-primitives
code-conflicts: quest-drawer-guild-board-tab (QuestDrawer.vue, quest-drawer-model.js, AppClient.vue, manifest), guild-board-structured-offers (test_browser_services_quest_drawer.py: that change bumps one injected services payload and this change rewrites the journeys; the story fixtures are different files)
```

Batch 2, after both dependencies merge. It can run in parallel with `guild-board-structured-offers`. `quest-drawer-guild-board-tab` must wait for this change.

Archive strictly in this order: `quest-log-structured-rows` → `guild-board-structured-offers` → `quest-drawer-book-tab` → `quest-drawer-guild-board-tab`. `quest-drawer-ui-primitives` has no deltas and can archive any time after it merges. Any other order fails `openspec archive`: `quest-drawer-book-tab` REMOVES a requirement that `quest-log-structured-rows` MODIFIES, and `quest-drawer-guild-board-tab` adds to the capability that `quest-drawer-book-tab` creates and REMOVES a requirement that `guild-board-structured-offers` adds.

## Worker profile

**Visual.** Assign a worker with visual ability: one that can read screenshots, use `agent-browser`, and judge pixel parity against the `Design/QuestDrawerRedesign` prototype. The work is most of the drawer's look (list rows, hero, ribbon, stamp, pips, letter, reward cells, action bar) plus live-client visual parity at two viewports (task 5.2).

## Size and standalone delivery

About 8 hours, the largest in the set: model and its unit tests (2h), QuestList and QuestDetail with stories (2.5h), QuestDrawer shell and wiring (1.5h), Vitest and browser test migration (1.5h), and visual parity review (0.5h). It is deployable alone: the drawer is fully usable, and the counter tab shows the current counter.
