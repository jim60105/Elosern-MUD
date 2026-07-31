## ADDED Requirements

### Requirement: Settlement stages run in the fixed order regen, buffs, sexual decay, magic study,
daily resets, then the four declared world-event seams
`world/rules/clock.py` SHALL define a single, ordered stage sequence — `gauge_regen`, `buff_ticks`,
`sexual_decay`, `magic_study`, `daily_resets`, `caravan_arrivals`, `shop_hours`, `quest_deadlines`,
`npc_schedules` — matching design doc §6.5's four built stages plus `magic_study` (change 11b's
`accrue_magic_study()`, inserted between `sexual_decay` and `daily_resets`), and SHALL execute every
`advance()` call's stages in this order with no configuration or call-site override capable of
changing it.

#### Scenario: The stage order is exactly the fixed sequence, including magic_study
- **WHEN** the settlement stage sequence is inspected
- **THEN** it is exactly `("gauge_regen", "buff_ticks", "sexual_decay", "magic_study", "daily_resets",
  "caravan_arrivals", "shop_hours", "quest_deadlines", "npc_schedules")`, in that order, with no
  duplicate or missing entry

#### Scenario: Transposing any of the four ordered stages is mechanically detected
- **WHEN** a test asserts `"buff_ticks"` appears strictly before `"sexual_decay"` and strictly after
  `"gauge_regen"` in the stage sequence, and `"magic_study"` appears strictly between `"sexual_decay"`
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

#### Scenario: No arithmetic transposition proof exists for magic_study, because it shares no
resource with its neighbors
- **WHEN** `magic_study`'s data dependencies are inspected (reads `entity.race`,
  `entity.skills.owned_keys()`, `entity.buffs`; writes only `entity.db.magic_xp`/
  `entity.traits.magic_level`) against `sexual_decay`'s (`entity.sexual`'s ordered-level fields) and
  `daily_resets`'s (`entity.sexual.climax_today` only)
- **THEN** no field is written by both `magic_study` and either neighbor, so the structural check above
  is `magic_study`'s only mechanical safeguard against transposition — this is a verified property, not
  an unexamined gap

### Requirement: buff_ticks, sexual_decay, and magic_study are skipped for combat-sourced advances
`world/rules/clock.py`'s settlement stage runner SHALL skip the `buff_ticks`, `sexual_decay`, and
`magic_study` stages entirely when `advance()` is called with `AdvanceSource.COMBAT`: `buff_ticks` and
`sexual_decay` because change 9's `run_round()` already applies both once per round as part of combat's
own per-round upkeep; `magic_study` because ambient study is a downtime concept that must never accrue
during a fight. Every other stage (`gauge_regen`, `daily_resets`, and the four declared world-event
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

#### Scenario: A combat-sourced advance does not accrue magic study XP
- **WHEN** `advance(seconds, AdvanceSource.COMBAT, entities)` is called for an entity that would
  otherwise accrue magic-study XP under `AdvanceSource.SKIP`
- **THEN** `entity.db.magic_xp` is unchanged by the call

#### Scenario: A command- or skip-sourced advance runs the full stage list
- **WHEN** `advance(seconds, AdvanceSource.COMMAND, entities)` or `advance(seconds,
  AdvanceSource.SKIP, entities)` is called
- **THEN** `buff_ticks` and `sexual_decay` both run for every entity in `entities`, unlike the
  `AdvanceSource.COMBAT` case

### Requirement: magic_study is invoked through a self-arming lazy import, and its own internal
AdvanceSource.SKIP gate composes with, rather than duplicates, the stage-level gate
`world/rules/clock.py` SHALL invoke `world.rules.progression.accrue_magic_study()` (change 11b) through
a lazy import that degrades to a silent no-op while that module does not exist, and self-arms once it
does — mirroring change 9's own `_try_sexual_decay()` treatment of `world.rules.sexual_transitions`
(change 7b) — since change 11b depends on this change and not the reverse. The stage-level gate
(`source is not AdvanceSource.COMBAT`) SHALL be the sole authority for whether this stage is invoked at
all; `accrue_magic_study()`'s own internal gate (`source is not AdvanceSource.SKIP`) SHALL be the sole
authority for whether it does anything once invoked. Neither gate SHALL be modified to duplicate the
other's condition.

#### Scenario: magic_study is a silent no-op before change 11b exists
- **WHEN** `advance()` is called (with any `AdvanceSource`) while `world.rules.progression` is not
  importable
- **THEN** the call completes successfully with no exception raised, and no entity's `magic_xp`/
  `magic_level` changes as a result

#### Scenario: magic_study self-arms once change 11b's module exists
- **WHEN** `advance(seconds, AdvanceSource.SKIP, entities)` is called once `world.rules.progression.
  accrue_magic_study` is importable
- **THEN** it is called with exactly the `entities`, `seconds`, and `source` `advance()` received

#### Scenario: A command-sourced advance invokes the stage but its internal gate no-ops
- **WHEN** `advance(seconds, AdvanceSource.COMMAND, entities)` is called once `world.rules.progression`
  exists
- **THEN** the stage-level gate lets `accrue_magic_study()` be called (it is not `AdvanceSource.COMBAT`),
  but no entity's `magic_xp` changes, because `accrue_magic_study()`'s own internal gate no-ops for any
  source other than `AdvanceSource.SKIP` — proving the two gates compose without contradiction

### Requirement: Long jumps settle in quanta, not per-second steps, with an early exit once nothing
remains to settle
`world/rules/clock.py` SHALL derive `SETTLEMENT_QUANTUM_SECONDS` as the greatest common divisor of
every currently-configured buff `tick_interval` (change 6's `buffs.yaml`) and sexual-decay
`interval_seconds` (change 7's `DECAY_CONFIG`), and SHALL invoke `tick_buffs()`/`decay_tick()` once per
quantum rather than once per second. The settlement loop SHALL stop iterating quanta, for a given
`advance()` call, the moment no entity in scope has an active buff or a sexual field above its
configured floor, and SHALL additionally stop at a configured defensive cap
(`MAX_SETTLEMENT_QUANTA`) regardless of remaining work.

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
  still completes (calendar advance, gauge regen, magic study, and boundary stages are unaffected by
  this cap)

#### Scenario: magic_study is closed-form and never participates in the quantum loop
- **WHEN** `advance(28800, AdvanceSource.SKIP, entities)` is called
- **THEN** `accrue_magic_study()` (once change 11b's module exists) is called exactly once, with the
  full `28800`-second value, regardless of `SETTLEMENT_QUANTUM_SECONDS` — never chunked into quanta
  the way `tick_buffs()`/`decay_tick()` are

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
