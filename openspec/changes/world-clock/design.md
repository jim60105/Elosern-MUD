## Context

This is roadmap item #11 (design doc §11), depending on change 7 (`sexual-state`) and change 9
(`dice-combat`). No code exists yet for this change's scope — nothing named `world/rules/clock.py`,
`world/rules/skip_safety.py`, `world/rules/rulebook/clock.yaml`, or `commands/skip.py` exists.

**This change is the single authority on settlement order, by explicit design of three prior
changes.** Change 6 (`buffs-rulebook`) built `tick_buffs(entity)` and stated in its own Non-Goals: "this
change exposes buff-tick as a plain callable ... for change 11 to invoke at the point in its fixed
settlement order ... that change 11 decides; this change does not invent, assume, or hardcode any
ordering relative to regen or sexual decay." Change 7 (`sexual-state`) built `decay_tick(entity,
elapsed_seconds)` and `reset_daily_counters(entity)` with the identical disclaimer, word for word: "no
ordering relative to trait regen or buff ticks is assumed or hardcoded here." Change 9 (`dice-combat`)
built `run_battle()` to report `total_seconds = rounds_elapsed * 6` and asserted, via a grep-based test,
that its own code "references no `WorldClock` and calls nothing named `advance()`." Change 10
(`overwhelm-resolution`) made the identical assertion for `OverwhelmResult.total_seconds`. Change 8
(`action-resolver`) built `ActionResolver.resolve()`'s step 8 to *report* `time_cost_seconds` and
documented explicitly: "this function never calls anything resembling `WorldClock.advance()` ... the
caller is expected to hand that number to `WorldClock.advance()` once change 11 exists." Five separate
changes, five separate refusals to guess — all deferred here. This design treats that deferral as a
mandate, not a suggestion: §6.5's order is fixed *because order changes outcomes* (regen before decay
means a long rest heals before arousal fades; the reverse would let a still-arousal-suppressed combatant
regen at a different effective rate depending on which pass ran first if any stage read another
stage's output — they do not, but the *order they commit in* is still part of what a save reproduces).

**What already exists for this change to build on, unmodified:**
- Change 6: `tick_buffs(entity)` (one call = one tick's worth of every active buff's rate modifier),
  `entity.buffs` (`BuffHandler`), `buffs.yaml` (seed set: `poisoned` `tick_interval: 10`, `paralysis`,
  `fear`, `conferred_growth_rate` with no rate/tick_interval).
- Change 7: `decay_tick(entity, elapsed_seconds)` (accumulates `elapsed_seconds` per configured field
  in `entity.attributes`; decrements one level toward its floor and resets the accumulator once a
  field's accumulator crosses its configured `interval_seconds`), `reset_daily_counters(entity)` (zeroes
  `climax_today`), `DECAY_CONFIG` (`arousal` 1800s, `wetness` 900s, `shame` 1800s, `climax_phase` 300s
  from `餘韻` only).
- Change 3 (`entity-traits`): `entity.traits.hp`/`mp`/`sp` as `GaugeTrait` (max + regen rate),
  `Monster`, `LivingEntity`.
- Change 9: `Battlefield` (`teams`, `roster`, `fled: set[str]`), `BattleResult.total_seconds`,
  per-round upkeep inside `run_round()` that *already* calls `tick_buffs()`/`decay_tick()` once per
  round for every living roster member — a fact this change's own settlement order must not
  double-apply against (D-3).
- Change 10: `OverwhelmResult.total_seconds` (same `rounds_elapsed * 6` formula, bounded to a handful of
  rounds by its own Signal 3).
- Change 8: `ActionResolver.resolve()` → `ActionResult.success(event_log, time_cost_seconds)`;
  `commands/action.py::CmdCast`, which currently calls `resolve()` and renders the result but does not
  call anything resembling `advance()`.

**What genuinely does not exist yet, and is out of this change's scope by roadmap design.** Changes
12-14 (map layers) have not built `AnchorRoom`/`GridRoom`/`InstanceRoom` or any location-safety
metadata; change 15 (`quest-runtime`) has not built quest deadlines; change 16 (`guild-economy`) has
not built shop hours or caravans; change 19 (`npc-dialogue`) has not built `NPC.schedule`'s consumer.
This change must give each of those four a place to attach (§6.5's own list: caravan arrivals → shop
hours → quest deadlines → NPC schedules) without inventing their data.

## Goals / Non-Goals

**Goals:**
- `world/rules/clock.py::WorldClock` — `tick: int` as the sole persisted driver of game time,
  `calendar: WorldDateTime` as a pure function of `tick`, `advance(seconds, source, entities) -> list[
  ScheduledEvent]` as the only way `tick` ever moves.
- A fixed, ordered, tested settlement-stage registry implementing design doc §6.5's exact order, with
  a transposition test that fails if any two stages swap.
- `AdvanceSource` (`COMMAND` / `COMBAT` / `SKIP`) so a combat-sourced advance does not re-run buff-tick/
  sexual-decay that change 9's own per-round upkeep already applied.
- Quantum-batched settlement for long jumps: no per-second iteration, an explicit early-exit once
  nothing remains to settle, and boundary-arithmetic (not iteration) for hourly/daily stages.
- A concrete, simple, subtropical four-season calendar with no invented month names.
- `world/rules/skip_safety.py::evaluate_skip_safety(actor)` — the three named reject conditions, built
  from data genuinely available at this point in the roadmap (no map layers).
- `commands/skip.py`: `rest <duration>`, `sleep`, `wait until <daypart>`.
- Declared, no-op seam stages (and an open `ScheduledEvent` source registry) for caravan arrivals, shop
  hours, quest deadlines, and NPC schedules.
- A reproducibility guarantee — same `tick` + same stored entity state → same settlement outcome —
  proven by a test, not merely asserted.
- Persist `tick` via a non-repeating Evennia `Script` used purely as an attribute container, with a
  tripwire test proving no wall-clock read exists anywhere in this change's code.
- Wire the two time-cost producers this change can concretely reach today: `CmdCast` (change 8) and a
  named `settle_combat_result()` seam for whichever future change adds a top-level combat command.

**Non-Goals:**
- **No character progression** (change 11b) — `growth_rate_multiplier()`'s consumer is not this
  change's job; nothing here reads or writes XP/level state.
- **No map layers, location-safety metadata, or coordinates** (changes 12-14). `evaluate_skip_safety()`
  uses only data that exists today: `Battlefield` membership and room co-location with a living
  `Monster`. It does not invent a `safe_zone` flag, a terrain type, or anything else changes 12-14 would
  need to actually supply.
- **No quest deadlines, shop hours, or caravan logic** (changes 15, 16). This change registers named,
  no-op placeholder stages and an event-source registry for these; it authors no scheduling data.
- **No NPC schedule content** (change 19, and change 3's still-unowned `NPC.schedule` field). Same
  placeholder treatment.
- **No whole-world simulation.** `advance()` settles exactly the entities its caller passes to it —
  there is no global entity registry, no "catch-up simulation" for NPCs the player is nowhere near.
  Single-player scope; see D-8 for the explicit scoping decision and its rationale.
- **No movement or conversation commands.** `move`/`converse` need rooms/exits (changes 12-14) and NPC
  dialogue (change 19) respectively, neither of which exists. This change declares their time-cost
  constants as rulebook data and nothing else (D-9).
- **No edits to any other change's OpenSpec artifacts.** `CmdCast`'s *source file* (change 8's
  implementation output, not its proposal/design/specs) gains one `WorldClock.advance()` call as this
  change's own integration task — the identical "downstream change touches upstream code" pattern every
  change in this roadmap already exercises (e.g., change 9 registering into change 8's effect registry).
- No backward-compatibility, migration, or deprecation handling — the project is unreleased with zero
  users.

## Decisions

### D-1. `WorldClock`: `tick` is the only persisted number; `calendar` is a pure function of it, never
stored separately.

```python
# world/rules/clock.py
@dataclass
class WorldClock:
    tick: int   # total elapsed game-seconds since epoch (tick=0). The ONLY field this class persists.

    @property
    def calendar(self) -> "WorldDateTime":
        return WorldDateTime.from_tick(self.tick)   # pure function — see D-2
