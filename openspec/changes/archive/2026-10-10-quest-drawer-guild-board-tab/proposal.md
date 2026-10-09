# Proposal

## Why

After `quest-drawer-book-tab`, the guild counter tab still hosts the old stacked `GuildCounter.vue`: a flat board list with one-line offers. The approved redesign (`docs/superpowers/specs/2026-10-09-quest-drawer-redesign-design.md` §3.3–§3.8; visual reference `docs/design/quest-drawer-redesign/`, story `GuildBoard`) organizes the board by difficulty grade and shows each offer in the same master/detail layout as a held quest, so a player can judge an offer before accepting it.

## What Changes

- The guild counter tab gains a vertical grade rail built from the guild section's `rank_ladder`, with one gem tab per grade, counts, own-grade mark, dimmed empty grades, and locked grades above the holder's rank. The default grade is the highest at or below the holder's rank that has offers.
- `GuildRankCard` sits at the top of the board list column. Board offers render in `QuestList`, and the selected offer renders in `QuestDetail` with the acceptance condition, deadline, branch label, flavor, reward, and the `accept` descriptor as the primary action.
- Unregistered holders see a registration card instead of the rail and board.
- `quest-drawer-model.js` gains the board functions: grouping by grade, the default grade, the lock rule from the ladder and holder rank, the offer detail view model, and offer actions.
- `GuildCounter.vue`, its stories, and its Vitest file are deleted. The `.elosern-root .guild-counter*` skin rules in `styles/app-shell.css` are removed. `GuildRankCard` keeps its class names but no longer depends on those rules. `World/GuildCounter` leaves the manifest, and the QuestDrawer, QuestList, and QuestDetail stories gain board variants.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-quest-drawer`: adds the grade-tabbed board, the rank card placement, offer detail and acceptance, and the unregistered registration card, and narrows "The guild counter tab presents counter business only" so registration shows only to an unregistered holder.
- `webclient-service-menus`: removes "The guild counter renders the structured board offer", which `guild-board-structured-offers` adds for the legacy component this change deletes.

## Impact

`web/webclient-app/components/QuestDrawer.vue` and `quest-drawer-model.js`; deleted `GuildCounter.vue`, `stories/World/GuildCounter.stories.js`, and `tests/world/guild_counter.test.js`; `styles/app-shell.css`; QuestDrawer, QuestList, and QuestDetail stories and tests; `component-manifest.json` and the showcase evidence key sets; `web/webclient/tests/test_vue_hud_drawer_evidence.py`; browser tests `test_browser_services_guild.py` (counter journeys), `test_browser_pointer.py` (register), and `test_browser_services_quest_drawer.py`; `web/tests/browser/seed/services_fixture.py` if a multi-grade board seed is needed.

## Non-goals

No payload change: everything needed ships in `guild-board-structured-offers`. No change to board eligibility, acceptance rules, the rank card's design, or examination behavior. No board category filter.

## Batch:

```text
depends-on: guild-board-structured-offers, quest-drawer-ui-primitives, quest-drawer-book-tab
code-conflicts: quest-drawer-book-tab (QuestDrawer.vue, quest-drawer-model.js, stories, manifest, showcase evidence key sets, test_node_suite_evidence.py), guild-board-structured-offers (test_browser_services_guild.py, services browser seed)
```

Batch 3, the last change in the set. Start only after all three dependencies merge.

Archive strictly in this order: `quest-log-structured-rows` → `guild-board-structured-offers` → `quest-drawer-book-tab` → `quest-drawer-guild-board-tab`. `quest-drawer-ui-primitives` has no deltas and can archive any time after it merges. Any other order fails `openspec archive`: `quest-drawer-book-tab` REMOVES a requirement that `quest-log-structured-rows` MODIFIES, and `quest-drawer-guild-board-tab` adds to the capability that `quest-drawer-book-tab` creates and REMOVES a requirement that `guild-board-structured-offers` adds.

## Worker profile

**Visual.** Assign a worker with visual ability: one that can read screenshots, use `agent-browser`, and judge pixel parity against the `Design/QuestDrawerRedesign` prototype. The work is the grade rail, rank card placement, offer detail, and registration card, plus live-client visual parity (task 4.2).

## Size and standalone delivery

About 7 hours: model board functions and tests (1.5h), the counter tab composition and registration card (2h), the GuildCounter removal and story and test migration (1.5h), browser journeys (1.5h), and visual parity review (0.5h). After it lands, the redesign is complete.
