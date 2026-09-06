# Tasks: webclient-quest-drawer-split

## 1. QuestLog.vue

- [ ] 1.1 New `web/webclient-app/components/QuestLog.vue` taking the committed `quest_log` panel.
  Render an honest absent marker when the panel is unavailable; render `rows: []` as an explicit
  empty-book message. Invent nothing.
- [ ] 1.2 Rows grouped by state (in progress, completed, failed) in panel order within each group,
  each showing display name, issuer label, settlement indication, objective line, stage and progress,
  deadline line when present, detail, and reward line when the panel carries one — nothing in its
  place when it is `null`.
- [ ] 1.3 Tracking control from the row's own `track` descriptor, present regardless of host.
- [ ] 1.4 Abandon and turn-in rendered only from a `services.guild.quests` row matching by
  `quest_id`, mirroring that descriptor's enabled state, label, and disabled reason. Never synthesize
  or enable one the counter disabled. Keep the existing two-step abandon confirmation.
- [ ] 1.5 Delivery control rendered when the exploration affordances carry an `explore.deliver` entry
  whose recipient is that quest's bound recipient; dispatch the affordance's exact params.
- [ ] 1.6 Stable `data-testid` on the surface, each row, and each control.

## 2. GuildCounter.vue

- [ ] 2.1 New `web/webclient-app/components/GuildCounter.vue` taking the committed `services` panel.
  Render registration, the board rows with their accept controls, and the rank block with the
  examination control — exactly the current `QuestBoard.vue` behavior for those three sections.
- [ ] 2.2 Do NOT render the guild section's `quests` rows; the quest book owns them.
- [ ] 2.3 Render the registry-owned unavailable reason and the absent marker honestly when the
  services panel is unavailable or the guild section is absent.
- [ ] 2.4 Stable `data-testid` on the surface and each control.

## 3. Drawer composition

- [ ] 3.1 `AppClient.vue`: the quest drawer body renders `QuestLog` first and `GuildCounter` below it,
  the counter only when the guild section is available, with an explicit marker otherwise stating the
  counter needs a clerk.
- [ ] 3.2 Keep the drawer's hosted-service-frame behavior intact: the guild frames still route to the
  quest drawer, and the drawer's close teardown is unchanged.
- [ ] 3.3 Delete `web/webclient-app/components/QuestBoard.vue` and its story. Do NOT carry over its
  `世界圖鑑` button — the codex trigger lives in `.cmdutil` after `webclient-lore-codex-drawer`.

## 4. Stories and tests

- [ ] 4.1 New Storybook stories for both components covering: book with no counter, book plus
  counter, empty book, unavailable panel, private-commission row, disabled counter action.
- [ ] 4.2 Component tests for the merge rule: tracking always present; abandon and turn-in only on a
  counter-side match; a disabled counter descriptor renders disabled; a private commission row offers
  tracking only even with a clerk present.
- [ ] 4.3 Browser tests updated for the new testids, including the away-from-clerk case that
  previously showed `尚未取得公會資料`.
- [ ] 4.4 Assert no quest appears twice when both surfaces render.

## 5. Contract registration

- [ ] 5.1 Register every new `data-testid` in
  `docs/development/webclient-vue-frozen-contract-audit.md` §2.3, and remove the retired
  `quest-board__*` identifiers in the same edit.
- [ ] 5.2 Keep `tests/test_webclient_frozen_contract.py` green.

## 6. Sequencing

- [ ] 6.1 This change conflicts with `webclient-lore-codex-drawer` on `AppClient.vue` and the frozen
  contract audit document. Land the codex drawer FIRST, then rebase this change onto it.
