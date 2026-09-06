# Proposal: webclient-quest-drawer-split

## Why

`QuestBoard.vue` is a 496-line component reading one data source and titled `公會任務板`. After
`webclient-quest-log-panel` there are two sources with different availability rules: the player's own
quest book, readable anywhere, and the guild counter, which exists only in front of a clerk. Keeping
them in one component means one file that is half host-gated and half not, and a player away from a
clerk still sees `尚未取得公會資料` where their quests should be.

The component boundary should be the data boundary.

## What Changes

- New `QuestLog.vue` reading the `quest_log` panel: every accepted quest, always present, grouped by
  state with the issuer labelled on each row. Per-row actions:
  - **Track / untrack** — always available, from the panel's own descriptor.
  - **Abandon / turn in** — rendered only when `services.guild.quests` carries a row with the same
    `quest_id` and that action is enabled. Matching by `quest_id` is the single merge point between
    the two panels.
- New `GuildCounter.vue` reading `services.guild`: registration, the quest board (accepting new
  quests), and guild rank with the promotion examination. It does **not** re-list accepted quests, so
  nothing is shown twice.
- The quest drawer hosts both: the quest book first, the counter below it and only when the guild
  section is available, carrying an explicit marker that the counter needs a clerk.
- `QuestBoard.vue` is deleted. Its `世界圖鑑` button is NOT carried over — the codex trigger moves to
  `.cmdutil` in `webclient-lore-codex-drawer`.
- The store's service-surface routing keeps opening the quest drawer for the guild frames; the drawer
  now also opens with content when no guild frame exists.
- New test identifiers registered in the frozen contract audit §2.3.
- **Amended 2026-09-06 (consistency review).** The earlier per-row **Deliver** bullet is removed. The
  parent design (§9.1) lists per-row actions as track/abandon/turn-in only, and the `quest_log` v1
  row carries no delivery binding while an `explore.deliver` affordance carries only
  `{npc_id, item_key}` with no quest reference — a per-row delivery control would have to fabricate
  the join. The delivery affordance is dispatched from the exploration interact surface (landed with
  `quest-deliver-action`); the delta spec never carried a delivery requirement.

## Capabilities

### New Capabilities

(None.)

### Modified Capabilities

- `webclient-service-menus`: the quest drawer's composition changes — the quest log is no longer part
  of the guild service surface, the counter surface loses its quest-record list, and the drawer
  renders content with no local host.

## Impact

- New `web/webclient-app/components/QuestLog.vue` and
  `web/webclient-app/components/GuildCounter.vue`; `QuestBoard.vue` deleted along with its story.
- `web/webclient-app/AppClient.vue`: drawer body wiring for the two components.
- `web/webclient-app/stores/elosern.js`: no drawer-name change; the quest drawer is unchanged as a
  name and keeps its hosted-frame teardown.
- New Storybook stories; browser tests updated for the new testids.
- `docs/development/webclient-vue-frozen-contract-audit.md` §2.3 gains the new identifiers.
- **Conflicts with `webclient-lore-codex-drawer`** on `AppClient.vue` and the audit document. Land
  them sequentially, codex drawer first.
