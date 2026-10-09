
## Purpose

Define the runtime consumption of the NPC schedule model: the `npc_schedules` clock source,
settlement of due move and state entries, deterministic events, failure isolation, and
schedule-state interaction gating.

## Requirements

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
whose Exit is locked, or whose destination is gone SHALL skip only that entry: a bounded
diagnostic log, no location/state change, and **no failure event** — the event stream contains
only successful occurrences. Settlement SHALL never raise from one NPC's failure and SHALL never
roll back other NPCs.

#### Scenario: A locked Exit skips only that move entry
- **WHEN** an NPC's due `move` entry points through a locked Exit while another NPC has a valid
  due entry
- **THEN** the locked NPC stays put with a bounded diagnostic, and the other NPC settles normally

#### Scenario: An unresolvable target skips the entry
- **WHEN** an NPC's due `move` entry references a target that resolves to no room
- **THEN** the entry is skipped, the NPC stays put, and no event for that move is emitted

#### Scenario: A redirecting exit never moves the NPC off the scheduled route
- **WHEN** an NPC's due `move` entry resolves to a destination whose only candidate Exit
  overrides `at_traverse` to ignore the requested destination
- **THEN** the entry is skipped, the NPC stays put (never relocated to an un-named room), and no
  event for that move is emitted

#### Scenario: Redirecting non-standard traversal is a defined failure mode
- **WHEN** a `move` entry's only candidate Exit is a redirecting non-standard traversal (an `at_traverse` that ignores the requested destination, such as the wilderness gates)
- **THEN** it is treated as this per-entry-skip failure mode

### Requirement: Schedule state gates NPC-directed interactions at every host-resolving surface

`world/rules/npc_schedules.py` SHALL provide
`interaction_reason(npc, interaction_kind) -> str | None`: `None` when the NPC's `schedule_state`
does not block the interaction kind, otherwise a stable authored Traditional Chinese rejection
reason. A blocked interaction SHALL present the stable reason and SHALL write no state — no
affinity gain, no guide progress, no memory append, no intent application, no transaction.

#### Scenario: A busy schedule state blocks scripted talk with a stable reason
- **WHEN** the player talks to a scripted-dialogue host whose `schedule_state` is `busy`,
  through the text `talk` command or the WebClient `explore.talk_scripted` action
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

#### Scenario: The enumerated consult points per interaction kind
- **WHEN** the consult points are enumerated
- **THEN** the consult points SHALL be enumerated per kind, covering every surface that resolves a local NPC host and performs a transaction
- **AND** `talk` is consulted by the scripted-talk command path — the text `talk` command and the WebClient `explore.talk_scripted` action — and the free-form dialogue seam (`LLMNPC.at_talked_to`)
- **AND** its direct `run_npc_exchange` callers are the party-invite surface, which is not an enumerated interaction kind and needs no gate in this change
- **AND** `service_shop` is consulted by the shop buy/sell commands and the WebClient `shop.buy` / `shop.sell` action adapters
- **AND** `service_guild` is consulted by the guild operation commands and the WebClient guild action adapters whenever the resolved local host is the NPC

#### Scenario: The engage kind is declared but unreachable and needs no gate
- **WHEN** the `engage` interaction kind is considered
- **THEN** it SHALL be declared in the API, SHALL be unreachable today because the engagement surface rejects non-hostile targets, and SHALL require no gate at that surface

### Requirement: The npc_schedules clock source is registered before startup combat recovery advances time

The server `at_server_start()` composition root SHALL call `sync_npc_schedules()` — and through it `register_npc_schedules()` — before `restore_persisted_sessions()` may advance the world clock, so every schedule occurrence whose due tick falls inside a startup recovery settlement window settles exactly as it would in an ordinary advance.

#### Scenario: A recovery advance settles an occurrence due inside its window

- **WHEN** a cold start begins at tick 0 with an NPC whose schedule is effective from tick 0 and has a `state` entry due at tick 3, and a well-formed one-round persisted session that is terminated as invalid (recorded enemy deleted) settles through restoration, advancing the clock from 0 to 6
- **THEN** the tick-3 occurrence settles: the NPC's `schedule_state` holds the entry's state and a `npc_state_changed` event with the entry's due tick is produced, exactly as if `advance(6, ...)` had run with `npc_schedules` registered

#### Scenario: The stage source is registered from startup, not lazily

- **WHEN** `at_server_start()` has completed its deterministic sync sequence
- **THEN** the clock's registered `npc_schedules` source is `settle_npc_schedules` and it was registered before any startup-time world advance

#### Scenario: The recovery settlement window uses the ordinary due-tick bounds
- **WHEN** a startup recovery settlement window is evaluated for occurrences
- **THEN** its bounds are `start_tick < due_tick <= end_tick` and `due_tick >= effective_from_tick`

#### Scenario: No occurrence is lost to an unregistered stage and no backfill is required
- **WHEN** a recovered session's accumulated rounds produce a settlement window
- **THEN** the window SHALL NOT lose an occurrence to an unregistered `npc_schedules` stage, and no later sync or backfill SHALL be required to recover it