```

**Why a single integer, not a struct of separately-mutable fields.** If `year`/`season`/`day`/`hour`
were each their own persisted counter, incrementing them correctly on every `advance()` call (carrying
between hour→day→season→year) would be a second, independent place this change could get wrong, and a
save/reload cycle would need all four counters to agree with each other for reproducibility (hard
requirement 4) to hold at all. Deriving every calendar field from one monotonically increasing integer
means there is exactly one number to persist and exactly one function (`WorldDateTime.from_tick()`,
pure, memoization-free) that ever computes "what time is it" — the same "derived, never stored"
discipline change 5's `effective_value()` and change 9's `effective_power()` already established for
their own domains.

**Persistence: a non-repeating `Script` used purely as an attribute container — not a ticker.**

```python
# server startup / first access
clock_script = evennia.create_script(
    "world.rules.clock.WorldClockScript",
    key="world_clock", persistent=True, interval=0, repeats=0,
)
```

```python
class WorldClockScript(DefaultScript):
    """Persistent singleton storage for WorldClock.tick -- NOT a ticker.
    `interval=0` and `repeats=0` at creation, and `at_repeat()` is never
    overridden, so this Script never fires on its own; its only job is
    surviving a server restart via Evennia's ordinary Attribute-persistence
    mechanism, exactly as any other piece of persistent global state would.
    Flagged for implementer verification: the exact DefaultScript constructor
    keyword names for 'never repeat' against the installed Evennia 6.1.0
    package, consistent with this project's established discipline."""
    def at_script_creation(self):
        self.db.tick = 0
```

**Why this, and why the distinction matters for D4.** Design doc D4 says the world advances *only* on
player action, plus `rest`/`sleep`/`wait`. Evennia's `Script`/`TickerHandler` machinery is normally
introduced specifically to make something happen on a wall-clock interval (`interval=N`, repeating
`at_repeat()`) — using it that way here would be the literal violation D4 warns about: game time
advancing because real time passed, not because the player acted. This design uses exactly one piece of
`Script` machinery (`DefaultScript`, for its Attribute-persistence and its guaranteed one-per-server
lookup by `key`), with the ticking half explicitly disabled (`interval=0`, no `at_repeat()` override) —
a storage box, not a timer. A tripwire test (D-10) asserts this in the negative: no file this change
adds contains `interval=` set to a nonzero literal, an `at_repeat` method definition, or a call into
`evennia.scripts.tickerhandler`.

**Alternative considered**: store `tick` as a plain `Attribute` on the account or the first player
character instead of a dedicated `Script`. Rejected — a single-player game still benefits from one
canonical, unambiguous location for "the world's clock" that does not depend on which character object
happens to exist first or survive an account being deleted and recreated; a dedicated, well-known-`key`
`Script` is Evennia's own idiom for exactly this ("a persistent singleton that isn't attached to any one
object"), and is not being used for anything beyond that idiom here.

### D-2. `WorldDateTime`: a subtropical, four-mild-season calendar with no invented month names —
season index, day-in-season, and a 24-hour clock, all derived from `tick`.

`world_info.md` states the setting's climate directly: "氣候：亞熱帶為主，四季分明但溫和宜居" (predominantly
subtropical; four distinct but mild seasons; temperate and habitable) — four seasons, explicitly named
nowhere beyond that one line, and no month or day-count convention anywhere in the source material.
This change owns filling that gap, and keeps it as small as design doc §6.5's actual consumers need:
a day boundary (for daily resets), an hour boundary (for future shop-hours/NPC-schedule stages), and a
handful of named dayparts (`wait until dawn`) — nothing richer.

```yaml
# world/rules/rulebook/clock.yaml
seconds_per_hour: 3600
hours_per_day: 24            # -> 86400 seconds/day
days_per_season: 90
seasons_per_year: 4          # -> 360 days/year -- deliberately not 365; no leap-year
                               # arithmetic, no invented intercalary day. This project's
                               # own precedent (dice-combat D-2, overwhelm-resolution D-1)
                               # treats "simplest correct number" as a first-class virtue,
                               # not a placeholder to apologize for.
