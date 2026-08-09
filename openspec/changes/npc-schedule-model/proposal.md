## Why

`npc_schedules` is the only world-clock settlement stage without a registered source
(`world/rules/clock.py:41` lists the name; no `register_event_source("npc_schedules", ...)` caller
exists), and `NPC.schedule` (`typeclasses/npcs.py:31`) is an unused placeholder attribute. NPCs
therefore have no schedule data at all — the foundation for any future world-simulation behavior.

This first slice establishes the deterministic schedule **data model**: immutable role templates,
per-NPC schedule storage, validation, and idempotent startup synchronization. The clock settlement,
movement, and interaction gating that consume this model land in the companion `npc-schedule-runtime`
change.

## What Changes

- **New rulebook data**: `world/rules/rulebook/npc_schedules.yaml` with `schema_version: 1` and a
  `templates:` mapping of role templates (`guard`, `storekeeper`, `resident`, ...). Each template is
  an ordered list of entries: `{tick_offset, kind: move|state, target?, state?}` where
  `tick_offset` is seconds since world-day start and entries repeat daily; templates may declare an
  optional `default_state` (vocabulary-validated) that a successful move settlement writes.
- **Per-NPC storage**: `npc.db.schedule` accepts exactly two validated shapes — a template reference
  (`{"schema_version": 1, "template": <key>, "overrides": {...}}`) or a full custom list
  (`{"schema_version": 1, "entries": [...]}`). Special NPCs (event or major characters) use the
  custom form; ordinary NPCs reference a template.
- **Sole assignment API**: `set_npc_schedule(npc, schedule)` validates the schedule, records
  `effective_from_tick` (the assignment world tick — mid-day assignment never replays past
  occurrences), and maintains a persistent `schedule` tag on the NPC so settlement finds
  post-startup or reassigned NPCs.
- **Validation**: template keys resolve against the rulebook; entry fields are type-checked and
  bounded (`tick_offset` in `[0, day_seconds)`, `kind` in `{move, state}`, `target`/`state` presence
  per kind, `default_state` in the vocabulary); malformed schedules are rejected with named errors
  at assignment and at consumption, never silently accepted.
- **Startup sync**: an idempotent startup pass confirms template references, validates stored
  schedules, and confirms the `schedule` tag on every schedule-bearing NPC; failures log and
  degrade to "no schedule" rather than blocking startup.
- **Runtime-state declaration**: the change declares the `npc.db.schedule_state` attribute contract
  (current state or `None`) that the runtime change writes; no clock or gameplay behavior changes in
  this slice.

## Capabilities

### New Capabilities
- `npc-schedule-model`: the deterministic NPC schedule data contract — rulebook templates, per-NPC
  storage shapes, entry validation, and startup synchronization.

### Modified Capabilities

None. This slice changes no existing requirement-level behavior; the `npc_schedules` stage remains a
registered-name/no-source seam until the runtime change.

## Impact

- `world/rules/rulebook/npc_schedules.yaml` (new data)
- `world/rules/npc_schedules.py` (new: parsing, validation, `set_npc_schedule()` assignment API,
  sync helpers)
- `typeclasses/npcs.py` (`schedule` placeholder attribute contract documented; storage written only
  through the assignment API)
- Startup bootstrap path (idempotent schedule sync alongside existing syncs)
- Pure unit tests; no database, command, or clock behavior changes
