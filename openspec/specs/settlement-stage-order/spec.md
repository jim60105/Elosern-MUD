## Purpose

Define the deterministic order and execution rules for world-clock settlement stages.

## Requirements


### Requirement: Settlement stages run in the fixed order regen, buffs, sexual decay, practice settlement,
daily resets, then the five declared world-event seams
`world/rules/clock.py` SHALL define a single, ordered stage sequence — `gauge_regen`, `buff_ticks`,
`sexual_decay`, `practice_settlement`, `daily_resets`, `caravan_arrivals`, `shop_hours`, `quest_deadlines`,
`npc_schedules`, `instance_reclamation` — matching design doc §6.5's four built stages plus
`practice_settlement` (the declared-practice writer owned directly by
`world/rules/clock.py`, inserted between `sexual_decay` and
`daily_resets`) plus `instance_reclamation` (change 14's `reclaim_due_instances()`, appended after
`npc_schedules` as the final stage), and SHALL execute every `advance()` call's stages in this order
with no configuration or call-site override capable of changing it.

#### Scenario: The stage order is exactly the fixed sequence, including practice_settlement and instance_reclamation
- **WHEN** the settlement stage sequence is inspected
- **THEN** it is exactly `("gauge_regen", "buff_ticks", "sexual_decay", "practice_settlement", "daily_resets",
  "caravan_arrivals", "shop_hours", "quest_deadlines", "npc_schedules", "instance_reclamation")`, in
  that order, with no duplicate or missing entry

#### Scenario: Transposing any of the four ordered stages is mechanically detected
- **WHEN** a test asserts `"buff_ticks"` appears strictly before `"sexual_decay"` and strictly after
  `"gauge_regen"` in the stage sequence, and `"practice_settlement"` appears strictly between `"sexual_decay"`
  and `"daily_resets"`
- **THEN** the assertion fails immediately if the stage sequence is ever edited to place any of these
  stages out of that relative order

#### Scenario: A transposed regen/buff order produces a different, incorrect final hp value
- **WHEN** a fixture entity starts with `hp` within one regen-step of its gauge `max`, an active
  `poisoned` buff, and a fixed elapsed time is settled once under the correct order (`gauge_regen`
  before `buff_ticks`) and once under a deliberately transposed order (`buff_ticks` before
  `gauge_regen`) constructed in the same test
- **THEN** the two resulting final `hp` values differ, because the regen-first order clamps against
  `max` on a step the buff-first order does not, proving the order has an observable, not merely
  documented, consequence

#### Scenario: No arithmetic transposition proof exists for practice settlement, because it shares no
resource with its neighbors
- **WHEN** `practice_settlement`'s data dependencies are inspected (it reads the caller's
  declared-practice booking and race/buff state, and writes only `skill_proficiency`) against `sexual_decay`'s (`entity.sexual`'s ordered-level fields) and
  `daily_resets`'s (`entity.sexual.climax_today` only)
- **THEN** no field is written by both `practice_settlement` and either neighbor, so the
  structural check above
  is `practice_settlement`'s only mechanical safeguard against transposition — this is a verified property, not
  an unexamined gap

#### Scenario: instance_reclamation running after quest_deadlines and npc_schedules reclaims within
one advance() call; running before either leaves the room existing for one extra call
- **WHEN** a test registers a synthetic `quest_deadlines` source that, when its deadline comes due
  within `(start_tick, end_tick]`, calls `unpin_instance_room()` on a target `InstanceRoom`, and that
  room is simultaneously due for TTL reclamation, unoccupied, unnamed, and pinned by exactly the
  reason the synthetic source releases
- **THEN** under the declared order (`quest_deadlines` before `instance_reclamation`), a single
  `advance()` call across both boundaries results in the room no longer existing; a test that
  constructs the transposed order (`instance_reclamation` before `quest_deadlines`) in isolation shows
  the same single `advance()` call leaves the room still existing, deferred, requiring a second call —
  an existence-differs proof, not merely a differently-ordered but equivalent outcome