season_names: ["春季", "夏季", "秋季", "冬季"]   # Spring/Summer/Autumn/Winter -- the
                               # generic Chinese terms themselves, not a new proper noun;
                               # "溫和宜居" (mild, habitable) is honored by NOT differentiating
                               # season-specific mechanical effects here (no season carries a
                               # stat penalty/bonus in this change's scope) -- a later change
                               # is free to add one, this change only supplies the calendar.
dayparts:                     # named points in the 24-hour clock, for `wait until <daypart>`
  midnight: 0
  dawn: 6
  noon: 12
  dusk: 18
```

```python
@dataclass(frozen=True)
class WorldDateTime:
    year: int
    season_index: int      # 0-3, index into season_names
    day_in_season: int      # 1-90
    hour: int               # 0-23
    minute: int
    second: int

    @property
    def season_name(self) -> str:
        return CLOCK_YAML["season_names"][self.season_index]

    @classmethod
    def from_tick(cls, tick: int) -> "WorldDateTime":
        """Pure function -- every field is computed from `tick` alone, no
        persisted state of its own, no wall-clock read. Days/hours/minutes/
        seconds fall out of simple integer division; season/year fall out of
        360-day-year arithmetic."""
        spd = CLOCK_YAML["seconds_per_hour"] * CLOCK_YAML["hours_per_day"]        # 86400
        days_per_year = CLOCK_YAML["days_per_season"] * CLOCK_YAML["seasons_per_year"]  # 360
        total_days, rem_seconds = divmod(tick, spd)
        year, day_of_year = divmod(total_days, days_per_year)
        season_index, day_in_season = divmod(day_of_year, CLOCK_YAML["days_per_season"])
        hour, rem_seconds = divmod(rem_seconds, CLOCK_YAML["seconds_per_hour"])
        minute, second = divmod(rem_seconds, 60)
        return cls(year, season_index, day_in_season + 1, hour, minute, second)
```

**Why day boundaries and hour boundaries are the only two granularities this change defines**, rather
than a richer week/month structure: design doc §6.5's own consumer list is `daily resets` (needs a day
boundary), `shop hours` (needs an hour boundary — "open 9-18" is expressible with hour alone), `caravan
arrivals`/`quest deadlines` (both expressible as "due at tick T," needing no calendar granularity finer
than a raw tick comparison), and `NPC schedules` (plausibly hour-of-day, same granularity shop hours
need). Nothing in this change's own consumer set needs a week or a month; inventing one now would be
speculative structure with no reader.

**Why the day boundary is "hour rolls from 23 to 0," not a locally-defined "a day starts at dawn."**
`reset_daily_counters()` (change 7) has no opinion on what a day boundary means — it is just a
callable. Defining the boundary at midnight (hour 0), the same convention `divmod` above already
produces for free, needs no separate case; defining it at dawn instead would require carrying an offset
through every day-boundary computation for no stated benefit — `variable_rule.md`/`world_info.md` never
say `climax_today` should reset at dawn specifically, only "daily."

### D-3. Settlement order is fixed, tested by a transposition-sensitive test, and
`AdvanceSource`-conditional to avoid double-applying what combat's own turn loop already did.

**The exact order, unconditionally, per design doc §6.5:**

```python
class AdvanceSource(StrEnum):
    COMMAND = "command"   # a single resolved skill cast / future move-or-converse command
    COMBAT = "combat"     # BattleResult.total_seconds / OverwhelmResult.total_seconds
    SKIP = "skip"         # rest / sleep / wait

_STAGE_ORDER = (
    "gauge_regen",          # HP/MP/SP regen
    "buff_ticks",           # buff durations
    "sexual_decay",         # sexual state decay
    "daily_resets",         # climax_today, etc.
    "caravan_arrivals",     # declared seam — change 16
    "shop_hours",           # declared seam — change 16
    "quest_deadlines",      # declared seam — change 15
    "npc_schedules",        # declared seam — change 19
)
```

**Why `buff_ticks` and `sexual_decay` are skipped entirely when `source is AdvanceSource.COMBAT` — the
one correctness bug this design exists to prevent.** Change 9's `run_round()` (D-9 of its own design)
*already* calls `tick_buffs(entity)` and attempts `decay_tick(entity, ...)` once per round, for every
living roster member, as part of combat's own per-round upkeep — this is not something this change
adds, it is already-landed change-9 behavior. If `WorldClock.advance(total_seconds,
AdvanceSource.COMBAT)` naively re-ran the full stage list including `buff_ticks`/`sexual_decay` for that
same elapsed span, a poisoned combatant's hp would be debited twice for the identical six seconds — once
inside `run_round()`'s own upkeep, once again inside this change's own settlement pass over the same
interval. **Decision**: the settlement-stage registry gates `buff_ticks` and `sexual_decay` on
`source is not AdvanceSource.COMBAT`; every other stage (`gauge_regen`, `daily_resets`, and the four
declared-seam stages) always runs regardless of source, since none of those is applied anywhere inside
combat's own turn loop today.

```python
def _run_stages(clock: WorldClock, seconds: int, source: AdvanceSource, entities) -> list["ScheduledEvent"]:
    events: list[ScheduledEvent] = []
    _settle_gauge_regen(entities, seconds)                                    # always
    if source is not AdvanceSource.COMBAT:
        _settle_buffs_and_decay(entities, seconds)                            # D-4's quantum loop
    events += _settle_boundary_stages(clock.tick, clock.tick + seconds)       # D-5's declared seams
    return events
