## Why

Design doc §6.5 defines `WorldClock` as the sole mechanism by which game time ever advances, and D4
makes this a hard architectural boundary: the world is player-driven, never wall-clock-driven. Three
prior changes have already built the things that *report* a time cost without ever calling anything
resembling `advance()` — change 8's `ActionResolver` step 8, change 9's `run_battle()`, and change
10's `resolve_overwhelm()` all compute a `time_cost_seconds`/`total_seconds` integer and stop there,
by design, naming this change as the owner of what happens next. Two more changes — 6 (`buffs-
rulebook`) and 7 (`sexual-state`) — went further and exposed `tick_buffs(entity)` and
`decay_tick(entity, elapsed_seconds)`/`reset_daily_counters(entity)` as plain callables, explicitly
declining to invent the order in which they fire relative to each other or to trait regen, precisely
so that a single change would decide once and enforce it everywhere. Without this change, none of
that reported time ever becomes elapsed time, and there is no single place that settles regen, buffs,
sexual decay, and daily resets in a fixed, non-accidental order.

## What Changes

- Add `world/rules/clock.py::WorldClock` — `tick: int` (the sole persisted driver of game time) and
  `calendar: WorldDateTime` (a pure function of `tick`, never separately stored), with
  `advance(seconds, source) -> list[ScheduledEvent]` as the only way tick ever moves.
- Add a fixed, ordered settlement-stage registry implementing design doc §6.5's exact order (HP/MP/SP
  regen → buff durations → sexual state decay → daily resets → caravan arrivals → shop hours → quest
  deadlines → NPC schedules), with a test that fails if any two stages are transposed.
- Add `AdvanceSource` (`COMMAND` / `COMBAT` / `SKIP`) so a combat-sourced advance does not re-apply
  buff ticks / sexual decay that change 9's `run_round()` already applied per round — the one
  double-application bug this change's ordering authority exists to prevent.
- Register no-op, declared-seam stages for caravan arrivals, shop hours, quest deadlines, and NPC
  schedules (changes 12-16/19's future territory), plus an open `ScheduledEvent` source registry so
  those changes can attach without editing this change's code.
- Add quantum-batched settlement so a long skip (`rest 8h`) is one `advance()` call, not one
  step per second — regen is a closed-form formula (O(1)); buff-tick/sexual-decay are invoked once per
  a small, GCD-derived quantum with an early-exit once no entity has further per-quantum work; daily/
  hourly boundary stages fire by direct arithmetic on tick boundaries crossed, never by iteration.
- Add a subtropical, four-season calendar (`WorldDateTime`) with no invented month names — season and
  day-of-season counters only, plus a 24-hour/day clock with named dayparts (`dawn`, `noon`, `dusk`,
  `midnight`) for `wait until <daypart>`.
- Add `commands/skip.py`: `rest <duration>`, `sleep`, `wait until <daypart>` — the three explicit-skip
  commands, each computing a concrete duration (explicit, regen-to-full-capped, or
  calendar-arithmetic-to-next-daypart) and each gated by the safety check below.
- Add `world/rules/skip_safety.py::evaluate_skip_safety(actor)` — the safety gate: rejects a skip if
  the actor is an active (non-fled) member of an unresolved `Battlefield` ("in combat"), or shares a
  room with a living `Monster` ("targeted by a hostile" / "unsafe location," folded into one condition
  — the only location-safety signal available before changes 12-14 build map layers). `Battlefield.fled`
  was considered as a proxy for "targeted by a hostile" and rejected — it records combatants who
  successfully disengaged, the opposite of being hunted; see design.md D-6. No "shorten" branch is
  added at the gate itself; see design.md D-6 for why.
- Wire the two already-built time-cost producers this change can concretely reach: update
  `commands/action.py::CmdCast` (change 8) to call `WorldClock.advance(time_cost_seconds,
  AdvanceSource.COMMAND)` on success, and add `world/rules/clock.py::settle_combat_result()` as the
  sanctioned call site for `BattleResult.total_seconds`/`OverwhelmResult.total_seconds`
  (`AdvanceSource.COMBAT`) — flagged as an integration point for whichever future change adds a
  top-level combat command, since none exists yet (mirroring change 3's `NPC.schedule` treatment).
  `move`/`converse` command-default constants are declared as rulebook data for the same reason
  (their owning commands depend on map/NPC-dialogue changes not yet built).
- Persist `tick` via a non-repeating Evennia `Script` used purely as a persistent attribute container
  — explicitly not the `TickerHandler`/`interval` ticking mechanism — with a tripwire test proving no
  wall-clock read (`datetime.now`, `time.time`, a nonzero `interval`) exists anywhere in this change's
  code.

## Capabilities

### New Capabilities
- `world-clock`: `WorldClock`, `tick`, the subtropical four-season `WorldDateTime` calendar, the
  reproducibility guarantee (same tick + same stored state → same world), the non-ticking `Script`
  persistence mechanism, and the two concrete command-default/combat integration points.
- `settlement-stage-order`: the fixed, tested settlement order; `AdvanceSource`-conditional stage
  skipping to prevent combat double-ticking; quantum-based batching for long skips; the declared no-op
  seams for caravan/shop/quest/npc stages; the `ScheduledEvent` and event-source extension registry.
- `skip-safety-gate`: `evaluate_skip_safety()` — two reject conditions (in combat; a co-located living
  hostile, which is the one honest expression this project's data gives to both "targeted by a hostile"
  and "unsafe location") built from data available at this point in the roadmap. `Battlefield.fled` was
  considered and rejected as a third signal — see design.md D-6.
- `time-skip-commands`: `rest <duration>`, `sleep`, `wait until <daypart>` — duration computation and
  safety-gate integration for all three.

### Modified Capabilities
- None. No `openspec/specs/` capability specs exist yet (this is the first change to reach the archive
  step in this project); nothing here changes another change's already-frozen requirements.

## Impact

- New modules: `world/rules/clock.py`, `world/rules/skip_safety.py`, `world/rules/rulebook/clock.yaml`
  (calendar/quantum/command-default constants), `commands/skip.py`.
- Touches change 8's `commands/action.py::CmdCast` (adds one `WorldClock.advance()` call after a
  successful resolve — an implementation-level integration edit, not an edit to change 8's own
  OpenSpec artifacts).
- Reads, without modifying: change 6's `tick_buffs()`, change 7's `decay_tick()`/
  `reset_daily_counters()`, change 9's `Battlefield`/`BattleResult`, change 10's `OverwhelmResult`,
  change 3's `Monster`/gauge traits.
- No database migration concerns (project is unreleased, zero users).
