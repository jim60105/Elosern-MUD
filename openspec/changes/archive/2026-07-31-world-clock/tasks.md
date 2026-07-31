## 1. Package layout and confirmations

- [x] 1.1 Confirm `world/rules/` holds change 6's `buffs.py` (`tick_buffs`, `entity.buffs`), change 7's
      `sexual_state.py` (`decay_tick`, `reset_daily_counters`, `DECAY_CONFIG`), change 3's
      `typeclasses/entities.py` (`Monster`, gauge traits), and change 9's `combat.py`
      (`Battlefield`, `BattleResult`, `is_battle_over`); create `world/rules/clock.py`,
      `world/rules/skip_safety.py`, `world/rules/rulebook/clock.yaml`, and `commands/skip.py` as new
      files; register the skip commands in the character command set; correct inherited gauge and buff
      wall-clock behavior so `WorldClock` is the sole elapsed-time source.
- [x] 1.2 Confirm the exact import paths and public names for `world.rules.buffs.{tick_buffs}`,
      `world.rules.sexual_state.{decay_tick, reset_daily_counters, DECAY_CONFIG}`, and
      `world.rules.combat.{Battlefield, BattleResult, is_battle_over}` against how changes 6/7/9
      actually landed — no code in this change should assume an unconfirmed symbol name before this
      step.
- [x] 1.3 Confirm change 9's `run_round()` landed implementation genuinely calls `tick_buffs()`/
      `decay_tick()` once per round as its own per-round upkeep (design.md D-3's stated precondition
      for skipping these two stages on `AdvanceSource.COMBAT`) — if it does not, revisit D-3 before
      writing the combat double-tick-avoidance tests.
- [x] 1.4 Confirm change 8's landed `commands/action.py::CmdCast` implementation and its exact
      `ActionResult.success()` shape (`event_log`, `time_cost_seconds`) before adding the integration
      line in task 8.1.
- [x] 1.5 Confirm `world.rules.progression.accrue_magic_study(entities, seconds, source)`'s exact
      signature against change 11b's landed implementation, if change 11b has landed by the time this
      task runs — this change's own `_try_accrue_magic_study()` (task 7.2) must degrade to a no-op
      rather than assume a signature that does not match, since change 11b depends on this change and
      may not exist yet at this change's own implementation time.

## 2. Rulebook data (`world/rules/rulebook/clock.yaml`)

- [x] 2.1 Author `seconds_per_hour: 3600`, `hours_per_day: 24`, `days_per_season: 90`,
      `seasons_per_year: 4`, `season_names: ["春季", "夏季", "秋季", "冬季"]`, `dayparts: {midnight: 0,
      dawn: 6, noon: 12, dusk: 18}` per design.md D-2, with an inline comment citing `world_info.md`'s
      "四季分明但溫和宜居" line as the calendar's sole lore anchor.
- [x] 2.2 Author `command_defaults: {move: 30, converse: 60, cast: 6}` per design.md D-9, with an
      inline comment stating `cast`'s value is documentation only — `CmdCast` reads
      `ActionResult.time_cost_seconds`, never this table, for its actual advance() call.
- [x] 2.3 Author `max_settlement_quanta: 4320` and `max_sleep_seconds: 43200` per design.md D-4/D-7,
      each with an inline comment marking it an invented placeholder flagged for a future balance pass
      (mirroring `combat.yaml`/`overwhelm.yaml`'s own invented-constant disclosure convention).
- [x] 2.4 Implement a small loader in `world/rules/clock.py` (`CLOCK_YAML = yaml.safe_load(...)`),
      mirroring change 9's `COMBAT_YAML` loader pattern exactly.

## 3. WorldDateTime and the calendar (`world/rules/clock.py`)

- [x] 3.1 Implement `WorldDateTime` (frozen dataclass: `year`, `season_index`, `day_in_season`,
      `hour`, `minute`, `second`) and `WorldDateTime.from_tick(tick: int) -> WorldDateTime` per
      design.md D-2's `divmod`-based derivation, reading every constant from `CLOCK_YAML`, never a
      hardcoded literal.
- [x] 3.2 Implement `WorldDateTime.season_name` reading `CLOCK_YAML["season_names"][season_index]`.
- [x] 3.3 Test: tick `0` yields `year=0, season_index=0, day_in_season=1, hour=0, minute=0, second=0`;
      tick `86400` yields `day_in_season=2` with every other field unchanged; tick `86400*90` yields
      `season_index=1, day_in_season=1`; tick `86400*360` yields `year=1, season_index=0,
      day_in_season=1`.
- [x] 3.4 Implement `seconds_until_daypart(calendar: WorldDateTime, daypart_name: str) -> int` per
      design.md D-7: raises a named error for a daypart absent from `CLOCK_YAML["dayparts"]`; computes
      seconds to the next occurrence of that hour, always strictly positive (rolls to the following
      day when the target hour is not later than the current hour-and-fraction).
- [x] 3.5 Test `seconds_until_daypart()`: a future-today daypart computes the same-day interval; a
      daypart matching or earlier than the current hour computes tomorrow's occurrence (never zero or
      negative); an unrecognized daypart name raises before any other computation runs.

