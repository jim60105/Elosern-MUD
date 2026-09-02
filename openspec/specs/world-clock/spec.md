## Purpose

Define the persistent, deterministic game clock, calendar, and sanctioned clock-advance call sites.

## Requirements


### Requirement: WorldClock persists exactly one integer; every calendar field is derived from it
`world/rules/clock.py` SHALL provide `WorldClock` with a single persisted field, `tick: int` (total
elapsed game-seconds since epoch), and a `calendar` property returning a `WorldDateTime` computed
entirely as a pure function of `tick`. No other field of `WorldClock` or `WorldDateTime` SHALL be
independently persisted or mutated outside of `tick` changing.

#### Scenario: calendar is fully determined by tick
- **WHEN** two `WorldClock` instances are constructed with the identical `tick` value
- **THEN** their `calendar` properties are equal in every field (`year`, `season_index`,
  `day_in_season`, `hour`, `minute`, `second`)

#### Scenario: No calendar field is stored independently of tick
- **WHEN** `world/rules/clock.py` is inspected
- **THEN** `WorldDateTime` has no constructor path or setter that assigns any of its fields except
  through `WorldDateTime.from_tick(tick)`, and `WorldClock` has no attribute other than `tick` that
  changes as a side effect of anything but `advance()`

### Requirement: The calendar is a subtropical, four-mild-season year with no invented month names
`world/rules/rulebook/clock.yaml` SHALL declare `seconds_per_hour: 3600`, `hours_per_day: 24`,
`days_per_season: 90`, `seasons_per_year: 4`, and `season_names` naming exactly four seasons (春季/
夏季/秋季/冬季), matching `world_info.md`'s "四季分明但溫和宜居." `WorldDateTime` SHALL expose `year`,
`season_index` (0-3), `day_in_season` (1-90), `hour` (0-23), `minute`, and `second` — no month, week,
or other calendar granularity SHALL be introduced.

#### Scenario: A tick of zero is the first day of the first season of year zero
- **WHEN** `WorldDateTime.from_tick(0)` is computed
- **THEN** it returns `year=0`, `season_index=0`, `day_in_season=1`, `hour=0`, `minute=0`, `second=0`

#### Scenario: A tick crossing exactly one day advances day_in_season by one
- **WHEN** `WorldDateTime.from_tick(86400)` is computed
- **THEN** it returns `day_in_season=2` with every other field unchanged from tick zero's date

#### Scenario: A tick crossing 90 days advances the season, not just the day count
- **WHEN** `WorldDateTime.from_tick(86400 * 90)` is computed
- **THEN** it returns `season_index=1` (夏季) and `day_in_season=1`

#### Scenario: A tick crossing 360 days advances the year
- **WHEN** `WorldDateTime.from_tick(86400 * 360)` is computed
- **THEN** it returns `year=1`, `season_index=0`, `day_in_season=1`

#### Scenario: Named dayparts resolve to fixed hours
- **WHEN** `rulebook/clock.yaml`'s `dayparts` mapping is inspected
- **THEN** it declares `midnight: 0`, `dawn: 6`, `noon: 12`, `dusk: 18`, with no additional
  finer-grained time unit (week, month) declared anywhere in the calendar configuration

### Requirement: tick is persisted via a non-repeating Script used purely as an attribute container
`WorldClock.tick` SHALL be persisted through an Evennia `Script` (`WorldClockScript`) created with
`interval=0` and no overridden `at_repeat()` method. This Script SHALL NOT fire on any wall-clock
schedule; its sole purpose SHALL be surviving a server restart via ordinary Attribute persistence.

#### Scenario: The clock script is created with ticking disabled
- **WHEN** `WorldClockScript` is created via `evennia.create_script`
- **THEN** it is created with `interval=0` and `repeats=0`

#### Scenario: No wall-clock read exists anywhere in this change's code
- **WHEN** `world/rules/clock.py`, `world/rules/skip_safety.py`, and `commands/skip.py` are scanned for
  the literal tokens `datetime.now`, `time.time`, `utcnow`, and `at_repeat`
- **THEN** none of the tokens appear in any of these files

#### Scenario: The script never overrides at_repeat
- **WHEN** `WorldClockScript`'s class body is inspected
- **THEN** it defines no `at_repeat` method

