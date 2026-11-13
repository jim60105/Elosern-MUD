# Design

## Context

See proposal.md - Why. Facts (symbols from commit `f9925e49` and from earlier changes of the chain):

- `population_lifecycle.ensure_population_current(wilderness, seeds)` settles a closed set to the current tick with a registry, `held_advance_registry()`, `transaction.atomic()` and `restore_advance_registry` on failure. `settle_population_scope(wilderness, seeds, end_tick, *, contact=False)` settles to any target tick. `snapshot_population_lifecycle_surfaces(start, end, *, scope=...)` builds the registry for a scope.
- `population_units`: `current_unit_index()`, `closed_sets`, `build_scope`, `scope_start_tick`, `read_unit_cursors`, `unit_cursor`, `RESIDUAL_UNIT`.
- Precedent for a periodic script: `world/art/scheduler.py::ArtDrainScript` (a `DefaultScript` that sets `self.interval` from settings in `at_script_creation` and checks an enabled setting in `at_repeat`), registered in `server/conf/settings.py::GLOBAL_SCRIPTS`, with settings `ART_SCHEDULER_ENABLED = _env_bool(...)`, `ART_SCHEDULER_INTERVAL_SECONDS = _env_int(...)`.
- Every environment-backed setting name must be listed in `server/conf/test_settings.py::_ENV_OVERRIDES`; `server/conf/tests/test_env_overrides/test_inventory_and_shard_ownership.py` checks the list against `settings.py`. `.env.example` and `docs/development/settings-and-environment.md` document each name.
- The Server reactor is single-threaded and every clock advance is synchronous, so a script repeat can never interleave with an advance.
- The main design's decision D4: "The world advances only on player action". The drain does not move the world tick.

## Goals / Non-Goals

**Goals:**

- A deterministic drain function that tests call directly.
- A thin periodic caller with no logic of its own.

**Non-Goals:**

- No change to the clock stage, catch-up, entry points, owners or unit resolution.
- No real-time measurement, no adaptive slice, no priority by distance to the player.
- No drain in the Portal process and no thread: the drain runs on the Server reactor.
- No test that waits for a timer.

## Decisions

### D1. Lagging sets

Add to `population_units.py`:

```python
def all_units(index: UnitIndex) -> tuple[str, ...]      # RESIDUAL_UNIT plus every unit of zones and areas, sorted
def closed_sets(index: UnitIndex, state: MonsterActivityState, seeds: Iterable[str]) -> tuple[frozenset[str], ...]
def lagging_sets(wilderness, now: int) -> tuple[tuple[int, frozenset[str]], ...]
```

`closed_sets`: the distinct `unit_closure` results of the seeds, sorted by their smallest unit identifier.

`lagging_sets`: `closed_sets(index, read_monster_activity(wilderness), all_units(index))`; the cursor of a set is the lowest `unit_cursor` of its units (a set with unequal cursors is lawful and is settled from its lowest cursor, `unit-scoped-population-settlement` D1); keep sets with cursor below `now`; return `(cursor, set)` pairs sorted by `(cursor, min(set))`.

### D2. Drain function

Create `world/maps/population_drain.py`:

```python
def drain_population_backlog(slice_seconds: int) -> bool:
    """Settle the most lagging closed set forward by one slice; True when it settled anything."""
```

1. `slice_seconds` must be a positive `int`, else `ValueError`.
2. Resolve `regional_population.live_wilderness()`; return `False` when it is `None`, not provisioned, or has no cursor record.
3. `now = regional_population.current_population_tick()`; `pending = lagging_sets(wilderness, now)`; return `False` when empty.
4. For each `(start, units)` of `pending[:MAX_SETS_PER_RUN]` (module constant `MAX_SETS_PER_RUN = 3`), in order:
   1. `target = min(now, start + slice_seconds)`; `scope = build_scope(wilderness, units)`; `registry = snapshot_population_lifecycle_surfaces(start, target, scope=scope)`.
   2. `try:` → `with held_advance_registry(), transaction.atomic():` → `settle_population_scope(wilderness, units, target, contact=False)`; `remaining = len(pending) - (1 if target >= now else 0)`; `transaction.on_commit(lambda: log_info("population_backlog_drained", context={"units": len(units), "tick_from": start, "tick_to": target, "remaining": remaining}))`. On success return `True`.
   3. `except Exception as error:` → `restore_advance_registry(registry)`; `log_error("population_backlog_drain_failed", exc=error, context={"units": len(units), "tick_from": start, "tick_to": target})`; continue with the next set.
5. Return `False` when no set succeeded.

Steps 2 and 3 of the list above (wilderness resolution and `lagging_sets`) are inside one outer `try/except Exception` that emits the same error event with `units=0` and returns `False`, so the repeating script survives a malformed record. The function never re-raises. A failing set is tried again by the next run, after which the run moves on to the next sets; the error event repeats once per interval, which is the intended signal.