## 4. WorldClock core and persistence (`world/rules/clock.py`)

- [x] 4.1 Implement `AdvanceSource` (`StrEnum`: `COMMAND`, `COMBAT`, `SKIP`).
- [x] 4.2 Implement `WorldClock` (dataclass: `tick: int`) with a `calendar` property returning
      `WorldDateTime.from_tick(self.tick)` — no other persisted field.
- [x] 4.3 Implement `WorldClockScript(DefaultScript)` per design.md D-1: `at_script_creation()` seeds
      `self.db.tick = 0`; created elsewhere with `interval=0`, `repeats=0`; no `at_repeat()` override
      anywhere in the class body. Implement the accompanying lookup helper (`get_world_clock()` /
      equivalent) that finds-or-creates the singleton `Script` by `key="world_clock"`.
- [x] 4.4 Confirm (grep-based check) that `world/rules/clock.py`, `world/rules/skip_safety.py`, and
      `commands/skip.py` contain none of the literal tokens `datetime.now`, `time.time`, `utcnow`, or
      `at_repeat`.
- [x] 4.5 Test: two `WorldClock` instances constructed with the identical `tick` produce field-for-
      field identical `calendar` properties; `WorldClockScript` is created with `interval=0` and
      `repeats=0`; the class defines no `at_repeat` method (via `hasattr`/`inspect` check against the
      class body, not the inherited default).

## 5. Gauge regen (`world/rules/clock.py`)

- [x] 5.1 Implement `_settle_gauge_regen(entities, elapsed_seconds: int) -> None` per design.md D-4:
      for each of `hp`/`mp`/`sp` on each entity, sets `.value = min(.max, .value + .rate *
      elapsed_seconds)`, writing directly through the trait's own public setter — one computation per
      entity per gauge per `advance()` call, never chunked.
- [x] 5.2 Verify the installed Evennia 6.1.0 `GaugeTrait`'s wall-clock timer and replace it with this
      change's deterministic registered gauge trait, retaining the public `GaugeTrait` surface while
      preventing `.value` reads and writes from advancing real time.
- [x] 5.3 Test: an 8-hour (`28800`) elapsed value applied to a `hp` gauge with `rate=2` below max
      updates in one computation to `min(max, current + 2*28800)`, with no per-second iteration (call-
      count or timing-based assertion that `_settle_gauge_regen()`'s cost does not scale with
      `elapsed_seconds`); regen never exceeds `max`.

## 6. Buff-tick / sexual-decay quantum loop (`world/rules/clock.py`)

- [x] 6.1 Implement `SETTLEMENT_QUANTUM_SECONDS`, computed once at import time as
      `math.gcd(*every buffs.yaml tick_interval, *every DECAY_CONFIG interval_seconds)`, per design.md
      D-4. Implement the startup assertion: raise immediately, naming the offending value, if any
      currently-configured interval is not evenly divisible by the resulting GCD.
- [x] 6.2 Implement `_has_settlement_work(entity) -> bool` per design.md D-4: `True` if
      `entity.buffs.all()` is non-empty, or if any of `entity.sexual`'s decay-configured fields
      (`arousal`, `wetness`, `shame`, `climax_phase`) is not already at its vocabulary floor level;
      `False` (never raises) if `entity.sexual` is `None`.
- [x] 6.3 Implement deterministic buff expiry/tick accumulation, then `_settle_buffs_and_decay(entities,
      elapsed_seconds: int)` per design.md D-4: it loops no more than
      `elapsed_seconds // SETTLEMENT_QUANTUM_SECONDS` times, passes the quantum to `tick_buffs()` and
      `decay_tick()` for every entity, and breaks before a no-op quantum when `_has_settlement_work()`
      is false for the entire scope; it hard-stops at `CLOCK_YAML["max_settlement_quanta"]` and passes
      any nonzero final partial quantum to the accumulators once.
