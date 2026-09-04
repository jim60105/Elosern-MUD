# Proposal: webclient-align-06-quest-tracking-contract

## Why

The draft's bottom-right 目標 tracker is the last HUD surface deferred for lack of a read model.
Quest truth exists server-side (`world/quests/runtime.py` records, stage objectives,
`describe_objective`/`describe_deadline` prose), but nothing discloses which active quests the
player tracks, and the alignment design pins the tracker to server-side tracking state
(`tracked` on the record + the `guild.quest_track` WS action, cap 3). The one gap against the
design doc's original sketch: deriving the tracker from `services.guild.quests` rows cannot
work — that section is guild-host-gated, so the tracker would vanish outside the guild hall.
This change keeps every design-doc server decision (record field, action, cap, panel-backed
first-3 rows) and amends only the disclosure vehicle: a dedicated `objectives` panel reads the
same record truth independent of any host. The client surfaces (tracker island, browser toggle,
showcase) were split into **webclient-align-09-objective-tracker-ui** after rubber-duck review.

## What Changes

- **Tracking state (design-doc §3/Change 6):** persistent boolean `tracked` on `QuestRecord`
  (default false; accepting never auto-tracks), written only through the quest lifecycle API
  (`world/quests/runtime.py`); a new `guild.quest_track` WS action with payload
  `{quest_id, tracked}` — setting true beyond the cap of 3 tracked quests is rejected, and only
  `in_progress` records are trackable.
- **New `objectives` presentation panel (schema version 1):** available form carries `rows` —
  the holder's `tracked && in_progress` records in quest-log order, each
  `{quest_id, display_name, objective_line, stage_index, stage_total, stage_progress,
  objective_quantity, reward_copper, deadline_line}` with prose from the existing describe
  seams. No guild host is required; empty tracked set → `rows: []`; corrupt log → shared
  unavailable form.
- **Services panel v3 → v4:** `guild.quests` rows gain `tracked: bool` (validator mirrored).

## Capabilities

### New Capabilities

- `webclient-objectives-panel`: the tracked-objectives read model — shape, describe-seam reuse,
  host independence, availability forms, push timing on quest/tracking seams, read-only
  isolation.

### Modified Capabilities

- `quest-lifecycle`: `tracked` joins the JSON-safe record; a bounded deterministic tracking
  operation owns the write.
- `webclient-service-menus`: services schema v4 with `tracked` on quest rows; the action set
  gains `guild.quest_track`. (The browser's tracking-toggle UI is a client requirement and
  moved to webclient-align-09-objective-tracker-ui.)

## Impact

- `world/quests/runtime.py` (record field, storage, lifecycle op, cap), `services.py`
  (schema v4 + row validator), new `web/webclient/presentation/objectives.py`, registry
  registration, action registry + `service_actions.py` adapter, coordinator invalidation on
  accept/abandon/fulfil/fail/progress/track seams.
- UMD + Vue panel allowlists gain `objectives` (three-list agreement test extended);
  `.github/evennia-shards.json` gains the new server test modules.
- No client UI in this change: `ObjectiveTracker.vue`, the QuestBoard toggle, and the showcase
  registration all belong to webclient-align-09-objective-tracker-ui.
- Amends `docs/superpowers/specs/2026-09-04-webclient-redesign-alignment-design.md` §3 Change 6:
  the tracker derives from the `objectives` panel, not from guild-host-gated services rows, and
  the change split into 06 (server) + 09 (client).