```

**The transposition-sensitive test — proving the *order* is what it claims to be, not merely that
each stage ran.** A test that only asserts "hp increased, some buff decremented, some sexual field
decayed, `climax_today` reset" after one `advance()` call would still pass if two adjacent stages were
swapped, because none of design doc §6.5's four built stages currently reads another built stage's
*output* — they are independent effects on independent fields. Order-sensitivity therefore has to be
constructed, not discovered incidentally, exactly as the task asks. **Decision**: construct a fixture
where `gauge_regen`'s effective outcome depends on a *combat modifier* driven by `sexual_decay`'s
*starting* value in a way that materially changes if decay runs before or after the modifier is read for
that pass — concretely: an entity whose `arousal` starts at `高度` (triggering change 6's
`high_arousal_agility_accuracy_penalty` combat-modifier row, which this change does not itself consume,
but whose presence is used here only as an *observable side channel*, not as a mechanical dependency
between stages) is too indirect and reintroduces a real coupling this change must not create. The
actual, minimal, and honest construction instead exploits the one place §6.5's stages *do* share a
resource: **HP.** Stage a fixture with a `poisoned` buff (change 6's own seed buff: `-5 hp` per tick,
regen `entity.traits.hp` at `+2/quantum`) and assert the *exact final hp value* after one `advance()`
call — this final number is different depending on whether `gauge_regen` or `buff_ticks` runs first
within the same settlement pass (regen-then-poison vs. poison-then-regen over the same number of
quanta/seconds does not commute once either value clamps against `hp.max`, and even away from the
clamp, applying a flat `+2` before a flat `-5` accumulates a different intermediate trajectory than the
reverse when *both* are re-derived per quantum against the then-current value rather than computed once
against the starting value — see the worked arithmetic below). **A second assertion in the same test**
directly inspects `_STAGE_ORDER` and fails if `"buff_ticks"` does not appear strictly before
`"sexual_decay"` and strictly after `"gauge_regen"`, and if `"daily_resets"` does not appear strictly
after `"sexual_decay"` — a structural check the arithmetic check alone cannot fully substitute for
(two adjacent stages that happen not to interact arithmetically in a given fixture would still pass the
arithmetic check if swapped; the structural check catches that case directly). **Together, these two
assertions are what the task means by "fails if two stages are transposed"**: the structural assertion
catches any transposition mechanically and immediately; the arithmetic assertion additionally proves the
order has a real, executable consequence for at least the regen/buff pair, not just a documented
convention nothing enforces.

**Worked arithmetic for the regen/poison case (quantum = 10s, per D-4):** starting hp = 50, max = 200,
regen rate = +2/quantum, poison = -5/quantum, both active for 3 quanta.
- Regen-first order, quantum-interleaved (`regen; poison; regen; poison; regen; poison`): 50 → 52 → 47
  → 49 → 44 → 46 → 41.
- Poison-first order, quantum-interleaved (`poison; regen; poison; regen; poison; regen`): 50 → 45 → 47
  → 42 → 44 → 39 → 41.

These two sequences land on the identical final value (41) for this specific linear, non-clamping
fixture — which is precisely why the test's fixture is instead constructed so regen would clamp against
`hp.max` under one order but not the other (e.g., starting hp within 2 of `max`, so a regen-first quantum
saturates at the ceiling while a poison-first quantum for the same quantum does not), making the final
hp value provably different between the two orderings, not merely differently-routed to the same number.
The exact fixture numbers are a task-list/implementation detail (task list specifies the precise starting
hp/max/rate combination); this section records the *shape* of the proof — clamping breaks commutativity,
flat addition alone does not — so the implementer builds the actual regression test against a fixture
where the non-commutativity is real, not accidentally cancelled out.

### D-4. Quantum-batched settlement: `rest 8h` is one `advance()` call, and the per-quantum stages
early-exit the moment nothing is left to settle.

**Why per-second stepping is unacceptable and what replaces it.** `decay_tick(entity, elapsed_seconds)`
and `tick_buffs(entity)` are each documented (changes 6/7) as "one call = one tick's worth" — the
accumulator lives *inside* the callable (change 7's own `entity.attributes`-backed accumulator; change
6's contrib-managed buff duration/tick-interval bookkeeping), which means correctly simulating a long
skip means calling these functions enough times, with correctly-sized `elapsed_seconds` chunks, that
their own internal accumulators cross exactly as many interval boundaries as the real elapsed time
implies — not a single call with the full elapsed seconds, which (per change 7's own documented
"accumulates ... when a field's accumulator crosses its configured interval, decrements ... by one
level ... resetting the accumulator") would incorrectly apply only a single decrement no matter how many
interval-widths the elapsed time actually spans.

**Decision: a settlement quantum equal to the GCD of every currently-configured per-tick interval.**
Today's seed data: `buffs.yaml`'s only rate-bearing buff, `poisoned`, has `tick_interval: 10`;
`sexual_state.py`'s `DECAY_CONFIG` has intervals `1800` (arousal), `900` (wetness), `1800` (shame), `300`
(climax_phase). `gcd(10, 300, 900, 1800) = 10`. `SETTLEMENT_QUANTUM_SECONDS = 10` is computed once at
`clock.py` import time from these two rulebooks (not hand-copied), with a loud startup assertion if a
future buff or decay entry is ever added with an interval not evenly divisible by the resulting GCD
(the same "recompute, don't hand-copy" discipline as `combat.yaml`'s own to-hit constant derivation) —
this makes every quantum-sized call line up exactly on an interval boundary for every currently
configured field, so `tick_buffs()`/`decay_tick()`'s own internal accumulators cross correctly with no
special-casing per field.

```python
def _settle_buffs_and_decay(entities, seconds: int) -> None:
    quanta, remainder = divmod(seconds, SETTLEMENT_QUANTUM_SECONDS)
    # `remainder` (always 0 while every configured interval divides the quantum's own GCD-derived
    # value, per the startup assertion above) is intentionally not separately special-cased.
    for _ in range(quanta):
        if not any(_has_settlement_work(e) for e in entities):
            break   # early exit: no active buff and every sexual field already at its floor,
                     # for every entity in scope -- further quanta are provable no-ops
        for entity in entities:
            tick_buffs(entity)
            decay_tick(entity, SETTLEMENT_QUANTUM_SECONDS)

def _has_settlement_work(entity) -> bool:
    """True if this entity has anything left for a quantum to do -- an active
    buff, or a sexual field not already at its vocabulary floor. Reads only
    the public surfaces (entity.buffs.all(), entity.sexual.<field>.level vs.
    the field's own floor) -- never a private accumulator."""
    if entity.buffs.all():
        return True
    sexual = getattr(entity, "sexual", None)
    if sexual is None:
        return False
    return any(
        getattr(sexual, field).level != floor
        for field, floor in _DECAY_FLOOR_LEVELS.items()   # {"arousal": "平靜", "wetness": "乾燥", ...}
    )