### Requirement: advance() settles exactly the entities its caller supplies, never a global registry
`WorldClock.advance(seconds, source, entities)` SHALL apply the per-entity settlement stages (gauge
regen; buff ticks and sexual decay, subject to the `AdvanceSource` gate) only to the `entities`
iterable the caller supplies. `advance()` SHALL NOT query any global entity registry, database-wide
scan, or `evennia`-wide object search to discover additional entities to settle.

#### Scenario: Only the supplied entities are settled
- **WHEN** `advance()` is called with `entities=[actor]`, and a different `LivingEntity` exists
  elsewhere in the database with an active buff
- **THEN** that other entity's buff state is unchanged after the call — only `actor`'s state reflects
  settlement

#### Scenario: The registered call sites pass their documented scopes
- **WHEN** `CmdCast`'s integration and the skip commands call `advance()`
- **THEN** each passes `entities=[caller]`; `settle_combat_result()` passes
  `entities=battlefield.roster.values()`

### Requirement: gauge regen is a closed-form computation, never a per-second or per-quantum loop
`world/rules/clock.py` SHALL compute HP/MP/SP regen for a settled entity as
`min(max, current + rate * elapsed_seconds)`, applied once per `advance()` call per entity, regardless
of how large `elapsed_seconds` is. This computation SHALL read `elapsed_seconds` from the `advance()`
call's own argument, never from any wall-clock-timestamp-based mechanism the underlying `GaugeTrait`
implementation might provide.

#### Scenario: A large elapsed_seconds value is applied in one step
- **WHEN** `advance()` is called with `seconds=28800` (8 hours) for an entity whose `hp` gauge has
  `rate=2` per second and is below max
- **THEN** the entity's `hp` reflects `min(max, current + 2 * 28800)` after exactly one regen
  computation, not 28,800 individual one-second increments

#### Scenario: Regen never exceeds the gauge's max
- **WHEN** `elapsed_seconds * rate` would push a gauge's value past its configured `max`
- **THEN** the gauge's value is clamped to exactly `max`, never higher

### Requirement: settle_combat_result is the sanctioned call site for combat-sourced advances
`world/rules/clock.py` SHALL provide `settle_combat_result(result, entities) -> list[ScheduledEvent]`,
accepting either a `BattleResult` (change 9) or an `OverwhelmResult` (change 10) and calling
`WorldClock.advance(result.total_seconds, AdvanceSource.COMBAT, entities)`. This is a declared
integration point for a future top-level combat command that does not yet exist in this roadmap.

#### Scenario: settle_combat_result advances the clock by the reported total_seconds
- **WHEN** `settle_combat_result(result, entities)` is called with a `result.total_seconds` of `18`
- **THEN** `WorldClock.tick` increases by exactly `18`

#### Scenario: settle_combat_result always uses AdvanceSource.COMBAT
- **WHEN** `settle_combat_result()` is called with either a `BattleResult` or an `OverwhelmResult`
- **THEN** the underlying `advance()` call receives `AdvanceSource.COMBAT` in both cases

### Requirement: CmdCast advances command time only outside a persistent combat session
`commands/action.py::CmdCast` SHALL settle a successful out-of-combat `ActionResolver.resolve()` call
and its command-time charge inside one outer settlement transaction
(`world/rules/cast_settlement.settle_out_of_combat_cast`, the cast-settlement-atomicity capability):
the settlement SHALL invoke `ActionResolver.resolve()` and, only on success,
`WorldClock.advance(result.time_cost_seconds, AdvanceSource.COMMAND, entities=[self.caller])` as
nested operations inside a single outer transaction, committing only after both succeed. `CmdCast`
SHALL NOT call `WorldClock.advance()` directly, and SHALL NOT advance when the resolution is rejected.
During an active persistent combat session, CmdCast SHALL delegate the selected request to combat-
session orchestration and SHALL NOT advance command time. Completed combat rounds SHALL accumulate in
the session and advance exactly once through `settle_combat_result(..., AdvanceSource.COMBAT)` at
terminal settlement.