### D3. Periodic caller

In the same module:

```python
class PopulationDrainScript(DefaultScript):
    def at_script_creation(self) -> None:
        self.key = "population_drain"
        self.interval = settings.POPULATION_DRAIN_INTERVAL_SECONDS
        self.persistent = True

    def at_repeat(self) -> None:
        if not settings.POPULATION_DRAIN_ENABLED:
            return
        drain_population_backlog(settings.POPULATION_DRAIN_SLICE_SECONDS)
```

Copy the remaining attribute lines (`desc`, `start_delay`, anything else) from `ArtDrainScript.at_script_creation` so both scripts are configured alike. Add to `GLOBAL_SCRIPTS`:

```python
"population_drain": {
    "typeclass": "world.maps.population_drain.PopulationDrainScript",
    "repeats": -1,
    "desc": "Periodic bounded settlement of lagging population units.",
},
```

### D4. Settings

In `server/conf/settings.py`, in a new commented block after the `ART_SCHEDULER_*` block:

```python
POPULATION_DRAIN_ENABLED = _env_bool("POPULATION_DRAIN_ENABLED", True)
POPULATION_DRAIN_INTERVAL_SECONDS = _env_int("POPULATION_DRAIN_INTERVAL_SECONDS", 2)
POPULATION_DRAIN_SLICE_SECONDS = _env_int("POPULATION_DRAIN_SLICE_SECONDS", 600)
```

Use the same helper calls and bounds form as the `ART_SCHEDULER_*` lines (positive integers). Add the three names to `_ENV_OVERRIDES` in `server/conf/test_settings.py`, to `.env.example` (commented, with one line of explanation each, next to the `ART_SCHEDULER_*` entries) and to the table of `docs/development/settings-and-environment.md` in that file's language.

The slice is game seconds. 600 equals `monster_activity.RESTING_DECISION_INTERVAL`, so one slice of a resting unit holds about one decision per group.

### D5. Tests

New `world/maps/tests/test_population_drain.py` on `ActivityFixture` with the two-zone synthetic world; make units lag by setting the world tick forward and writing the cursor record directly.

- Scenarios of the four requirements. "Drain to completion" loops `while drain_population_backlog(600): pass` with a hard iteration cap of 200 that fails the test when reached, and compares `settlement_projection` with a rebuilt world settled by `settle_population_lifecycle`.
- Events: patch `world.maps.population_drain.log_info` / `log_error`, with `self.captureOnCommitCallbacks(execute=True)` for the info event.
- Failure: `patch.object(regional_population, "record_population_transition", side_effect=RuntimeError)` for one run.
- Periodic caller: instantiate nothing through the reactor. Call `PopulationDrainScript.at_repeat` on an object created with `evennia.utils.create.create_script(PopulationDrainScript, obj=None, autostart=False)` (or, if creation starts a timer, call the unbound method with a `unittest.mock.Mock()` as `self`), under `override_settings(POPULATION_DRAIN_ENABLED=False)` and `True`, with `drain_population_backlog` patched by `wraps=`.
- The environment tests: run the existing package; add the three names where its inventory fixture lists names, following the entries for `ART_SCHEDULER_*`.

No test starts the script's timer and no test sleeps.

### D6. Documentation and amendment

- `docs/development/regional-monster-population.md`: section "Background drain": selection order, slice, atomicity, failure behaviour, settings, and how to drain by hand from a shell (`drain_population_backlog(600)`).
- `docs/superpowers/specs/2026-09-02-observability-logging-design.md` §4.2: rows for `population_backlog_drained` (`units`, `tick_from`, `tick_to`, `remaining`) and `population_backlog_drain_failed` (`units`, `tick_from`, `tick_to` + `exc`, error level).
- `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §6.5: blockquote `> **Amended 2026-11-14 (change population-backlog-drain).**` stating that a periodic server task settles lagging population units up to, never past, the current world tick; it materialises game time that already elapsed through player actions, moves no clock, and yields the same state as immediate settlement, so decision D4 stands.

## Risks / Trade-offs

- [A player advances game time faster than the drain pays it off (a long sleep), then travels at once into another unit] → that unit's remaining lag is paid synchronously by the movement's catch-up; the drain does not bound it. The backlog is finite and shrinks in real time while the player reads or idles. The defaults pay 300 game seconds per real second per lagging set; both numbers are settings.
- [More than three sets fail permanently and the sets behind them are never reached] → every failure is an error event with its tick range; the failing units' writers refuse by `PopulationUnitNotCurrent` and an observing player gets the catch-up error event. Three attempts per run bound the cost of one repeat.
- [A drain transaction delays a command that arrives during it] → one slice of one closed set; the slice setting bounds it.
- [Saves taken at different real times hold different cursor records for the same played history] → game-visible outcomes are equal after catch-up; only the materialisation point differs. Stated in the D6 amendment.