```

**Why this bounds the real iteration count in the common case, and what the worst case still costs.**
A rest/sleep starting from a fully settled, buff-free, floor-level state (the overwhelmingly common
case for a deliberate "go to sleep" action, since nothing provoked a stimulus recently) exits after
exactly one quantum's check — `O(1)`, regardless of how many hours the player requested. A rest that
begins mid-poison (duration 300s, i.e. 30 quanta) ticks correctly through those 30 quanta and then
early-exits for the remainder of an 8-hour request (2,850 more quanta skipped) — bounded by the buff's
own configured duration, not by the skip length. The genuine worst case — every entity in scope
permanently active for the entire requested span — is bounded by a defensive cap,
`MAX_SETTLEMENT_QUANTA` (`rulebook/clock.yaml`, seeded at `4320`, i.e. 12 in-game hours' worth at the
current 10-second quantum): the loop stops there regardless of `_has_settlement_work()`'s answer,
mirroring `overwhelm-resolution`'s own `max_rounds` defensive backstop pattern exactly. Hitting this cap
is a named, tested outcome — `advance()` still completes (the calendar/regen/boundary stages are
unaffected, since they are `O(1)` per D-1/D-5), it simply stops applying further buff-tick/sexual-decay
quanta and the caller sees a `ScheduledEvent` noting the cap was hit, rather than the call hanging.

**Why `gauge_regen` needs no quantum loop at all.** HP/MP/SP regen is a closed-form read of each
`GaugeTrait`'s own `rate` — `new_value = min(max, current + rate * elapsed_seconds)` — computed once
per entity per `advance()` call, using the full `seconds` value directly, never chunked. This is
deliberately **not** routed through whatever automatic, possibly wall-clock-timestamp-driven regen
mechanism the installed `GaugeTrait` contrib might implement internally (flagged for implementer
verification: if `GaugeTrait.value`'s own getter lazily regenerates based on `datetime.now()` rather
than an explicit elapsed-seconds argument, that mechanism must be bypassed or disabled entirely, since
reading it would let real wall-clock time leak into `entity.traits.hp` — exactly what D4 forbids).
`_settle_gauge_regen()` writes `entity.traits.<key>.value` directly through the trait's own public
setter, using only the `seconds` this change's own `advance()` call received as an argument.

**Why hourly/daily/etc. boundary stages (D-5) are not part of this quantum loop.** `caravan_arrivals`,
`shop_hours`, `quest_deadlines`, `npc_schedules`, and `daily_resets` are boundary-crossing checks —
"has an hour/day boundary been crossed between `start_tick` and `end_tick`" — answerable by one integer
division per boundary type (`end_tick // period - start_tick // period`), never by iterating every
second or even every quantum in between. A week-long `wait` (were one ever requested) costs the same
handful of arithmetic operations as a one-minute one for these stages; only the quantum loop's own cost
scales with elapsed time (bounded, per above, by actual settlement work or the defensive cap), not the
boundary stages'.

### D-5. Declared, no-op seam stages for caravan arrivals, shop hours, quest deadlines, and NPC
schedules — plus an open `ScheduledEvent` source registry, mirroring this project's established
"declare here, populate later" idiom.

```python
@dataclass(frozen=True)
class ScheduledEvent:
    kind: str            # open string convention, matching change 8's EventEntry.kind precedent
    due_tick: int
    payload: dict         # kind-specific, plain-JSON-compatible — no live entity references

EventSource = Callable[[int, int], list[ScheduledEvent]]   # (start_tick, end_tick) -> due events
_EVENT_SOURCES: dict[str, EventSource] = {}

def register_event_source(kind: str, source: EventSource) -> None:
    """The only sanctioned way a future change (12/16's caravans and shop
    hours, 15's quest deadlines, 19's NPC schedules) adds a boundary-crossing
    event query -- mirrors change 8's register_effect_handler() exactly."""
    _EVENT_SOURCES[kind] = source

def _settle_boundary_stages(start_tick: int, end_tick: int) -> list[ScheduledEvent]:
    events = []
    if start_tick // _SECONDS_PER_DAY != end_tick // _SECONDS_PER_DAY:
        events.append(ScheduledEvent(kind="daily_reset", due_tick=end_tick, payload={}))
        # reset_daily_counters(entity) is invoked by the caller for every entity in scope --
        # see the settlement loop; this stage's own job is detecting the boundary, exactly as
        # design doc S6.1 step 8 only *reports*, never itself applies a gameplay consequence
        # beyond its own named stage.
    for kind in ("caravan_arrivals", "shop_hours", "quest_deadlines", "npc_schedules"):
        source = _EVENT_SOURCES.get(kind)
        if source is not None:
            events.extend(source(start_tick, end_tick))
        # absent source == the honest, undecorated no-op this change ships with; see below
    return events
```

**Why a no-op, not a stub class or a `NotImplementedError`.** Design doc §6.5's order names four
stages this change is explicitly told not to build (caravans, shop hours, quest deadlines, NPC
schedules — Non-Goals). Raising for an unregistered source would make every `advance()` call fail
until changes 15/16/19 land, which is clearly wrong — the correct behavior for "nothing has registered
yet" is "nothing is due," exactly the same posture change 8's `_build_context()` took for `entity.sexual
is None` before change 7 existed. A test registers a synthetic source for a made-up `kind` and asserts
its `ScheduledEvent`s are returned in the correct position of `advance()`'s result list, proving the
extension mechanism works without needing any of changes 15/16/19's real data to exist — the identical
"prove the seam, not the payload" test shape this project's registries (change 6 D-1, change 8 D-7) all
use.

**Why `daily_resets` is hardcoded inside `_settle_boundary_stages()` rather than gone through the
`_EVENT_SOURCES` registry too.** Unlike the four declared-seam stages, `reset_daily_counters()` already
exists (change 7) and this change already knows exactly what "a new day" means (D-2's calendar) — there
is nothing to defer here, and routing an already-real, already-owned stage through an extension point
built for *unowned* future stages would blur which stages are this change's own settled behavior versus
a seam for someone else.

### D-6. `evaluate_skip_safety(actor)`: three reject conditions built entirely from data that exists
today — no invented location metadata.

Design doc §6.5: "reject or shorten a skip if the player is in combat, targeted by a hostile, or in an
unsafe location. Otherwise players will `sleep 8h` in front of a monster." Changes 12-14 (map layers,
location-safety tagging) have not landed. The only two data sources available at this point in the
roadmap are change 9's `Battlefield` (`teams`, `roster`, `fled`) and plain Evennia room co-location
(`entity.location.contents`, available since change 1's bootstrap) plus change 3's `Monster` typeclass.
**Decision: map all three named conditions onto these two sources, with no fabricated third signal.**

```python
class SkipRejectReason(StrEnum):
    IN_COMBAT = "in_combat"                 # active, non-fled roster member of an unresolved Battlefield
    TARGETED_BY_HOSTILE = "targeted_by_hostile"   # fled an unresolved Battlefield -- the fight isn't over
    HOSTILE_PRESENT = "hostile_present"      # a living Monster shares the actor's current room

