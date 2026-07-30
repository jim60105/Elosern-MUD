## ADDED Requirements

### Requirement: Settlement stages run in the fixed order regen, buffs, sexual decay, daily resets,
then the four declared world-event seams
`world/rules/clock.py` SHALL define a single, ordered stage sequence — `gauge_regen`, `buff_ticks`,
`sexual_decay`, `daily_resets`, `caravan_arrivals`, `shop_hours`, `quest_deadlines`, `npc_schedules` —
matching design doc §6.5 exactly, and SHALL execute every `advance()` call's stages in this order with
no configuration or call-site override capable of changing it.

#### Scenario: The stage order is exactly design doc §6.5's sequence
- **WHEN** the settlement stage sequence is inspected
- **THEN** it is exactly `("gauge_regen", "buff_ticks", "sexual_decay", "daily_resets",
  "caravan_arrivals", "shop_hours", "quest_deadlines", "npc_schedules")`, in that order, with no
  duplicate or missing entry

#### Scenario: Transposing two stages is mechanically detected
- **WHEN** a test asserts `"buff_ticks"` appears strictly before `"sexual_decay"` and strictly after
  `"gauge_regen"` in the stage sequence, and `"daily_resets"` appears strictly after `"sexual_decay"`
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

### Requirement: buff_ticks and sexual_decay are skipped for combat-sourced advances
`world/rules/clock.py`'s settlement stage runner SHALL skip the `buff_ticks` and `sexual_decay` stages
entirely when `advance()` is called with `AdvanceSource.COMBAT`, since change 9's `run_round()` already
applies both once per round as part of combat's own per-round upkeep. Every other stage
(`gauge_regen`, `daily_resets`, and the four declared world-event stages) SHALL run regardless of
`AdvanceSource`.

#### Scenario: A combat-sourced advance does not double-tick an active buff
- **WHEN** a `poisoned` combatant's fight is resolved via `run_round()` for `N` rounds (each round
  already calling `tick_buffs()` once per change 9's own upkeep), and the resulting `total_seconds` is
  then passed to `WorldClock.advance(total_seconds, AdvanceSource.COMBAT, entities)`
- **THEN** the combatant's `hp` reflects exactly `N` poison ticks' worth of damage, not `2N`

#### Scenario: A combat-sourced advance still applies gauge regen
- **WHEN** `advance(seconds, AdvanceSource.COMBAT, entities)` is called
- **THEN** every entity in `entities`' `hp`/`mp`/`sp` gauges reflect regen for the full `seconds`
  elapsed, unaffected by the `AdvanceSource.COMBAT` gate

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
quantum rather than once per second. The settlement loop SHALL stop iterating quanta, for a given
`advance()` call, the moment no entity in scope has an active buff or a sexual field above its
configured floor, and SHALL additionally stop at a configured defensive cap
(`MAX_SETTLEMENT_QUANTA`) regardless of remaining work.

#### Scenario: An 8-hour skip with no active buffs or elevated sexual state settles in one quantum
- **WHEN** `advance(28800, AdvanceSource.SKIP, entities)` is called for an entity with no active buffs
  and every sexual field already at its vocabulary floor
- **THEN** `tick_buffs()`/`decay_tick()` are each called exactly once (the check-and-exit quantum), not
  2,880 times

#### Scenario: A short-lived buff ticks correctly through its own duration, then the loop exits early
- **WHEN** `advance(28800, AdvanceSource.SKIP, entities)` is called for an entity with a `poisoned`
  buff (duration 300 seconds) active at the start
- **THEN** `tick_buffs()`/`decay_tick()` are called enough times to cover the buff's own 300-second
  duration at the derived quantum size, and no further quanta are processed once the buff has expired
  and every sexual field is at its floor

#### Scenario: Adding an interval not divisible by the derived quantum fails loudly at startup
- **WHEN** a future `buffs.yaml` or `DECAY_CONFIG` entry declares a `tick_interval`/`interval_seconds`
  not evenly divisible by the currently-derived `SETTLEMENT_QUANTUM_SECONDS`
- **THEN** a startup assertion raises, naming the offending interval, rather than silently misaligning
  future accumulator crossings

#### Scenario: A permanently active fixture is bounded by the defensive quantum cap
- **WHEN** every entity in scope has continuously active settlement work for longer than
  `MAX_SETTLEMENT_QUANTA` quanta
- **THEN** the settlement loop stops at exactly `MAX_SETTLEMENT_QUANTA` iterations, and `advance()`
  still completes (calendar advance, gauge regen, and boundary stages are unaffected by this cap)

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
`world/rules/clock.py` SHALL provide `register_event_source(kind, source)` as the only sanctioned way
to attach a boundary-crossing event query for `caravan_arrivals`, `shop_hours`, `quest_deadlines`, or
`npc_schedules`. When no source is registered for a given `kind`, `advance()` SHALL treat that stage as
producing zero events — never raising, never blocking the rest of settlement.

#### Scenario: An unregistered world-event stage produces no events and does not fail
- **WHEN** `advance()` is called before any change registers a source for `caravan_arrivals`,
  `shop_hours`, `quest_deadlines`, or `npc_schedules`
- **THEN** the call completes successfully and the returned event list contains no entries for any of
  those four kinds

#### Scenario: A registered synthetic source's events are returned in the correct stage position
- **WHEN** a test registers a source for a synthetic `kind` via `register_event_source()` and calls
  `advance()` across a boundary that source reports an event for
- **THEN** the returned `ScheduledEvent` list includes that source's event, proving the registry
  mechanism works without any of changes 15/16/19's real scheduling data existing

### Requirement: ScheduledEvent is a plain, JSON-compatible record with no live entity references
`world/rules/clock.py` SHALL define `ScheduledEvent` as a frozen dataclass with `kind: str`,
`due_tick: int`, and `payload: dict`, following change 8's `EventEntry`/`EventLog` precedent of
key-only, serializable data.

#### Scenario: A ScheduledEvent contains no live object reference
- **WHEN** any `ScheduledEvent` returned by `advance()` is inspected
- **THEN** its `payload` contains only plain, JSON-compatible values — no live `LivingEntity` or
  `Battlefield` reference
