# Delta spec: npc-schedule-runtime (service-anchor-presentation-silence)

Adds the traveling-place-bound silence skip to settlement. The settlement requirement is
reproduced in full (body and every pre-existing scenario verbatim) with the silence rule inserted
into the body and three silence scenarios appended.

## MODIFIED Requirements

### Requirement: The npc_schedules clock source settles due schedule entries

`world/rules/npc_schedules.py` SHALL provide `settle_npc_schedules(start_tick, end_tick)` and
register it through `world.rules.clock.register_event_source("npc_schedules", ...)` as the only
`npc_schedules` source. Settlement SHALL query NPCs carrying the persistent `schedule` tag (the
`npc-schedule-model` assignment API and startup sync maintain it) and, for every occurrence with
`start_tick < due_tick <= end_tick` and `due_tick >= effective_from_tick`, settle it in
`(due_tick, npc_stable_id, entry_index)` order — where `npc_stable_id` is the persistent primary
key (`npc_id`), unique and JSON-safe where display keys are not. An occurrence due exactly at
`start_tick` SHALL settle only when `effective_from_tick` equals that tick (the assignment
happened at that same moment, so no earlier window could have settled it); any other occurrence at
the start boundary was already settled by the preceding window. A `move` entry SHALL resolve its
target to a destination room, traverse the real Exit path from the NPC's current room (locks and
vetoes apply), and on success set `schedule_state` to the referenced template's `default_state`
and emit `npc_departed` / `npc_arrived` events; a `state` entry SHALL update
`npc.db.schedule_state` and emit `npc_state_changed`. Multi-day skips SHALL use boundary
arithmetic, not per-second iteration. An NPC with no schedule SHALL produce no entries and no
events. Every event SHALL carry a JSON-safe payload (the stable `npc_id`, a display `npc` key,
and `state` or `from`/`to` target) and `due_tick = day_start + tick_offset`. Settlement SHALL
first skip every NPC for which `world/rules/service_gate.py::schedule_silenced(npc)` is true —
a bound party companion carrying a `place`-bound service component outside its anchor room —
producing no entries, no events, and no state change for it, exactly as a schedule-less NPC;
every other NPC SHALL settle byte-identically to the pre-change settlement.

#### Scenario: A due state entry updates the NPC's schedule state
- **WHEN** an NPC with a schedule whose next `state` entry falls within `(start_tick, end_tick]`
  is settled
- **THEN** `npc.db.schedule_state` holds the entry's state and the returned events include
  `npc_state_changed` for that NPC with a payload naming the NPC's `npc_id` and state

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

#### Scenario: A schedule assigned exactly at an entry's due tick settles that occurrence
- **WHEN** an NPC is assigned a schedule at the exact world tick one of its entries is due
- **THEN** that occurrence settles in the next advance (its due tick equals the assignment tick,
  so no earlier window could have settled it), and occurrences due before the assignment never do

#### Scenario: The stage source is the registered one
- **WHEN** the clock's registered `npc_schedules` source is inspected
- **THEN** it is `settle_npc_schedules` and no other source is registered under that kind

#### Scenario: A traveling place-bound companion settles nothing
- **WHEN** the guild clerk is a bound companion standing in a wilderness room away from his
  anchor, and the window crosses a full day of his authored shift
- **THEN** no entry of his schedule settles, no `npc_departed` / `npc_arrived` /
  `npc_state_changed` event names him, and his `schedule_state` is unchanged

#### Scenario: Returning to anchor resumes settlement
- **WHEN** the dismissed clerk stands again in his anchor room and a window crosses due entries
- **THEN** those entries settle through the ordinary path (boundary arithmetic tolerates the
  skipped windows)

#### Scenario: Unrelated NPCs are byte-identical
- **WHEN** the guard and resident NPCs (place-unbound) settle across the same window as the
  silenced clerk
- **THEN** their entries, events, and state match the pre-change settlement exactly