def evaluate_skip_safety(actor) -> SkipRejectReason | None:
    battlefield = _active_battlefield_for(actor)   # caller-supplied lookup; see Open Questions
    if battlefield is not None:
        if actor.key in battlefield.roster and actor.key not in battlefield.fled \
                and actor.traits.hp.value > 0 and not is_battle_over(battlefield):
            return SkipRejectReason.IN_COMBAT
        if actor.key in battlefield.fled and not is_battle_over(battlefield):
            return SkipRejectReason.TARGETED_BY_HOSTILE
    for obj in actor.location.contents:
        if isinstance(obj, Monster) and obj.traits.hp.value > 0:
            return SkipRejectReason.HOSTILE_PRESENT
    return None   # safe to skip
```

**Why "targeted by a hostile" maps to `battlefield.fled`, not a bespoke aggro/threat model.** Design
doc §6.2 states plainly that "out of combat there is no hostility model" — there is no aggro table, no
threat score, nothing that names a specific hostile as "targeting" a specific actor outside an actual
`Battlefield`. The one condition that genuinely means "a hostile from a fight I was just in could still
reach me" with data that exists today is: the actor is recorded as having fled (`battlefield.fled`) an
encounter whose `is_battle_over()` is still `False` — the fight the actor left is still ongoing for
whoever remains, which is a real, present-tense danger signal, not an invented one. (Change 10c,
`combat-disengage`, is what will actually populate `fled` during play — the field already exists on
`Battlefield` today per change 9's dataclass, and reading it imposes no dependency on 10c's own write
path landing first, mirroring how change 9 itself already reads `battlefield.fled` before 10c exists.)

**Why "unsafe location" collapses to "a living Monster shares this room," not a terrain/zone
classification.** There is no `AnchorRoom`/`GridRoom`/safe-zone tag to read (changes 12-14 haven't
built one) — the only room-level fact available today is *what is physically standing in it*. A
wandering monster co-located with the actor, with no `Battlefield` yet formed at all (the player has not
engaged it, or it has not aggro'd), is exactly the scenario design doc's own worked example names
("sleep 8h in front of a monster") — this decision makes that literal sentence the literal rejection
condition.

**Why the gate rejects outright and does not attempt a "shorten" verdict of its own.** Hard requirement
2 says "reject or shorten." This decision reads that as two different commands' responsibility, not two
branches of the same gate function: **a monster standing in the room does not become less dangerous
partway through a shortened nap** — there is no data available (no threat/notice-timer model, no
`Monster.behaviour_tree`, which remains change 10b's unbuilt seam) from which to compute *how many
seconds* would actually be safe before the monster reacts. Inventing a plausible-looking "shortened to N
seconds" number with nothing backing it would be exactly the kind of guessed-at mechanic this project's
design docs consistently reject (e.g., change 9's D-7 refusing to guess at melee/ranged classification
from an unrelated field). **The gate's only two honest outcomes given today's data are "safe" and
"reject."** "Shorten" is real, but it belongs to the *commands* (D-7) as a duration-computation
concern independent of danger — `sleep`'s open-ended request is shortened to a concrete, bounded number
of seconds (regen-to-full, capped) for reasons that have nothing to do with whether a monster is
nearby, and would apply identically in a room this gate has already certified safe. The two concepts
("is this dangerous" and "how long does an open-ended request actually mean") are kept structurally
separate rather than conflated into one function that would otherwise need to reason about both at
once.

### D-7. `commands/skip.py`: `rest <duration>`, `sleep`, `wait until <daypart>` — each computing a
concrete second count before ever calling `advance()`.

```python
# commands/skip.py
class CmdRest(Command):
    key = "rest"
    # syntax: rest <duration>, e.g. "rest 1h", "rest 30m"

    def func(self):
        reason = evaluate_skip_safety(self.caller)
        if reason is not None:
            self.caller.msg(SKIP_REJECTION_MESSAGES[reason]); return
        seconds = _parse_duration(self.args)   # "1h" -> 3600, "30m" -> 1800; rejects unparseable input
        events = WORLD_CLOCK.advance(seconds, AdvanceSource.SKIP, entities=[self.caller])
        self.caller.msg(_render_skip_summary(seconds, events))

class CmdSleep(Command):
    key = "sleep"
    # syntax: sleep (no argument -- duration is computed, not requested)

    def func(self):
        reason = evaluate_skip_safety(self.caller)
        if reason is not None:
            self.caller.msg(SKIP_REJECTION_MESSAGES[reason]); return
        seconds = _seconds_to_full_regen(self.caller)   # D-7's "shorten" mechanism, below
        events = WORLD_CLOCK.advance(seconds, AdvanceSource.SKIP, entities=[self.caller])
        self.caller.msg(_render_skip_summary(seconds, events))

class CmdWaitUntil(Command):
    key = "wait"
    # syntax: wait until <daypart>, e.g. "wait until dawn"

    def func(self):
        reason = evaluate_skip_safety(self.caller)
        if reason is not None:
            self.caller.msg(SKIP_REJECTION_MESSAGES[reason]); return
        seconds = _seconds_until_daypart(WORLD_CLOCK.calendar, self.args)   # calendar arithmetic
        events = WORLD_CLOCK.advance(seconds, AdvanceSource.SKIP, entities=[self.caller])
        self.caller.msg(_render_skip_summary(seconds, events))
