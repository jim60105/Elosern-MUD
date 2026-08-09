## Why

`npc_schedules` is the only world-clock stage with a name but no source, and the
`npc-schedule-model` change's data contract has no consumer. NPC schedules are inert until
something settles them. This change makes schedules real: due entries move NPCs and change their
states at fixed world times, and schedule states gate NPC-directed interactions.

## What Changes

- **Clock source registration**: `settle_npc_schedules()` registered via
  `register_event_source("npc_schedules", ...)`; the stage stops being a no-op seam.
- **Settlement**: scans NPCs carrying the persistent `schedule` tag (maintained by the model
  change's `set_npc_schedule()` and startup sync — no stale index, no fallback scan), and settles
  every occurrence with `start_tick < due_tick <= end_tick` and `due_tick >= effective_from_tick`
  in `(due_tick, npc_stable_id, entry_index)` order:
  - `move` entries resolve the destination, traverse the real Exit path from the NPC's current
    room (locks and vetoes apply), set `schedule_state` to the template's `default_state` on
    success, and emit `npc_departed` / `npc_arrived` events;
  - `state` entries update `npc.db.schedule_state` and emit `npc_state_changed`.
  Multi-day skips use boundary arithmetic, never per-second iteration. NPC movement never charges
  the clock, never records map knowledge, and never triggers companion follow (the shared
  movement pipeline already no-ops for non-players). Events carry JSON-safe payloads (stable NPC
  identity, `state` or `from`/`to` target) and `due_tick = day_start + tick_offset`.
- **Per-entry failure isolation**: a missing/locked exit or vanished destination skips that entry
  with a bounded diagnostic log and no failure event; other NPCs and entries settle normally.
- **Interaction gating**: `interaction_reason(npc, interaction_kind)` returns a stable rejection
  reason when the NPC's schedule state blocks the interaction kind. Consult points are enumerated
  per kind and cover **every** surface that resolves a local NPC host and performs a transaction —
  the Telnet commands and the WebClient service action adapters (`shop.buy` / `shop.sell` /
  guild operations): `talk` (scripted + free-form), `service_shop`, `service_guild`. The `engage`
  kind is declared in the API but currently unreachable (`engage` already rejects non-hostile
  targets); it is carried for a future NPC-combat change.

## Capabilities

### New Capabilities
- `npc-schedule-runtime`: settlement of due schedule entries (movement, state, events),
  failure isolation, and schedule-state interaction gating.

### Modified Capabilities
- `settlement-stage-order`: the `npc_schedules` stage gains a concrete registered source; it is
  no longer one of the declared no-op seams.
- `scripted-dialogue`: scripted talk may return a stable rejection when the host's schedule state
  blocks the interaction.
- `npc-dialogue`: the LLMNPC dialogue seam consults the schedule gate before running the guarded
  reply pipeline.

## Impact

- `world/rules/npc_schedules.py`: settlement, movement, state, event emission, `interaction_reason()`
- `world/rules/clock.py`: `npc_schedules` source registration (mechanism unchanged)
- `typeclasses/exits.py`: no change — the shared traversal path is reused as-is
- Talk entry points (`commands/talk.py`, `typeclasses/npcs.py`), NPC-hosted service commands
  (`commands/economy.py`, `commands/guild.py`), and the WebClient service action adapters
  (`web/webclient/actions/service_actions.py`): schedule-gate consultation
- `world/rules/rulebook/npc_schedules.yaml` (from `npc-schedule-model`): consumed, not changed
- Integration tests (`EvenniaTest`); no new dependencies
