# Proposal

## Why

A guild board row carries only a name, one objective line, a `reward_summary` string, and a rank, so a player cannot judge an offer before accepting it. The approved quest drawer redesign (`docs/superpowers/specs/2026-10-09-quest-drawer-redesign-design.md`, §4.2) shows each offer with the same detail as an accepted quest: category, objective note, deadline, rationale, flavor, structured reward, and the issuing branch.

## What Changes

- **BREAKING** `services` moves to schema version 6. Board rows drop `reward_summary` and gain `category`, `objective_note`, `deadline_line`, `rationale`, `flavor`, and `reward` (the quest log's reward shape, never null). `objective_summary` loses the species-hunt variant clause, which moves to `objective_note`.
- The `guild` section gains `branch_label`, the issuing branch's display name, and `rank_ladder`, every guild rank key in ascending order, so the client can lay out difficulty tabs without hardcoding authored rank data.
- A new offer-deadline describe seam renders an authored deadline as 接取後 N 日 or 接取後 N 小時.
- The service read model, the Python validator, the JS mirror, the protocol and story fixtures, and the current `GuildCounter.vue` board rendering move to v6 together. The guild `quests` rows, `registration`, and `rank` are unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-service-menus`: services schema version 6; the guild section's `branch_label` and `rank_ladder`; the board row field set and its canonical sources; the counter's board rendering.

## Impact

`world/quests/describe.py`; `world/rules/service_view.py` (`BoardRowView`, `GuildSectionView`, `_build_board`, `_build_guild`) and `world/rules/tests/test_service_view/`; `web/webclient/presentation/services.py` and `tests/test_services_panel/`; `web/static/webclient/js/elosern/protocol/panels/services.js`, `constants.js`, `protocol_services_b.test.js`, and `protocol_fixtures.js`; `tests/test_panel_schema_version_parity_contract.py`; `web/webclient-app/stories/fixtures/services_panels.js`; `web/webclient-app/components/GuildCounter.vue` and `tests/world/guild_counter.test.js`.

## Non-goals

No drawer redesign UI. No change to board eligibility, listing order, acceptance, quest rows, or rank and exam logic. No locked or above-rank offers on the wire: the board still lists only offers at or below the actor's rank. No compatibility shim for v5.

## Batch:

```text
depends-on: quest-log-structured-rows
code-conflicts: quest-log-structured-rows (describe.py, constants.js, protocol fixtures), quest-drawer-ui-primitives (GuildCounter.vue), quest-drawer-guild-board-tab (services story fixtures, GuildCounter.vue, test_browser_services_guild.py), quest-drawer-book-tab (test_browser_services_quest_drawer.py)
```

Start after `quest-log-structured-rows` is merged, because it reuses that change's objective-parts and reward-parts seams and the reward shape. If `quest-drawer-ui-primitives` merges first, rebase onto it: that change moves the rank block out of `GuildCounter.vue`, and this change edits only the board part of that file. It can run in parallel with `quest-drawer-book-tab`.

Archive strictly in this order: `quest-log-structured-rows` → `guild-board-structured-offers` → `quest-drawer-book-tab` → `quest-drawer-guild-board-tab`. `quest-drawer-ui-primitives` has no deltas and can archive any time after it merges. Any other order fails `openspec archive`: `quest-drawer-book-tab` REMOVES a requirement that `quest-log-structured-rows` MODIFIES, and `quest-drawer-guild-board-tab` adds to the capability that `quest-drawer-book-tab` creates and REMOVES a requirement that `guild-board-structured-offers` adds.

## Worker profile

**Logic.** Server presenters, validators, JS protocol mirrors, and contract tests. The interim Vue edit is a field swap with no aesthetic judgment, so any capable worker can take this; visual ability is not needed.

## Size and standalone delivery

About 6 hours: the offer-deadline seam (0.5h), the read model and presenter at v6 (2h), the JS mirror and fixtures (1.5h), the counter board rendering and its Vitest file (1h), and acceptance (1h). It is deployable alone: the live counter keeps working on v6.