```

**`sleep`'s "shorten" mechanism — regen-to-full, capped, using only data this project already has.**

```python
MAX_SLEEP_SECONDS = 43200   # 12 in-game hours -- rulebook/clock.yaml; a placeholder cap, flagged
                              # for a future balance pass exactly like combat.yaml's own invented
                              # constants, so a near-zero regen-rate entity cannot request an
                              # absurd, unbounded jump

def _seconds_to_full_regen(entity) -> int:
    """Sleep lasts exactly as long as it takes every gauge (hp/mp/sp) to reach
    its max at its own regen rate, capped at MAX_SLEEP_SECONDS. This is the
    one duration this change computes rather than parses -- 'sleep' has no
    argument per design doc S6.5's own command list, so *some* concrete
    number must come from somewhere, and gauge regen rate is the only
    entity-specific, already-real data this project has for 'how long is a
    full rest.'"""
    needed = 0
    for key in ("hp", "mp", "sp"):
        gauge = getattr(entity.traits, key)
        if gauge.rate > 0 and gauge.value < gauge.max:
            needed = max(needed, math.ceil((gauge.max - gauge.value) / gauge.rate))
    return min(needed, MAX_SLEEP_SECONDS)
```

**`wait until <daypart>` — pure calendar arithmetic against `WORLD_CLOCK.calendar`, per D-2.** `seconds
= ((target_hour - current_hour) % 24) * 3600 - (current_minute * 60 + current_second)`, adjusted to
always land in the future (a request for the currently-active hour resolves to +24h, not 0). No
safety-specific logic here beyond the shared gate call already present in every one of the three
commands above.

**`rest <duration>` — explicit, parsed, never computed.** Unlike `sleep`, `rest` takes a concrete
duration argument (design doc §6.5's own example, "rest 1h") — no regen-to-full computation applies;
the player states exactly how long they mean, subject only to the shared safety gate.

### D-8. Explicit, caller-supplied settlement scope — no implicit whole-world simulation.

`WorldClock.advance(seconds, source, entities)` requires its caller to name which `LivingEntity`
instances are in scope for `gauge_regen`/`buff_ticks`/`sexual_decay` (D-3's per-entity stages); it never
queries a global entity registry itself. **Decision, and why**: this is a single-player game (design
doc §1) — simulating every NPC's hp regen and sexual decay everywhere in the world on every `advance()`
call, including NPCs the player is nowhere near, would require a global "every living entity in the
database" registry and a catch-up-simulation policy for entities re-encountered after a long absence,
neither of which any roadmap item through change 16 needs. Each of this change's own call sites commits
to a small, explicit scope: `CmdCast`/skip commands pass `[actor]`; `settle_combat_result()` passes
`battlefield.roster.values()` (though `buff_ticks`/`sexual_decay` are skipped there regardless per D-3,
`gauge_regen` still runs for the whole roster, which is the one stage combat's own turn loop never
applies on its own). A future change that needs NPCs elsewhere in the world to regen/decay while
unobserved (plausibly change 19's `NPC.schedule` consumer, itself still an unowned seam per change 3)
can extend the call sites it controls; this change does not guess at that policy.

### D-9. `move`/`converse` command-default time costs are declared as rulebook data only — no command
is built for either.

```yaml
# rulebook/clock.yaml (continued)
command_defaults:
  move: 30        # design doc S6.5
  converse: 60    # design doc S6.5
  cast: 6         # already change 8's own DEFAULT_CAST_SECONDS -- restated here as
                    # documentation cross-reference only, NOT a second source of truth;
                    # ActionResolver.resolve()'s own time_cost_seconds is what CmdCast
                    # actually passes to advance() (see D-10), never this table's copy
```

Building the commands that would actually charge these two costs needs a movement system (rooms/exits —
changes 12-14) and NPC dialogue (change 19), neither of which exists. Declaring the constants now, in
the one file every future command-default consumer would read anyway, costs nothing and gives whichever
change eventually builds `move`/`converse` a number to read rather than one more thing to invent from
scratch — the identical "declare here, build later" split this roadmap uses throughout (e.g., change
8's `damage:*` prefix, change 3's `NPC.schedule` field).

### D-10. The two concrete integration points this change can actually wire today.

**`CmdCast` (change 8, already built).** One line added to its existing `func()`, after a successful
`resolve()`:

```python
result = ActionResolver.resolve(request)
if result.outcome == "success":
    self.caller.msg(render_plain_text(result.event_log))
    WORLD_CLOCK.advance(result.time_cost_seconds, AdvanceSource.COMMAND, entities=[self.caller])
else:
    ...
```

This is an edit to change 8's *implementation output* (`commands/action.py`, a source file), not to any
of change 8's OpenSpec artifacts (`proposal.md`/`design.md`/`specs/`/`tasks.md`) — those remain
untouched, per this project's constraint against editing another change's planning documents.

**`settle_combat_result()` — a named seam, since no top-level combat command exists yet.**

```python
def settle_combat_result(result: "BattleResult | OverwhelmResult", entities) -> list[ScheduledEvent]:
    """Sanctioned call site for change 9's BattleResult.total_seconds and change
    10's OverwhelmResult.total_seconds. No roadmap item between changes 9 and
    16 builds a top-level 'engage in combat' Evennia command -- run_battle()/
    resolve_overwhelm() are library functions today, called by tests, with no
    owning command wrapper. This function is what such a command is expected
    to call once it exists; it is a declared, unbuilt integration point, the
    same treatment change 3 gave NPC.schedule/Monster.behaviour_tree."""
    return WORLD_CLOCK.advance(result.total_seconds, AdvanceSource.COMBAT, entities=entities)