#### Scenario: A successful out-of-combat cast advances its reported command time
- **WHEN** CmdCast resolves an out-of-combat skill successfully with `time_cost_seconds == 6`
- **THEN** WorldClock tick increases by exactly 6 with `AdvanceSource.COMMAND`, committed together with
  the skill effect, practice award, and planner writes in the same outer transaction

#### Scenario: A rejected out-of-combat cast does not advance the clock
- **WHEN** CmdCast resolves an out-of-combat skill cast that is rejected
- **THEN** WorldClock tick is unchanged and no effect, practice, or planner write commits

#### Scenario: A failed clock settlement leaves the cast uncommitted
- **WHEN** the clock callback or the final clock persistence raises after a successful resolution of an
  out-of-combat cast (for example `status_disguise`)
- **THEN** the failure propagates and the previously committed action state is rolled back too: the
  disguise/practice surfaces equal their pre-action values and the tick is unchanged

#### Scenario: Active-session cast does not advance command time
- **WHEN** a player submits a preflight-valid cast during an active combat session
- **THEN** CmdCast performs no `AdvanceSource.COMMAND` advance, regardless of the selected skill's
  ordinary command time

#### Scenario: Rejected active-session input does not advance time
- **WHEN** combat-session preflight rejects the selected action before initiative
- **THEN** neither command nor combat time advances

#### Scenario: Terminal session settles all round time once
- **WHEN** a combat session terminates after three completed six-second rounds
- **THEN** `settle_combat_result()` advances exactly 18 seconds with `AdvanceSource.COMBAT` and no earlier
  in-session CmdCast added command time