#### Scenario: instance_reclamation position is not itself proof against every possible transposition,
and this is a stated, not silent, limitation
- **WHEN** `instance_reclamation`'s data dependencies are inspected (reads/writes `InstanceRoom.db.
  expire_tick`/`named`/`interacted`/`pin_reasons`/`owned_entities`, none of which any other stage reads
  or writes) against `caravan_arrivals`/`shop_hours`/`npc_schedules`, none of which has a registered
  source in this project's shipped codebase as of this change (and `npc_schedules`, once
  `instance_reclamation`'s own occupancy check was corrected during rubber-duck review to gate on
  `PlayerCharacter` rather than any `LivingEntity`, no longer has any concrete releasing mechanism this
  design depends on either — see design.md D-3's own correction note)
- **THEN** the transposition proof above is the sole mechanical safeguard for `instance_reclamation`'s
  position relative to `quest_deadlines` specifically; its position relative to `caravan_arrivals`/
  `shop_hours`/`npc_schedules` (all three still unregistered, no-op seams, and none with a concrete
  releasing story this design leans on) has no equivalent proof and is justified by "last, so nothing
  after it could still need the room" reasoning alone (design.md D-3), not by an arithmetic
  counter-example against any of the three

### Requirement: buff_ticks, sexual_decay, and practice settlement are skipped for combat-sourced advances
`world/rules/clock.py`'s settlement stage runner SHALL skip the `buff_ticks`, `sexual_decay`, and
`practice_settlement` stages entirely when `advance()` is called with `AdvanceSource.COMBAT`: `buff_ticks` and
`sexual_decay` because change 9's `run_round()` already applies both once per round as part of combat's
own per-round upkeep; `practice_settlement` because declared practice is a downtime concept that must
never settle during a fight. Every other stage (`gauge_regen`, `daily_resets`, and the four declared world-event
stages) SHALL run regardless of `AdvanceSource`.

#### Scenario: A combat-sourced advance does not double-tick an active buff
- **WHEN** a `poisoned` combatant's fight is resolved via `run_round()` for `N` rounds (each round
  already calling `tick_buffs()` once per change 9's own upkeep), and the resulting `total_seconds` is
  then passed to `WorldClock.advance(total_seconds, AdvanceSource.COMBAT, entities)`
- **THEN** the combatant's `hp` reflects exactly `N` poison ticks' worth of damage, not `2N`

#### Scenario: A combat-sourced advance still applies gauge regen
- **WHEN** `advance(seconds, AdvanceSource.COMBAT, entities)` is called
- **THEN** every entity in `entities`' `hp`/`mp`/`sp` gauges reflect regen for the full `seconds`
  elapsed, unaffected by the `AdvanceSource.COMBAT` gate

#### Scenario: A combat-sourced advance performs no practice settlement
- **WHEN** `advance(seconds, AdvanceSource.COMBAT, entities)` is called for an entity carrying
  a declared-practice booking that would settle under `AdvanceSource.SKIP`
- **THEN** no `skill_proficiency` or other practice state changes as a result of the call, and the
  booking survives untouched for the actor's next SKIP-sourced advance

#### Scenario: A command- or skip-sourced advance runs the full stage list
- **WHEN** `advance(seconds, AdvanceSource.COMMAND, entities)` or `advance(seconds,
  AdvanceSource.SKIP, entities)` is called
- **THEN** `buff_ticks` and `sexual_decay` both run for every entity in `entities`, unlike the
  `AdvanceSource.COMBAT` case

### Requirement: Long jumps settle in quanta, not per-second steps, with an early exit once nothing
remains to settle
`world/rules/clock.py` SHALL derive `SETTLEMENT_QUANTUM_SECONDS` as the greatest common divisor of
every currently-configured buff `tick_interval` (change 6's `buffs.yaml`) and sexual-decay
`interval_seconds` (change 7's `DECAY_CONFIG`), and SHALL invoke `tick_buffs()`/`decay_tick()` once per
quantum rather than once per second. Immediately after each `decay_tick()` call within this loop, the
settlement SHALL also call `world.rules.sexual_state.climax_settlement_action(entity)` and, when it
returns `"extend"` or `"end"`, SHALL emit the correspondingly named event through
`world.rules.sexual_transitions.apply_event()`. The settlement loop SHALL stop iterating quanta, for a
given `advance()` call, the moment no entity in scope has an active buff, a sexual field above its
configured floor, **or a `climax_phase` of `進行中`** — an entity mid-climax always counts as needing
further settlement regardless of every other field's floor state — and SHALL additionally stop at a
configured defensive cap (`MAX_SETTLEMENT_QUANTA`) regardless of remaining work.

Any final partial quantum from a command or combat-adjacent duration SHALL still be passed to the
per-entity accumulators once. It is never discarded merely because it is smaller than the quantum.

#### Scenario: An 8-hour skip with no active buffs or elevated sexual state exits before a quantum
- **WHEN** `advance(28800, AdvanceSource.SKIP, entities)` is called for an entity with no active buffs
  and every sexual field already at its vocabulary floor
- **THEN** neither `tick_buffs()` nor `decay_tick()` is called, because there is no work to settle and
  the loop exits before its first quantum

#### Scenario: A short-lived buff ticks correctly through its own duration, then the loop exits early
- **WHEN** `advance(28800, AdvanceSource.SKIP, entities)` is called for an entity with a `poisoned`
  buff (duration 300 seconds) active at the start
- **THEN** `tick_buffs()`/`decay_tick()` are called enough times to cover the buff's own 300-second
  duration at the derived quantum size, and no further quanta are processed once the buff has expired
  and every sexual field is at its floor

#### Scenario: A six-second command preserves partial elapsed time
- **WHEN** two command-sourced advances of six seconds each occur while settlement work is active
- **THEN** both six-second portions reach buff and sexual-state accumulators; no elapsed game seconds are
  lost because they are smaller than the ten-second quantum

#### Scenario: A non-positive configured interval fails loudly at startup
- **WHEN** a future `buffs.yaml` or `DECAY_CONFIG` entry declares a non-positive `tick_interval` or
  `interval_seconds`
- **THEN** a startup assertion raises, naming the offending interval rather than creating an invalid
  quantum loop

#### Scenario: An entity in 進行中 keeps the loop iterating even after every other field reaches its floor
- **WHEN** `advance(28800, AdvanceSource.SKIP, entities)` is called for an entity whose `climax_phase`
  is `進行中` and whose every other `DECAY_CONFIG`-tracked field has already reached its floor
- **THEN** the settlement loop does not exit early on that account — it continues until
  `climax_settlement_action()` resolves the entity out of `進行中` (or the defensive quantum cap is
  reached)

#### Scenario: An entity in 進行中 with no other settlement work still receives climax settlement on the remainder branch
- **WHEN** `advance()` is called with an elapsed duration shorter than one quantum for an entity whose
  `climax_phase` is `進行中` and whose every other field is at its floor
- **THEN** the remainder branch still calls `decay_tick()` and `climax_settlement_action()` for that
  entity, because `climax_phase == 進行中` alone satisfies the settlement-work check gating that branch

### Requirement: Gauge and buff elapsed time is deterministic
The clock change SHALL disable the stock GaugeTrait wall-clock timer and SHALL make rulebook buff
expiration and tick accumulation consume explicit elapsed game seconds. Reading a gauge or buff outside
an `advance()` or combat round SHALL NOT advance it.

Timed rulebook buffs SHALL use an indefinitely-lived Evennia handler entry and persist their remaining
game seconds separately, so the handler cannot schedule real-time cleanup.

#### Scenario: Real time passing does not regenerate or expire game state
- **WHEN** a gauge has a positive regen rate or a timed buff is active, and no deterministic settlement
  receives elapsed seconds
- **THEN** reading the gauge or active-buff query leaves its state unchanged

#### Scenario: A permanently active fixture is bounded by the defensive quantum cap
- **WHEN** every entity in scope has continuously active settlement work for longer than
  `MAX_SETTLEMENT_QUANTA` quanta
- **THEN** the settlement loop stops at exactly `MAX_SETTLEMENT_QUANTA` iterations, and `advance()`
  still completes (calendar advance, gauge regen, practice settlement, and boundary stages are
  unaffected by this cap)

#### Scenario: Practice settlement never participates in the quantum loop
- **WHEN** `advance(28800, AdvanceSource.SKIP, entities)` is called
- **THEN** the `practice_settlement` stage is called exactly once with the full elapsed value
  regardless of `SETTLEMENT_QUANTUM_SECONDS` — it is never chunked into quanta the way
  `tick_buffs()`/`decay_tick()` are — and accrues `completed_whole_hours ×