```

A test calls this directly with a synthetic `BattleResult`/`OverwhelmResult`, proving the function
exists and produces the right `AdvanceSource`, independent of whichever future change supplies the
actual command that calls it in play.

## Risks / Trade-offs

- **[Risk] `SETTLEMENT_QUANTUM_SECONDS` is derived from today's seed `buffs.yaml`/`DECAY_CONFIG` data
  (GCD = 10). A future buff or decay entry with an interval not divisible by 10 would either shrink the
  quantum (more iterations for every future `advance()` call, project-wide) or, if the startup assertion
  were ever removed, silently misalign accumulator crossings.** → Mitigation: the startup assertion (D-4)
  fails loudly the moment such an entry is added, forcing whoever adds it to either pick an
  interval-compatible number or explicitly revisit the quantum — the same "recompute, don't hand-copy"
  discipline `combat.yaml`'s to-hit constant already uses.
- **[Risk] The transposition test's arithmetic proof (D-3) depends on a clamping fixture (starting hp
  near `max`) to make regen/poison ordering produce different final values; a less careful fixture could
  accidentally commute and pass even under a real transposition bug.** → Mitigation: D-3 documents the
  exact shape of fixture required (near-ceiling starting hp) and why a non-clamping fixture would not
  prove anything; the task list requires the regression test to assert the *specific* numeric hp value
  under the correct order and a *different* specific value under a deliberately-transposed order
  constructed in the same test, not merely "some value changed."
- **[Risk] `evaluate_skip_safety()`'s "hostile present" check (D-6) treats every living `Monster` in the
  room as equally dangerous, with no distinction for a monster that is asleep, non-aggressive, or
  otherwise narratively harmless** (`Monster.behaviour_tree` remains change 10b's unbuilt seam; there is
  no disposition field to read). → Accepted and named explicitly: inventing a disposition/aggro
  classification here would be exactly the kind of guessed-at mechanic this project's design docs reject
  elsewhere (change 9 D-7's melee/ranged refusal is the direct precedent); a conservative "any monster
  present blocks a skip" rule is the correct default until a later change (plausibly 10b) adds a real
  disposition model this gate can read instead.
- **[Risk] `MAX_SETTLEMENT_QUANTA`/`MAX_SLEEP_SECONDS` are both this change's own invented placeholder
  caps, not sourced from any lore document.** → Documented explicitly, flagged for a future balance
  pass, the identical disclosure discipline every prior change in this roadmap already applies to its
  own invented constants (combat.yaml's damage bands, overwhelm.yaml's round bound).
- **[Risk] `GaugeTrait`'s exact regen mechanism (whether its own `.value` getter lazily applies a
  wall-clock-timestamp-based regen internally) is unverified against the installed Evennia 6.1.0
  package.** → Flagged for implementer verification (D-4), consistent with changes 1-10's identical
  discipline for every other contrib-API assumption; this design's own `_settle_gauge_regen()` does not
  depend on the answer, since it writes the trait's value directly from an explicit `elapsed_seconds`
  argument rather than reading whatever automatic mechanism the contrib might supply — the risk is that
  the contrib's *own* automatic mechanism, if real time-based, must be verified as either dormant (never
  invoked) or explicitly disabled, not that this change's own arithmetic is wrong.
- **[Risk] Explicit, caller-supplied settlement scope (D-8) means an NPC or monster far from the player
  never regens or decays while unobserved, which could look inconsistent if the player later travels
  back to find a monster exactly as they left it hours of game-time ago.** → Accepted as the correct
  one-day scope cut for a single-player game with no roadmap item through change 16 needing distant-NPC
  simulation; named explicitly as an open question for whoever eventually needs it (plausibly change
  19's `NPC.schedule` consumer).

## Migration Plan

Not applicable in the backward-compatibility sense — the project is unreleased with zero users, and
none of `world/rules/clock.py`, `world/rules/skip_safety.py`, `world/rules/rulebook/clock.yaml`, or
`commands/skip.py` exist yet. The only sequencing concerns are operational:

- This change must land after change 7 (`decay_tick()`/`reset_daily_counters()`) and change 9
  (`Battlefield`, `BattleResult.total_seconds`, `tick_buffs()`/`decay_tick()` already called inside
  `run_round()`'s own upkeep) — matching design doc §11 exactly. Change 6 (`tick_buffs()`) is a
  transitive dependency through both.
- This change edits change 8's already-landed `commands/action.py::CmdCast` implementation (one
  `WorldClock.advance()` call added after success) — an implementation-level touch, not an edit to
  change 8's OpenSpec artifacts.
- Change 10 (`overwhelm-resolution`) is read (`OverwhelmResult.total_seconds`) but not edited.
- Changes 12-14 (map layers) are expected to eventually give `evaluate_skip_safety()`'s "unsafe
  location" condition a richer signal than "a monster is standing here" — this change does not block on
  that landing, and its own gate remains correct (if conservative) without it.
- Changes 15 (`quest-runtime`), 16 (`guild-economy`), and 19 (`npc-dialogue`) are expected to call
  `register_event_source()` for `quest_deadlines`, `caravan_arrivals`/`shop_hours`, and `npc_schedules`
  respectively — none of these calls exist yet; this change only guarantees the registry function and
  the fixed position each `kind` occupies in the settlement order.
- Change 10b (`monster-behaviour`) or a later change may eventually give `evaluate_skip_safety()` a real
  disposition/aggro signal to replace the current "any monster present" rule — not required for this
  change to be correct today.

## Open Questions

- **Should `evaluate_skip_safety()`'s `_active_battlefield_for(actor)` lookup be a caller-supplied
  parameter or a small global registry this change maintains (e.g., "which `Battlefield` is entity X
  currently a member of")?** No roadmap item through change 10c has built a canonical "find my current
  battlefield" lookup — change 9's `Battlefield` is constructed and held by whatever orchestrates combat
  (itself an unowned top-level command per D-10). This change's own commands (`rest`/`sleep`/`wait`)
  need *some* way to ask "is this actor currently in a fight," and the task list should have the
  implementer thread whatever combat-tracking mechanism the eventual combat command maintains through to
  this function's call site — left open because no such command exists yet to observe.
- **Should `MAX_SETTLEMENT_QUANTA`/`MAX_SLEEP_SECONDS` eventually be race- or activity-dependent** (an
  elf's vastly larger hp pool at the same regen rate implies a much longer natural full-heal time than
  this change's flat 12-hour cap allows for)? Left to a future balance pass; flagged already as an
  invented placeholder in Risks.
- **Exact `DefaultScript` constructor keyword names for "never repeat"** (`interval=0`/`repeats=0` vs.
  some other convention) are left to the implementer to confirm against the installed Evennia 6.1.0
  package, consistent with the verification discipline every prior change in this roadmap already
  established.