- [x] 6.4 Test: a fully-settled entity (no buffs, every decay field at floor) exits before the first
      quantum for a `28800`-second call — neither per-quantum callable is invoked, so the cost is
      independent of requested duration.
- [x] 6.5 Test: an entity with a `poisoned` buff (duration 300s) active at the start of a `28800`-second
      call ticks and expires from supplied game seconds at the derived quantum size, then exits before
      the remaining no-op quanta; two six-second advances preserve both partial durations rather than
      dropping their elapsed time.
- [x] 6.6 Test the interval validation: a non-positive buff or decay interval is rejected at startup.
- [x] 6.7 Test the defensive cap: a fixture engineered so `_has_settlement_work()` never returns
      `False` (e.g. a decay field configuration that never reaches its floor) stops at exactly
      `max_settlement_quanta` iterations, and the surrounding `advance()` call still completes (calendar
      and boundary stages unaffected).

## 7. Settlement stage order and the combat double-tick gate (`world/rules/clock.py`)

- [x] 7.1 Implement `_STAGE_ORDER` as the exact tuple `("gauge_regen", "buff_ticks", "sexual_decay",
      "magic_study", "daily_resets", "caravan_arrivals", "shop_hours", "quest_deadlines",
      "npc_schedules")` per design.md D-3/§6.5 — `magic_study` is change 11b's addition, inserted
      between `sexual_decay` and `daily_resets` at the coordinator's request.
- [x] 7.2 Implement `_try_accrue_magic_study(entities, seconds, source) -> None` per design.md D-3: a
      self-arming wrapper mirroring change 9's `_try_sexual_decay()` exactly — lazily imports
      `world.rules.progression.accrue_magic_study`, degrades to a silent no-op (never a crash) while
      `world.rules.progression` does not exist, and calls it with the received `entities`/`seconds`/
      `source` once it does. Do **not** hard-`import` `world.rules.progression` at module load time —
      change 11b depends on this change, not the reverse, so a hard import would fail during this
      change's own implementation.
- [x] 7.3 Implement `_run_stages(clock, seconds, source, entities) -> list[ScheduledEvent]` per
      design.md D-3: always calls `_settle_gauge_regen()`; when `source is not AdvanceSource.COMBAT`,
      calls `_settle_buffs_and_decay()` then `_try_accrue_magic_study(entities, seconds, source)` (in
      that order, after the quantum loop completes — `magic_study` is closed-form, called once with
      the full `seconds`, never chunked); always calls `_settle_boundary_stages()` (task 9).
- [x] 7.4 Test the structural transposition check: assert `"buff_ticks"` appears strictly between
      `"gauge_regen"` and `"sexual_decay"` in `_STAGE_ORDER`, and `"magic_study"` appears strictly
      between `"sexual_decay"` and `"daily_resets"` — a test that fails immediately if `_STAGE_ORDER`
      is ever edited to violate either constraint.
- [x] 7.5 Test the arithmetic transposition check per design.md D-3's worked shape: construct a
      fixture entity whose `hp` starts within one regen-step of `max`, with an active `poisoned` buff;
      settle it once through the real, correctly-ordered `_run_stages()` and once through a
      deliberately-transposed variant (buff-tick applied before regen) built in the same test; assert
      the two final `hp` values differ, and assert the correctly-ordered result matches the specific
      value design.md D-3's worked arithmetic predicts for the chosen fixture numbers. Do **not**
      attempt to extend this arithmetic proof to `magic_study` — design.md D-3 documents explicitly why
      no such proof exists (no shared resource with either neighbor); the structural check (task 7.4)
      is `magic_study`'s only mechanical safeguard, and that is the correct, complete answer, not a gap
      to fill in later.
- [x] 7.6 Test the combat double-tick gate: simulate an `N`-round `run_round()` sequence for a
      `poisoned` combatant (each round already calling `tick_buffs()`/`decay_tick()` per change 9's own
      upkeep), then call `advance(N*6, AdvanceSource.COMBAT, entities)`; assert the combatant's `hp`
      reflects exactly `N` poison ticks' worth of damage, not `2N`.
