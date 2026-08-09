# NPC Schedule Runtime

## Purpose

Define the runtime consumption of the NPC schedule model: the `npc_schedules` clock source,
settlement of due move and state entries, deterministic events, failure isolation, and
schedule-state interaction gating.

## ADDED Requirements

### Requirement: The npc_schedules clock source settles due schedule entries

`world/rules/npc_schedules.py` SHALL provide `settle_npc_schedules(start_tick, end_tick)` and
register it through `world.rules.clock.register_event_source("npc_schedules", ...)` as the only
`npc_schedules` source. Settlement SHALL query NPCs carrying the persistent `schedule` tag (the
`npc-schedule-model` assignment API and startup sync maintain it) and, for every occurrence with
`start_tick < due_tick <= end_tick` and `due_tick >= effective_from_tick`, settle it in
`(due_tick, npc_stable_id, entry_index)` order: a `move` entry SHALL resolve its target to a
destination room, traverse the real Exit path from the NPC's current room (locks and vetoes
apply), and on success set `schedule_state` to the referenced template's `default_state` and emit
`npc_departed` / `npc_arrived` events; a `state` entry SHALL update `npc.db.schedule_state` and
emit `npc_state_changed`. Multi-day skips SHALL use boundary arithmetic, not per-second iteration.
An NPC with no schedule SHALL produce no entries and no events. Every event SHALL carry a
JSON-safe payload (stable NPC identity; `state` or `from`/`to` target) and
`due_tick = day_start + tick_offset`.

#### Scenario: A due state entry updates the NPC's schedule state
- **WHEN** an NPC with a schedule whose next `state` entry falls within `(start_tick, end_tick]`
  is settled
- **THEN** `npc.db.schedule_state` holds the entry's state and the returned events include
  `npc_state_changed` for that NPC with a payload naming the NPC and state

#### Scenario: A due move entry relocates the NPC along a real Exit
- **WHEN** an NPC's due `move` entry resolves to a destination with a traversable Exit from the
  NPC's current room
- **THEN** the NPC's location changes to the destination through the Exit path, `schedule_state`
  becomes the template's `default_state`, and `npc_departed` / `npc_arrived` events with
  `from`/`to` payloads and the entry's due tick are emitted

#### Scenario: An NPC without a schedule settles to nothing
- **WHEN** settlement runs over an NPC without the `schedule` tag
- **THEN** the NPC produces no events and its location and state are unchanged

#### Scenario: A multi-day skip settles every due entry exactly once, in due order
- **WHEN** `advance()` crosses several world days with schedule entries due on each, including an
  A→B and later B→A route
- **THEN** every due occurrence settles exactly once, in `(due_tick, npc_stable_id, entry_index)`
  order, and the NPC's final location equals the location repeated day-by-day advances would
  produce; no per-second iteration occurs

#### Scenario: A schedule assigned mid-day does not replay past occurrences
- **WHEN** an NPC is assigned a schedule after some of that day's `tick_offset`s have passed
- **THEN** only occurrences with `due_tick >= effective_from_tick` settle; the passed occurrences
  produce no events and no state change

#### Scenario: The stage source is the registered one
- **WHEN** the clock's registered `npc_schedules` source is inspected
- **THEN** it is `settle_npc_schedules` and no other source is registered under that kind

### Requirement: NPC movement through settlement never charges the clock, records map knowledge,
or triggers companion follow

Settlement-driven NPC traversal SHALL flow through the shared movement pipeline's `at_post_traverse`
hook, whose `charge_movement`, `record_arrival`, and `follow_companions` calls SHALL remain no-ops
for non-`PlayerCharacter` traversers. A settled move SHALL therefore leave the world tick, the
player's map-knowledge record, and the party-follow state unchanged.

#### Scenario: A settled NPC move does not advance the world clock
- **WHEN** an NPC's due `move` entry traverses an Exit during settlement
- **THEN** the world tick is unchanged by that traversal