PRACTICE_XP_PER_STUDY_HOUR` scaled by learning, affinity, and `growth_rate_multiplier`, once per
  entity per advance, SKIP-source only, saturating at the skill's derived tip cap and writing
  nothing when the actor's booking has been consumed or never existed. A successful SKIP advance
  of fewer than 3600 seconds consumes any booking while growing nothing (whole-hour closed form),
  and a COMMAND-source advance leaves the booking unconsumed for the actor's next SKIP advance.
  Settlement is per-entity against each entity's OWN booking — the design §11 batch note's
  contract that every member's growth comes only from that member's own declared command; the
  only production SKIP callers supply a single-entity scope, and every unlabeled skip path
  clears stale bookings before advancing (see `time-skip-commands`)

### Requirement: Hourly and daily boundary stages fire by tick-boundary arithmetic, never by iterating
every second or quantum
`world/rules/clock.py` SHALL detect a day boundary crossing (and any future hour-boundary-driven stage)
by comparing `start_tick // period` against `end_tick // period` directly, and SHALL NOT iterate
through every second or settlement quantum between `start_tick` and `end_tick` to detect boundary
crossings.

#### Scenario: A single day-boundary crossing triggers exactly one daily reset
- **WHEN** `advance()` is called with a `seconds` value that carries `tick` across exactly one midnight
  boundary