- [x] 7.7 Test that `AdvanceSource.COMBAT` still applies gauge regen (task 5's stage runs regardless of
      source), that it never accrues magic-study XP (`entity.db.magic_xp` unchanged), and that
      `AdvanceSource.COMMAND`/`AdvanceSource.SKIP` both run the full stage list including
      `buff_ticks`/`sexual_decay`.
- [x] 7.8 Test `_try_accrue_magic_study()`'s self-arming behavior directly: (a) while
      `world.rules.progression` is not importable, `advance()` (any `AdvanceSource`) completes with no
      exception and no entity's `magic_xp`/`magic_level` changes; (b) once a stand-in
      `world.rules.progression.accrue_magic_study` exists (a test fixture, or the real module once
      change 11b lands), `advance(seconds, AdvanceSource.SKIP, entities)` calls it with exactly the
      received `entities`/`seconds`/`source`.
- [x] 7.9 Test the two-gate composition explicitly: with the stand-in `accrue_magic_study` from task
      7.8 in place, call `advance(seconds, AdvanceSource.COMMAND, entities)` and assert the stand-in
      *is* invoked (the stage-level gate only excludes `COMBAT`) but produces no XP change (the
      stand-in's own internal `source is not AdvanceSource.SKIP: return` gate no-ops) — proving the
      stage-level gate and `accrue_magic_study()`'s own internal gate compose rather than contradict,
      per design.md D-3's stated division of authority.

## 8. Boundary stages and the ScheduledEvent registry (`world/rules/clock.py`)

- [x] 8.1 Implement `ScheduledEvent` (frozen dataclass: `kind: str`, `due_tick: int`, `payload: dict`)
      per design.md D-5, matching change 8's `EventEntry` key-only, JSON-compatible discipline.
- [x] 8.2 Implement `register_event_source(kind: str, source: Callable[[int, int], list[
      ScheduledEvent]]) -> None` and the internal `_EVENT_SOURCES` registry.
- [x] 8.3 Implement `_settle_boundary_stages(start_tick, end_tick) -> list[ScheduledEvent]` per
      design.md D-5: detects a day-boundary crossing via `start_tick // 86400 != end_tick // 86400`
      (calling `reset_daily_counters(entity)` for every entity in scope once per boundary crossed, via
      direct integer-division arithmetic on the *number* of boundaries crossed, never by iteration);
      then, for each of `caravan_arrivals`/`shop_hours`/`quest_deadlines`/`npc_schedules`, calls the
      registered source if present, else contributes zero events.
- [x] 8.4 Test: a single day-boundary crossing calls `reset_daily_counters()` exactly once per entity;
      three boundary crossings in one call trigger exactly three calls per entity, computed by direct
      arithmetic (assert via a timing/complexity-independent check, e.g. mock call-count, not by
      inspecting iteration internals); no crossing triggers zero calls.
- [x] 8.5 Test: before any `register_event_source()` call, `advance()` completes successfully with zero
      events for all four declared-seam kinds; after registering a synthetic source for
      `caravan_arrivals`, its `ScheduledEvent`s appear in `advance()`'s returned list when a boundary it
      reports for is crossed.
- [x] 8.6 Test `ScheduledEvent.payload` contains no live entity/`Battlefield` reference for any event
      this change itself produces (the `daily_reset`-kind event).

## 9. advance() itself (`world/rules/clock.py`)

- [x] 9.1 Implement `WorldClock.advance(seconds: int, source: AdvanceSource, entities: Iterable[
      "LivingEntity"]) -> list[ScheduledEvent]`: captures `start_tick`, calls `_run_stages()` with the
      current tick's boundary information, increments `self.tick += seconds`, returns the accumulated
      `ScheduledEvent` list. Never queries a global entity registry — `entities` is exactly what the
      caller passed.
- [x] 9.2 Test: `advance()` only mutates state for entities in the supplied `entities` iterable — a
      separately-constructed `LivingEntity` with an active buff, not passed in, is unaffected.
- [x] 9.3 Test reproducibility (hard requirement 4): construct two independent `WorldClock` + entity-
      state snapshots with identical starting `tick` and identical entity attribute values; call
      `advance()` with the same `seconds`/`source`/equivalent entities on both; assert the resulting
      `tick`, every settled entity's `traits`/`buffs`/`sexual` state, and the returned `ScheduledEvent`
      list are bitwise/structurally identical between the two runs.
- [x] 9.4 Test a serialize-reload-replay cycle: capture `(tick, entity attribute values)`, "reload" by
      reconstructing fresh `WorldClock`/entity objects from those captured values, call `advance()` with
      the same arguments as an unreloaded control run, and assert identical outcomes — proving a save
      genuinely reproduces the same world, not merely that two in-memory objects match.

## 10. settle_combat_result() and CmdCast integration

- [x] 10.1 Implement `settle_combat_result(result, entities) -> list[ScheduledEvent]` per design.md
      D-10: obtains the persistent world clock and calls `advance(result.total_seconds,
      AdvanceSource.COMBAT, entities)`, accepting either a `BattleResult` or an `OverwhelmResult`.
- [x] 10.2 Test `settle_combat_result()` with a synthetic `BattleResult`/`OverwhelmResult` (a minimal
      stand-in exposing only `total_seconds`, not a full combat run) advances `tick` by exactly
      `total_seconds` and always uses `AdvanceSource.COMBAT`.
- [x] 10.3 Edit `commands/action.py::CmdCast` (change 8's already-landed implementation file — not its
      OpenSpec artifacts) to obtain the persistent world clock and call `advance(result.time_cost_seconds,
      AdvanceSource.COMMAND, entities=[self.caller])` immediately after a successful `resolve()`, before
      rendering. No call on a rejected outcome.
- [x] 10.4 Test: a successful `CmdCast` invocation advances `tick` by exactly the resolved
      `time_cost_seconds`; a rejected invocation leaves `tick` unchanged.
- [x] 10.5 Confirm (via `git diff`) that this task's edit to `commands/action.py` is the only change to
      any file authored by change 8, and that none of change 8's own OpenSpec artifacts
      (`proposal.md`/`design.md`/`specs/`/`tasks.md`) are touched.

## 11. Skip safety gate (`world/rules/skip_safety.py`)

- [x] 11.1 Implement `SkipRejectReason` (`StrEnum`: `IN_COMBAT`, `HOSTILE_PRESENT` — exactly two
      values) — a plain enumeration with no associated partial-duration field, per design.md D-6. Do
      **not** add a third value keyed to `battlefield.fled`; design.md D-6 documents why that proxy was
      considered and rejected (it records disengagement, not danger).
- [x] 11.2 Implement `evaluate_skip_safety(actor) -> SkipRejectReason | None` per design.md D-6: checks,
      in order, whether `actor` is a living, non-fled member of a `Battlefield` whose `is_battle_over()`
      is `False` (`IN_COMBAT`); whether any living (`hp.value > 0`) `Monster` shares `actor.location`
      (`HOSTILE_PRESENT`); returns `None` if neither applies. `battlefield.fled` is read only inside the
      `IN_COMBAT` check's own exclusion of fled members — never as an independent condition.
- [x] 11.3 Implement (or document, per design.md's Open Questions) `_active_battlefield_for(actor)` as
      a caller-injectable lookup — the mechanism a future combat-command change threads through, since
      no canonical "which battlefield is this actor in" registry exists yet. A minimal, test-only
      implementation (e.g. an explicit parameter or a simple in-memory map keyed by actor) is
      sufficient for this change's own tests; do not invent a persistent, ORM-backed registry beyond
      what the tests need.
- [x] 11.4 Test `IN_COMBAT`: an active, non-fled, living roster member of an unresolved `Battlefield`
      is rejected; the same actor after `is_battle_over()` becomes `True` is not rejected on this basis.
- [x] 11.5 Test that fled `Battlefield` membership alone is not a reject condition: an actor present in
      `battlefield.fled` (that `Battlefield`'s `is_battle_over()` still `False`), sharing no room with a
      living `Monster`, returns `None` — proving `fled` is not read as a positive hostility signal
      anywhere in this module (source-inspection check: `battlefield.fled` appears only inside the
      `IN_COMBAT` check).
- [x] 11.6 Test `HOSTILE_PRESENT`: a living `Monster` sharing the actor's room (no `Battlefield` at all)
      rejects; a dead `Monster` in the room does not; an empty room does not.
- [x] 11.7 Test the safe case: no `Battlefield` membership and no living `Monster` present returns
      `None`.
- [x] 11.8 Confirm `SkipRejectReason`'s definition carries no "allowed seconds"/partial-duration field
      (source inspection), matching design.md D-6's "reject outright, never shorten at the gate" claim.

## 12. Time-skip commands (`commands/skip.py`)

- [x] 12.1 Implement `_parse_duration(text: str) -> int` (e.g. `"1h"` → `3600`, `"30m"` → `1800`),
      raising a named parse error for an unrecognized shape.
- [x] 12.2 Implement `CmdRest` per design.md D-7: parses its argument via `_parse_duration()` before the
      safety check, so an invalid duration is rejected without querying safety; on a non-`None` safety
      result, reports the rejection and returns without calling `advance()`; otherwise calls
      `WORLD_CLOCK.advance(seconds, AdvanceSource.SKIP, entities=[self.caller])` and renders the result.
- [x] 12.3 Implement `_seconds_to_full_regen(entity) -> int` per design.md D-7: computes
      `ceil((gauge.max - gauge.value) / gauge.rate)` for each of `hp`/`mp`/`sp` (skipping a gauge already
      at max or with `rate <= 0`), takes the maximum across the three, caps at
      `CLOCK_YAML["max_sleep_seconds"]`, floors at `0`.
- [x] 12.4 Implement `CmdSleep` per design.md D-7: takes no argument; safety-gated identically to
      `CmdRest`; computes its duration via `_seconds_to_full_regen()`; advances and renders.
- [x] 12.5 Implement `CmdWaitUntil` per design.md D-7: parses `"until <daypart>"`; safety-gated
      identically; computes its duration via `seconds_until_daypart()` (task 3.4); advances and renders.
- [x] 12.6 Implement `_render_skip_summary(seconds, events) -> str`: reports the elapsed duration and
      any due `ScheduledEvent`s (in particular a `daily_reset` event) in plain text, calling no LLM.
- [x] 12.7 Test `CmdRest`: `"rest 1h"` on a safe actor advances by exactly `3600`; an unparseable
      duration rejects before any safety check or `advance()` call; a safety-gate rejection reports the
      reason and skips `advance()` entirely.
- [x] 12.8 Test `CmdSleep`: duration matches the largest of the three computed gauge-regen times when
      under the cap; is capped at `max_sleep_seconds` when the computed value would exceed it; is `0`
      when every gauge is already full; is blocked by the safety gate identically to `CmdRest`.
- [x] 12.9 Test `CmdWaitUntil`: a future-today daypart computes the same-day remainder; a
      already-passed-today daypart computes tomorrow's occurrence (never zero/negative); an unrecognized
      daypart name rejects before any safety check or `advance()` call; blocked by the safety gate
      identically to the other two commands.
- [x] 12.10 Test `_render_skip_summary()`: a skip crossing a day boundary reports the reset; a skip with
      an empty `ScheduledEvent` list still reports the elapsed duration with no error.

## 13. Verification

- [x] 13.1 Run the full `world/rules/tests/` suite added by this change and confirm every test passes.
- [x] 13.2 Confirm `world/rules/clock.py`, `world/rules/skip_safety.py`, and `commands/skip.py` contain
      no reference to `world/ai/` and no LLM call anywhere (source-scan, mirroring change 8's own
      no-Narrator discipline).
- [x] 13.3 Confirm the only inherited implementation edits are the documented deterministic-time
      corrections in `world/rules/traits.py`, `world/rules/buffs.py`, trait registration, combat's
      existing six-second buff call site, `commands/action.py::CmdCast`, and the character command set;
      no predecessor OpenSpec artifact is touched.
- [x] 13.4 Confirm change 6's, change 7's, change 9's, and change 10's suites pass with the deterministic
      gauge/buff correction; pass combat's existing six-second round duration into `tick_buffs()` but do
      not otherwise edit `sexual_state.py`, `combat.py`, `overwhelm.py`, or their rulebooks.
- [x] 13.5 Confirm no test or fixture added by this change relies on iterating one real second (or one
      real quantum) per unit of requested skip duration for a multi-hour skip — a complexity/call-count
      assertion guarding against a regression back toward per-second stepping.
- [x] 13.6 Confirm this change modifies no file authored by change 11b — `world/rules/progression.py`
      is read only through the self-arming lazy import in `_try_accrue_magic_study()` (task 7.2), never
      imported at module load time and never edited.
- [x] 13.7 Confirm permanent `conferred_growth_rate` remains an explicit no-op tick and does not expire;
      deterministic buff settlement must not reintroduce the prior unsupported `magic_level_growth`
      write path.
- [x] 13.8 Run `openspec validate world-clock --strict` and confirm it passes.