### Requirement: move and converse command-default time costs are declared as rulebook data only
`world/rules/rulebook/clock.yaml`'s `command_defaults` mapping SHALL declare `move: 30` and
`converse: 60` (design doc §6.5's flat defaults). `move` SHALL be consumed by every successful
traversal of a `typeclasses.exits.Exit` or `typeclasses.exits.CostedXYZExit` instance by a
`PlayerCharacter`, via `world.rules.movement.charge_movement()` (the `movement-cost-charging`
capability). This change SHALL NOT add a bespoke `move` or `converse` Evennia command — Evennia's own
per-exit, auto-generated traversal commands are what invoke `at_traverse`/`at_post_traverse`, and
`converse` remains unwired, exactly as change 11 and change 13 left it.

#### Scenario: move and converse defaults are declared
- **WHEN** `rulebook/clock.yaml`'s `command_defaults` is inspected
- **THEN** it contains `move: 30` and `converse: 60`

#### Scenario: No move or converse command is added by this change
- **WHEN** `commands/` is inspected for files added by this change
- **THEN** no command named `move` or `converse` is defined in any file this change adds

#### Scenario: The move cost is consumed by ordinary exit traversal, not a bespoke command
- **WHEN** `commands/` is inspected for files added by this change, and the mechanism that invokes
  `world.rules.movement.charge_movement()` is inspected
- **THEN** no command named `move` or `converse` exists anywhere, and the cost is instead consumed
  from inside `typeclasses/exits.py::MovementCostMixin.at_post_traverse` — a hook on the exit object
  itself, fired by Evennia's own per-exit, auto-generated traversal command, not by a new command this
  change adds

#### Scenario: A successful exit traversal advances the clock by the move cost
- **WHEN** a `PlayerCharacter` successfully traverses a `typeclasses.exits.Exit` or
  `typeclasses.exits.CostedXYZExit` instance
- **THEN** `WorldClock.tick` increases by exactly `CLOCK_YAML["command_defaults"]["move"]`

#### Scenario: converse remains unconsumed
- **WHEN** `world/rules/rulebook/clock.yaml`'s `converse` value is inspected for any consumer added by
  this change
- **THEN** no code added by this change reads `command_defaults["converse"]`


### Requirement: World-clock presentation reads never create the singleton
`world/rules/clock.py` SHALL provide a read-only accessor that returns the existing `WorldClock` or absence without creating a Script or other persistent state. The deterministic server startup lifecycle SHALL explicitly ensure the world-clock singleton before player presentation is accepted. Presentation code SHALL use only the read-only accessor and SHALL NOT call the create-or-read mutation helper.

#### Scenario: Startup ensures the clock through its deterministic owner
- **WHEN** the server completes deterministic startup against a database without a world-clock Script
- **THEN** exactly one non-repeating world-clock Script exists before a player can request WebClient presentation

#### Scenario: Read accessor reports absence without writing
- **WHEN** the world-clock Script is absent and the read-only accessor is called
- **THEN** it returns absence and creates no Script, Attribute, or other persistent record

#### Scenario: Presentation does not use the create-or-read helper
- **WHEN** WebClient presentation source is inspected and a full snapshot is built with an existing clock
- **THEN** presentation calls only the read-only accessor and leaves the Script count and world tick unchanged

### Requirement: advance() persists the tick and entity state atomically
`WorldClock.advance()` SHALL settle all per-entity stages, every registered boundary stage, and the
final `tick` increment inside a single durable transaction with snapshot/restore of the touched
entity attributes **and of every durable surface any registered boundary-stage source may write
(through its declared advance-surface contract, including quest logs and room pins, merchant
components, NPC schedule state and location, instance-room state, and pruned map knowledge)**, so a
process termination or a failure inside the call can never leave character state advanced without
the matching tick (or the reverse), and no observer can see or persist an uncommitted settlement.

#### Scenario: Terminated advance leaves no partial save
- **WHEN** a process is terminated while `advance()` is running after entity writes but before the
  tick persist
- **THEN** after restart both the entity state and `world_clock.db.tick` reflect the same pre-advance
  values

#### Scenario: Successful advance commits entity state and tick together
- **WHEN** `advance()` completes normally for a caller-supplied entity
- **THEN** the entity's gauge/daily-counter changes and the increased `tick` are both durably visible
  after restart

#### Scenario: A successful advance with a due quest deadline commits the failure together with the tick
- **WHEN** `advance()` completes normally while a player's in-progress quest deadline falls inside
  the window and all writing sources ship their contracts
- **THEN** the failed quest record is durably visible in `quest_log` after restart and the tick
  increased by the full `seconds`, with no divergence between cache and storage

#### Scenario: The fixed stage order and one-day bound survive the snapshot extension
- **WHEN** the stage sequence and `MAX_ADVANCE_SECONDS` are inspected after this change
- **THEN** the stage sequence is still exactly `("gauge_regen", "buff_ticks", "sexual_decay",
  "practice_settlement", "daily_resets", "caravan_arrivals", "shop_hours", "quest_deadlines",
  "npc_schedules", "instance_reclamation")`, an oversized call still raises before any write, and
  contracts run before any stage write

### Requirement: Every registered boundary-stage source declares the durable surfaces it may write
`register_event_source(kind, source, surfaces)` SHALL accept an optional advance-surface contract: a
pure, read-only callable `(start_tick, end_tick) -> mapping[id(obj), SurfaceSnapshot]` that
re-discovers, with the same deterministic queries its settlement uses, every object the source may
write and snapshots each durable surface and any location state through the shared attribute-snapshot
helper. A source that writes durable state SHALL ship a contract; a source with no contract (`None`)
SHALL be treated as a read-only seam and SHALL not write durable state during settlement.
`WorldClock.advance` SHALL run every registered contract before opening its transaction, SHALL merge
the results with its caller-entity snapshot set by object identity, and SHALL restore every declared
surface on failure. The two-argument registration form SHALL remain valid for read-only and test
sources.

#### Scenario: A writing source without a contract is a completeness violation
- **WHEN** the registered boundary-stage sources are inspected (`caravan_arrivals`,
  `quest_deadlines`, `npc_schedules`, `instance_reclamation`)
- **THEN** each one declares a contract that snapshots the durable surfaces its settlement writes,
  and a test fails if any of these four registrations loses its contract

#### Scenario: A read-only source declares no contract and still runs
- **WHEN** `register_event_source("shop_hours", settle_shop_hours)` is registered with no contract
  and `advance()` crosses a shop-hours boundary
- **THEN** settlement still emits its events, the call succeeds, and no snapshot or restore is
  performed for shop state

#### Scenario: A synthetic two-argument source registered by a test still works
- **WHEN** a test registers `register_event_source(kind, source)` with a lambda and calls
  `advance()` across a boundary
- **THEN** the source's events are returned in the correct stage position exactly as before, with no
  contract required

#### Scenario: A contract is a pure read that never mutates state
- **WHEN** a contract snapshot function is invoked
- **THEN** it only reads attributes and locations — no attribute, trait, location, or tag value
  changes as a side effect of the snapshot

### Requirement: A rolled-back advance restores every callback-owned surface, not just caller entities
When any stage or the final clock persistence fails inside `WorldClock.advance`, the in-memory values
of every durable surface written by any registered boundary-stage source SHALL be restored to their
pre-advance values in addition to the caller-entity surfaces and the clock tick, so the process never
serves or repersists state that the rolled-back transaction never committed.

#### Scenario: A failed advance restores a discovered quest log and room pins
- **WHEN** a player has an in-progress quest whose deadline falls inside the advance window, and a
  later registered stage raises
- **THEN** after the exception the player's `db.quest_log` in the in-process object, the raw
  `quest_log` Attribute row, and every affected room's `db.pin_reasons` are all unchanged from before
  the advance, and the clock tick is unchanged

#### Scenario: A failed advance restores merchant stock and last restock day
- **WHEN** an advance crosses a merchant's restock day and a later stage or the final persist raises
- **THEN** the merchant host's cached `merchant_stock` and `last_restock_day` values and their raw
  Attribute rows both equal their pre-advance values

#### Scenario: A failed advance restores NPC schedule state and location
- **WHEN** an advance settles a due schedule occurrence that writes `schedule_state` or relocates
  the NPC, and a later stage or the final persist raises
- **THEN** the NPC's cached and stored `schedule_state` equal the pre-advance value, the NPC's
  in-memory `db_location` points back at the pre-advance room, and the source and destination rooms'
  contents caches re-read from the rolled-back database

#### Scenario: A failed advance restores instance-room state, pruned map knowledge, and relocated occupants
- **WHEN** an advance promotes or reclaims a due `InstanceRoom` (including pruning `map_knowledge`
  records and relocating unowned occupants), and a later stage or the final persist raises
- **THEN** every touched room's `expire_tick`/`named`/`interacted`/`pin_reasons`/`owned_entities`
  values and every pruned player's `map_knowledge` value, in cache and in raw Attribute rows, equal
  their pre-advance values; every relocated occupant's in-memory location points back into the
  re-fetched (rolled-back) reclaimed room rather than at a deleted object or `None`; and a room
  deleted during the failed advance is re-fetched fresh from the rolled-back database on the next
  access

### Requirement: advance() has a bounded settlement budget per call
`WorldClock.advance()` SHALL reject or reject-and-degrade any call whose elapsed seconds would exceed
a configured maximum advance duration (`MAX_ADVANCE_SECONDS`, equal to one full game day —
`seconds_per_hour * hours_per_day` from `rulebook/clock.yaml`), so the per-day boundary loop and
event accumulation are bounded per call. One full day keeps `wait until`'s worst case (a day-long
wait) legal while still bounding the loop at one day crossing per call.

#### Scenario: Oversized advance is refused without writes
- **WHEN** `advance()` is called with seconds above `MAX_ADVANCE_SECONDS`
- **THEN** the call raises a named error before any entity or tick write occurs

### Requirement: Clock advance and restore failures emit observability events

`WorldClock.advance()` SHALL emit one `clock_advance` info event through the
`world.observability` facade on successful commit, with `tick_from`,
`tick_to`, and `scope` context. Every best-effort attribute-restore failure
inside advance/rollback paths SHALL emit a `rollback_restore_failed` warn
event carrying the failed attribute `key`, the affected `obj` identity, and
the exception chain, instead of passing silently. Emitting events MUST NOT
change the atomic persistence or restore semantics.

#### Scenario: A successful advance leaves one boundary event

- **WHEN** `advance()` commits normally for a supplied scope
- **THEN** exactly one `clock_advance` event is logged with the tick range in
  context

#### Scenario: A swallowed restore failure becomes visible

- **WHEN** a restore during a rolled-back advance raises and is swallowed to
  preserve the original exception
- **THEN** a `rollback_restore_failed` warn event identifies the key, the
  object, and the exception in context, and the original exception still
  propagates unchanged
