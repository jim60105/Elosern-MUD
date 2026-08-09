# npc-schedule-runtime — Design

## Context

The companion `npc-schedule-model` change ships the schedule data contract: role templates in
`rulebook/npc_schedules.yaml`, the two `npc.db.schedule` storage shapes, validation, and startup
synchronization. This change consumes that model. `world/rules/clock.py` lists `npc_schedules` in
its fixed stage order but no source is registered; the `settlement-stage-order` main spec still
documents it as a "declared, registrable, no-op seam".

The deterministic core owns all writes: settlement, movement, and schedule state are applied by
`world/rules/`; the generative layer never participates. The project is unreleased; no migration.

## Goals / Non-Goals

### Goals

- Register `settle_npc_schedules()` as the `npc_schedules` clock source.
- Settle due `move` and `state` entries with boundary arithmetic; move NPCs along real Exits.
- Emit deterministic `npc_departed` / `npc_arrived` / `npc_state_changed` events.
- Isolate failures per entry (skip, never block settlement).
- Provide `interaction_reason(npc, interaction_kind)` and consult it at the NPC-directed talk and
  service entry points.

### Non-Goals

- No schedule authoring or content: which shipped NPCs carry schedules is a separate content
  change; this change supplies the mechanism.
- No change to `typeclasses/exits.py`, the shared movement pipeline, or clock math.
- No changes to combat, quest, economy, or generative behavior beyond the talk/service gates.
- No weekly or multi-day cycles (the model repeats daily).

## Decisions

### D1: Settlement registers one source and scans the schedule tag

`settle_npc_schedules(start_tick, end_tick)` is registered through the existing
`register_event_source("npc_schedules", ...)` mechanism (same shape as `caravan_arrivals` /
`shop_hours`). It queries NPCs carrying the persistent `schedule` tag maintained by the model
change's `set_npc_schedule()` and startup sync — post-startup spawned or reassigned NPCs are
always found, so no stale index and no fallback scan exist. Due occurrences settle in
`(due_tick, npc_stable_id, entry_index)` order (duplicate `tick_offset`s tie-break by stable entry
index), so one multi-day `advance()` produces the same locations as repeated day-by-day advances.

- Alternatives: per-NPC one-off Deferred timers — rejected: the player-driven clock settles
  in fixed stages; timer-based NPC movement would escape settlement ordering and replayability.
- Why: matches every other world-event seam; deterministic and replayable; ordering is
  load-bearing for A→B→A routes across multi-day skips.

### D2: Movement walks the real Exit path; success writes the template's default_state

A `move` entry resolves its `target` (stable key via existing registries, or dbref override) to a
destination room, finds the real Exit from the NPC's current room leading to it, and traverses it —
locks and vetoes apply exactly as for a player. `MovementCostMixin.at_post_traverse` already
no-ops `charge_movement`, `record_arrival`, and companion follow for non-`PlayerCharacter`
traversers (`typeclasses/exits.py:35-47`), so NPC movement never advances the clock, never records
map knowledge, and never triggers follow. A successful move sets `npc.db.schedule_state` to the
referenced template's `default_state` (the only state change a move makes — move entries never
carry a `state` field).

- Alternatives: direct `move_to()` relocation — rejected: bypasses exit locks and vetoes and
  diverges from the map-movement-clock idiom of one shared traversal path.
- Why: the design doc's S3; observable consequences of a "real Exit traversal" are cheap and
  already correct; the `default_state` rule removes ambiguity about what a move writes.

### D3: Per-entry skip on failure, logged only

A missing exit, a locked exit, a vanished destination, or a malformed entry skips only that entry:
a bounded diagnostic log, no exception, no rollback of other entries or NPCs, and **no failure
event** — the `ScheduledEvent` stream contains only successful `npc_departed` / `npc_arrived` /
`npc_state_changed` occurrences.

- Alternatives: abort the NPC's remaining day — rejected by the superpowers design (S5);
  retry at the next boundary — rejected: adds complexity without a consumer.
- Why: one NPC's broken schedule must never stall the clock or other NPCs; a failure event would
  create an unmeasured contract for monitors and the narrator.

### D4: One gate API, consulted at every host-resolving surface

`interaction_reason(npc, interaction_kind) -> str | None` returns a stable, authored
Traditional Chinese rejection reason when the NPC's `schedule_state` blocks the interaction kind;
`None` means proceed. The interaction kinds and their exact consult points are enumerated:

- `talk` — the scripted-talk command path (`commands/talk.py`) and the free-form seam
  (`LLMNPC.at_talked_to` / `run_npc_exchange`);
- `service_shop` — the shop buy/sell commands (`commands/economy.py`) **and** the WebClient
  `shop.buy` / `shop.sell` action adapters (`web/webclient/actions/service_actions.py`);
- `service_guild` — the guild operation commands (`commands/guild.py`) **and** the WebClient
  guild action adapters, whenever the resolved local host is the NPC.

The gate is therefore consulted on every surface that resolves a local NPC host and performs a
service transaction — a busy merchant cannot be traded through the browser while the command path
rejects. `engage` is declared as an interaction kind but is currently unreachable: the engagement
surface rejects non-hostile targets (`SessionReason.NOT_HOSTILE`) before any schedule check, and
the schedule model is NPC-only; the kind is carried so a future NPC-combat change inherits the
gate (recorded as a dated amendment in the superpowers design).

- Alternatives: gate inside each deterministic service API — rejected: the service APIs and their
  specs stay unchanged; the gate is an interaction-surface concern, applied at every command and
  adapter entry so the deterministic transactions are untouched.
- Why: the design doc's S4 with an enumerated, no-bypass surface; services consult the same
  function without altering their atomic guarantees.

### D5: Gated talk writes nothing

When the gate blocks a talk interaction, the stable rejection line is shown and **no state
changes** — no affinity gain, no guide progress, no memory append, no intent application.

- Alternatives: partial processing with affinity withheld — rejected: the scripted-dialogue spec's
  known-keyword path grants affinity; a blocked interaction is not an answered interaction.
- Why: keeps the gate side-effect-free and trivially testable.

## Risks / Trade-offs

- [Exit ambiguity: multiple exits to the destination] → Deterministic resolution (e.g., first
  traversable exit in stable order); documented and tested.
- [Settlement cost of querying all tagged NPCs] → The persistent `schedule` tag limits the query
  to schedule-bearing NPCs; the tag is maintained by the sole assignment API and startup sync, so
  no unbounded scan exists.
- [Gate ordering vs shop hours] → The schedule gate is an additional layer on top of existing
  shop-hours logic; both can reject, the stable reason names the actual blocker.
- [Events flooding a long skip] → Settlement emits one event per settled occurrence; the narrator
  and template renderers already handle bounded event streams; long skips are a content concern.
- [Zero shipped schedules make the feature inert] → Accepted: mechanism-first, content-second;
  integration tests construct schedule-bearing NPCs to prove the contract.

## Migration Plan

No migration. NPCs without schedules produce no entries and are unaffected. The
`settlement-stage-order` requirement is updated from "no-op seam" to "registered source" in the
same change.

## Open Questions

- None blocking. Which shipped NPCs carry which templates (guard shifts, storekeeper hours) is a
  deliberate follow-up content change; the mechanism here accepts any schedule the model validates.