#### Scenario: A settled NPC move records no map knowledge
- **WHEN** an NPC's due `move` entry traverses an Exit during settlement
- **THEN** no player's map-knowledge record changes

#### Scenario: A settled NPC move does not trigger companion follow
- **WHEN** an NPC's due `move` entry traverses an Exit during settlement
- **THEN** no companion-follow side effect occurs

### Requirement: A failed entry settles as a per-entry skip without blocking settlement

A `move` entry whose target cannot resolve, whose room has no traversable Exit to the destination,
whose Exit is locked, or whose destination is gone SHALL skip only that entry: a bounded diagnostic
log, no location/state change, and **no failure event** — the event stream contains only successful
occurrences. Settlement SHALL never raise from one NPC's failure and SHALL never roll back other
NPCs.

#### Scenario: A locked Exit skips only that move entry
- **WHEN** an NPC's due `move` entry points through a locked Exit while another NPC has a valid
  due entry
- **THEN** the locked NPC stays put with a bounded diagnostic, and the other NPC settles normally

#### Scenario: An unresolvable target skips the entry
- **WHEN** an NPC's due `move` entry references a target that resolves to no room
- **THEN** the entry is skipped, the NPC stays put, and no event for that move is emitted

### Requirement: Schedule state gates NPC-directed interactions at every host-resolving surface

`world/rules/npc_schedules.py` SHALL provide
`interaction_reason(npc, interaction_kind) -> str | None`: `None` when the NPC's `schedule_state`
does not block the interaction kind, otherwise a stable authored Traditional Chinese rejection
reason. The consult points SHALL be enumerated per kind and SHALL cover every surface that
resolves a local NPC host and performs a transaction: `talk` SHALL be consulted by the scripted-talk
command path and the free-form dialogue seam (`LLMNPC.at_talked_to` / `run_npc_exchange`);
`service_shop` SHALL be consulted by the shop buy/sell commands and the WebClient `shop.buy` /
`shop.sell` action adapters; `service_guild` SHALL be consulted by the guild operation commands
and the WebClient guild action adapters whenever the resolved local host is the NPC. A blocked
interaction SHALL present the stable reason and SHALL write no state — no affinity gain, no guide
progress, no memory append, no intent application, no transaction. The `engage` kind SHALL be
declared in the API; it SHALL be unreachable today because the engagement surface rejects
non-hostile targets, and SHALL require no gate at that surface.

#### Scenario: A busy schedule state blocks scripted talk with a stable reason
- **WHEN** the player talks to a scripted-dialogue host whose `schedule_state` is `busy`
- **THEN** the player receives the stable rejection line and no affinity, guide progress, memory,
  or intent state changes

#### Scenario: A busy schedule state blocks free-form talk
- **WHEN** the player talks to an `LLMNPC` whose `schedule_state` is `busy`
- **THEN** the guarded reply pipeline is never invoked and the stable rejection line is shown

#### Scenario: A blocked merchant's shop trade is refused on every surface
- **WHEN** the player attempts to buy or sell through the shop command or the WebClient
  `shop.buy` / `shop.sell` adapters with a merchant whose `schedule_state` blocks the service
- **THEN** every surface returns the stable rejection reason and no transaction occurs

#### Scenario: A blocked guild host's operations are refused on every surface
- **WHEN** the player runs a guild operation command or its WebClient action with a guild host
  whose `schedule_state` blocks the service
- **THEN** the operation returns the stable rejection reason and no state changes

#### Scenario: The engage kind is declared but unreachable
- **WHEN** the interaction-kind vocabulary is inspected
- **THEN** `engage` is declared, and the engagement surface needs no schedule gate because it
  rejects non-hostile targets before any schedule check

#### Scenario: An unblocked NPC proceeds unchanged
- **WHEN** an NPC's `schedule_state` is `None` or does not block the interaction kind
- **THEN** `interaction_reason` returns `None` and the interaction behaves exactly as before
