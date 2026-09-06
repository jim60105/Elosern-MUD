# Proposal: webclient-quest-log-panel

## Why

Away from a guild clerk the quest drawer is empty. The `任務` dock tab is always present in
exploration mode — `exploration.quests.available` mirrors whether the services view can be built,
which needs no host — so the drawer opens anywhere, but `QuestBoard.vue` reads only `services.guild`,
and `_build_guild()` returns `None` without a local `GuildStaff`. The player sees
`尚未取得公會資料`.

Quest details are handed to the player when the quest is accepted. Reading one's own quest log is not
a counter service; only accepting new quests, browsing the board, turning in, claiming rewards, and
taking the rank examination are. And once private commissions exist, some quests have no counter at
all, so a host-gated read model cannot show them.

## What Changes

- New host-independent `quest_log` presentation panel (schema version 1), one row per stored record
  in quest-log order, capped at the shared `MAX_QUEST_ROWS` bound of 12.
- Each row carries the record's identity and progress (`quest_id`, `definition_key`, `display_name`,
  `state`, `stage_index`, `stage_total`, `stage_progress`, `objective_quantity`, `tracked`), its
  prose (`objective_line`, `deadline_line`, `detail`), its commission (`issuer` with kind, key, and
  display label; `settlement`; nullable `reward_line`), and the always-available `track` action
  descriptor.
- All prose comes from the canonical describe seams — `describe_objective`, `describe_deadline`,
  `describe_quest_detail`, `describe_reward` — so the quest book, the objective tracker, and the
  guild counter can never disagree.
- An unresolvable issuance yields a null `reward_line` rather than a fabricated one; the row still
  renders.
- A `QuestDataError` from the strict reader degrades the WHOLE panel to the registry-owned common
  unavailable form — never a partial row list.
- Registry registration plus a coordinator dirty-flag push on the existing quest-log mutation seams.
- Client-side validator mirroring the exact Python bounds, covered by the existing dual-direction
  parity test.
- The `objectives` panel is deliberately left unchanged. It serves the HUD tracker island with
  different bounds (three tracked in-progress rows) and a different lifecycle; both derive from the
  same describe seams, so the duplication cannot drift.

## Capabilities

### New Capabilities

- `webclient-quest-log-panel`: the `quest_log` read model — its shape and bounds, host independence,
  the canonical prose sources, issuer and settlement disclosure, the all-or-nothing degradation rule,
  push timing, and read-only presenter isolation.

### Modified Capabilities

(None — panel registration rides the existing `webclient-oob-protocol` registration contract without
changing it.)

## Impact

- New presenter and validator module `web/webclient/presentation/quest_log.py`; registration in the
  presentation registry.
- Client mirror in `web/static/webclient/js/elosern/protocol.js` and the
  `webclient-vue-application` protocol mirror table, so a stale client rejects rather than renders.
- New focused test module; `.github/evennia-shards.json` updated in the same change.
- No client component consumes it yet — `webclient-quest-drawer-split` does.