- **THEN** `reset_daily_counters()` is invoked exactly once for each entity in scope

#### Scenario: Multiple day-boundary crossings in one call trigger one reset per boundary
- **WHEN** `advance()` is called with a `seconds` value that carries `tick` across three midnight
  boundaries in a single call
- **THEN** `reset_daily_counters()` is invoked exactly three times per entity in scope, computed by
  direct tick-boundary arithmetic, not by iterating every intervening second

#### Scenario: No day-boundary crossing produces no daily reset
- **WHEN** `advance()` is called with a `seconds` value too small to cross a midnight boundary
- **THEN** `reset_daily_counters()` is not invoked

### Requirement: caravan_arrivals, shop_hours, quest_deadlines, and npc_schedules are declared,
registrable, no-op seams

`world/rules/clock.py` SHALL provide `register_event_source(kind, source)` as the only sanctioned
way to attach a boundary-crossing event query for `caravan_arrivals`, `shop_hours`,
`quest_deadlines`, or `npc_schedules`. When no source is registered for a given `kind`, `advance()`
SHALL treat that stage as producing zero events — never raising, never blocking the rest of
settlement. As of the `npc-schedule-runtime` change, `npc_schedules` SHALL have exactly one
registered source, `settle_npc_schedules`, supplied by `world/rules/npc_schedules.py`.

#### Scenario: An unregistered world-event stage produces no events and does not fail
- **WHEN** `advance()` is called with no source registered for `caravan_arrivals`,
  `shop_hours`, or `quest_deadlines` in the test-isolated clock registry
- **THEN** the call completes successfully and the returned event list contains no entries for any
  of those three kinds

#### Scenario: The npc_schedules stage runs its registered source
- **WHEN** `advance()` crosses a boundary where `settle_npc_schedules` reports a due event
- **THEN** the returned `ScheduledEvent` list includes that event at the `npc_schedules` stage
  position

#### Scenario: A registered synthetic source's events are returned in the correct stage position
- **WHEN** a test registers a source for a synthetic `kind` via `register_event_source()` and calls
  `advance()` across a boundary that source reports an event for
- **THEN** the returned `ScheduledEvent` list includes that source's event, proving the registry
  mechanism works without real scheduling data

### Requirement: ScheduledEvent is a plain, JSON-compatible record with no live entity references
`world/rules/clock.py` SHALL define `ScheduledEvent` as a frozen dataclass with `kind: str`,
`due_tick: int`, and `payload: dict`, following change 8's `EventEntry`/`EventLog` precedent of
key-only, serializable data.

#### Scenario: A ScheduledEvent contains no live object reference
- **WHEN** any `ScheduledEvent` returned by `advance()` is inspected
- **THEN** its `payload` contains only plain, JSON-compatible values — no live `LivingEntity` or
  `Battlefield` reference
