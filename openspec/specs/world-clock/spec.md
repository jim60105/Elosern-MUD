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

### Requirement: CmdCast advances the clock by the resolved action's reported time cost
`commands/action.py::CmdCast` SHALL call `WorldClock.advance(result.time_cost_seconds,
AdvanceSource.COMMAND, entities=[self.caller])` after a successful `ActionResolver.resolve()` call, and
SHALL NOT call `advance()` when the resolution was rejected.

#### Scenario: A successful cast advances the clock by its reported time cost
- **WHEN** `CmdCast` resolves a skill cast successfully with `time_cost_seconds == 6`
- **THEN** `WorldClock.tick` increases by exactly `6` as a result of that command

#### Scenario: A rejected cast does not advance the clock
- **WHEN** `CmdCast` resolves a skill cast that is rejected
- **THEN** `WorldClock.tick` is unchanged

### Requirement: move and converse command-default time costs are declared as rulebook data only
`world/rules/rulebook/clock.yaml`'s `command_defaults` mapping SHALL declare `move: 30` and
`converse: 60` (design doc §6.5's flat defaults), as data only. This change SHALL NOT add a `move` or
`converse` Evennia command.

#### Scenario: move and converse defaults are declared
- **WHEN** `rulebook/clock.yaml`'s `command_defaults` is inspected
- **THEN** it contains `move: 30` and `converse: 60`

#### Scenario: No move or converse command is added by this change
- **WHEN** `commands/` is inspected for files added by this change
- **THEN** no command named `move` or `converse` is defined in any file this change adds

sed: -e 表示式 #1，字元 2: 未預期的「,」
