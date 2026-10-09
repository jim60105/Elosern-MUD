## REMOVED Requirements

### Requirement: The npc_schedules clock source settles due schedule entries
**Reason**: This single requirement combines independent source, occurrence, entry, silence, and hold contracts and exceeds the strict-validation size limit. The split replacements preserve its full semantics and scenarios.
**Migration**: None; requirement IDs are test annotations, not persisted runtime data. Retag substantive tests to the replacement canonical IDs in the same implementation.

## ADDED Requirements

### Requirement: The npc_schedules settlement source selects tagged NPCs

The clock SHALL register exactly one `npc_schedules` source, `settle_npc_schedules`. It SHALL select NPCs carrying the persistent `schedule` tag maintained by the `npc-schedule-model` assignment API and startup sync. Untagged NPCs produce no entries or events and have no location or state change.

#### Scenario: The registered source is the sole source
- **WHEN** the registered `npc_schedules` source is inspected
- **THEN** it is `settle_npc_schedules` and no other source is registered under that kind

#### Scenario: An NPC without a schedule settles to nothing
- **WHEN** settlement runs over an NPC without the `schedule` tag
- **THEN** it produces no events and its location and state are unchanged

### Requirement: Occurrences obey the shared due-window boundaries

Shared occurrence arithmetic SHALL include `start_tick < due_tick <= end_tick` and `due_tick >= effective_from_tick`. An occurrence exactly at `start_tick` settles only when `effective_from_tick` equals that tick; otherwise the preceding window settled it.

#### Scenario: An assignment does not replay past occurrences
- **WHEN** an NPC is assigned a schedule after some daily offsets have passed
- **THEN** only occurrences at or after `effective_from_tick` settle; past occurrences cause no events or state changes

#### Scenario: Assignment at the due tick settles on the next advance
- **WHEN** a schedule is assigned exactly at an entry's due tick
- **THEN** that occurrence settles in the next advance, but earlier occurrences never settle

#### Scenario: The start boundary uses the effective-from exception
- **WHEN** an occurrence is due exactly at `start_tick`
- **THEN** it settles only if `effective_from_tick` equals that tick; all other start-boundary occurrences were settled by the preceding window

### Requirement: Cycles and ordering remain absolute and deterministic

Daily and weekly cycles SHALL use shared occurrence arithmetic phase-anchored to absolute tick zero; assignment, reload, and calendar boundaries SHALL NOT restart phase. Settle by `(due_tick, npc_stable_id, entry_index)`, with `npc_stable_id` the unique, JSON-safe persistent primary key `npc_id`. Multi-day skips use boundary arithmetic, not per-second iteration.

#### Scenario: Multi-day skips settle once in due order
- **WHEN** several days with due entries, including an A→B then B→A route, are crossed
- **THEN** each occurrence settles once in stable order and final location matches day-by-day advances, without per-second iteration

#### Scenario: Weekly bulk and bounded advances agree
- **WHEN** bulk and consecutive bounded advances cross a week, season, and year
- **THEN** ordered events and final locations/states agree without duplicates or clock charges

### Requirement: Due state entries update state and emit events

A due `state` entry SHALL update `npc.db.schedule_state` and emit `npc_state_changed`.

#### Scenario: A due state entry updates the NPC state
- **WHEN** a scheduled `state` entry is due in the settlement window
- **THEN** the NPC holds the entry's state and its event names `npc_id` and that state

### Requirement: Due movement uses real exits and emits events

A due `move` SHALL resolve its target room and traverse the real Exit path from the NPC's current room, with locks and vetoes applying. On success, location changes through that path, `schedule_state` becomes the referenced template's `default_state`, and `npc_departed` / `npc_arrived` events are emitted.

#### Scenario: A due move traverses a real Exit
- **WHEN** a move target resolves to a destination with a traversable Exit
- **THEN** the NPC reaches it through the Exit; its default state and departure/arrival events are produced

#### Scenario: Events carry safe identity, target, and due tick
- **WHEN** a settlement event is emitted
- **THEN** its JSON-safe payload carries stable `npc_id`, display `npc`, and `state` or `from`/`to`; `due_tick` equals `cycle_start + tick_offset`

### Requirement: Silenced NPCs skip all schedule effects first

Settlement SHALL first skip every NPC where `world/rules/service_gate.py::schedule_silenced(npc)` is true: a bound party companion with a `place`-bound service component outside its anchor. It has no entries, events, or state change, exactly as if schedule-less; all other NPCs settle byte-identically to pre-change behavior.

#### Scenario: A traveling companion is skipped and resumes at anchor
- **WHEN** a bound guild clerk is away from its anchor across due shifts, then returns for a later due window
- **THEN** no entry/event/state change occurs while away; settlement resumes through the ordinary path after return despite skipped windows

#### Scenario: Unrelated NPCs remain byte-identical
- **WHEN** place-unbound guards and residents share the window
- **THEN** their entries, events, and state match pre-change settlement exactly

### Requirement: An active exam hold defers host schedule mutation

The source SHALL consult a persisted exam-owned hold before host movement/state settlement. A held host accumulates a recoverable interval without routine location/state mutation; unrelated NPCs settle unchanged. The complete hold/release core SHALL be usable before production persistent-host exams activate.

#### Scenario: A held host stays unchanged while others settle
- **WHEN** a synthetic exam hold covers host movement/state and another NPC occurrence
- **THEN** host location/state remain unchanged and the other NPC settles normally

### Requirement: Releasing an exam hold replays its interval once

Release SHALL consume held occurrences once without advancing the world clock. A failed traversal is consumed like an ordinary schedule skip. Corrupt schedule storage SHALL leave the active hold intact for explicit repair.

#### Scenario: Release consumes held occurrences once
- **WHEN** release replays an elapsed held interval
- **THEN** occurrences are consumed once without another clock advance, including failed traversals as skips

#### Scenario: Corrupt schedule storage preserves the hold
- **WHEN** release encounters indeterminate host schedule storage
- **THEN** the active hold remains intact for explicit repair