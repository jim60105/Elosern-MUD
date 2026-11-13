# Design

## Context

See proposal.md - Why. Facts verified at commit `f9925e49` (re-locate by symbol name), plus earlier changes of the chain:

- `world/rules/clock.py::WorldClock.advance` builds a registry, sets the registry-held flag (`settlement-outer-rollback` D2), runs the stages in `transaction.atomic()`, and on failure calls `_restore_clock_tick` and `_restore_advance_registry(registry, scope)`.
- `population_lifecycle.snapshot_population_lifecycle_surfaces(start_tick, end_tick)` is the union snapshot contract of the three owners. `population_lifecycle.settle_population_scope(wilderness, seeds, end_tick, *, contact=False)` exists (`unit-scoped-population-settlement` D3).
- `regional_population.current_population_tick()` returns the world tick; `live_wilderness()` the wilderness script or `None`; `population_provisioned(wilderness)`.
- `world/rules/sight.py::MAX_GROUND_SIGHT_RADIUS = 8`. `world/rules/movement_edges.py::location_ref(entity)` gives a `LocationRef` or raises `LocationRefError`/`ValueError`.
- `_active_session_protection` already enumerates players with `typeclasses.characters.PlayerCharacter.objects.all_family()`.
- `commands/command.py::at_pre_cmd` emits `cmd_in` for every command.
- Call sites: `world/quests/materializer.py` calls `register_explicit_individual` (near line 342); `world/maps/gm.py` calls it (near line 60) and removes an individual (near lines 92-156); `world/quests/runtime.py` calls `site_living_members(objective.site_key)` (near line 709); `monster_activity.commit_monster_departure(wilderness, plan)` is the escape departure writer; `world/rules/movement_settlement.py` settles a movement edge and calls the clock.
- `web/gm/readers/monsters.py::placement_section(monster)` returns `{"rows": [{"label": ..., ...}]}`; `world/maps/tests/test_monster_activity.py` asserts its labels.
- An escape destination is adjacent to the battle cell, which is within sight of the fighting player, so it is always inside the observed units.

## Goals / Non-Goals

**Goals:**

- One catch-up function with the same rollback strength as a clock advance.
- Fail-closed writers.

**Non-Goals:**

- The clock stage still settles the whole world; this change does not make any unit lag.
- No background work.
- No catch-up from a GM view, from `population_view`, or from any pure read other than the quest site-target read named above.
- No new command, no player-facing text.

## Decisions

### D1. Shared registry scope in the clock

In `world/rules/clock.py` add:

```python
@contextmanager
def held_advance_registry() -> Iterator[None]:
    """Mark that the caller holds a restore registry for everything the enclosed stages write."""


def restore_advance_registry(registry: dict[int, SurfaceSnapshot], entities: Iterable[Any] = ()) -> None:
    """Public name of the advance restore for another registry owner."""
```

`held_advance_registry` sets and restores the flag behind `advance_registry_held()`; `WorldClock.advance` uses it instead of setting the flag inline. `restore_advance_registry` calls `_restore_advance_registry`.

### D2. Catch-up

In `world/maps/population_lifecycle.py`:

```python
def ensure_population_current(wilderness, seeds: Iterable[str]) -> bool:
    """Catch the closed set around ``seeds`` up to the current tick; True when it settled anything."""
```

1. Return `False` when `wilderness is None`, not provisioned, or `population_units.pass_running()` (D5).
2. `scope = build_scope(wilderness, seeds)`; `start = scope_start_tick(wilderness, scope)`; `now = regional_population.current_population_tick()`; return `False` when `start >= now`.
3. `registry = snapshot_population_lifecycle_surfaces(start, now)`.
4. Inside `try:` → `with held_advance_registry(), transaction.atomic():` call `settle_population_scope(wilderness, scope.units, now, contact=False)` and schedule `transaction.on_commit(lambda: log_info("population_caught_up", context={"units": len(scope.units), "tick_from": start, "tick_to": now}))`.
5. `except Exception:` → `restore_advance_registry(registry)`; `raise`.
6. Return `True`.

Helpers in the same module:

```python
def ensure_locations_current(locations: Iterable[LocationRef]) -> bool   # seeds = units_around(location) for each
def ensure_observed_population_current() -> bool                         # seeds = population_units.observed_units(wilderness)
```

Both resolve `regional_population.live_wilderness()` themselves.

### D3. Observed units

In `world/maps/population_units.py`:

```python
OBSERVATION_RADIUS = MAX_GROUND_SIGHT_RADIUS   # imported from world.rules.sight

def units_around(index: UnitIndex, location: LocationRef | None) -> frozenset[str]
def announced_observation(locations: Iterable[LocationRef]) -> ContextManager[None]
def observed_units(wilderness) -> frozenset[str]
```

- `units_around`: `{RESIDUAL_UNIT}` for `None` or a room; for a wilderness locator the units of every cell `(x + dx, y + dy)` with `-R <= dx, dy <= R` and non-negative coordinates, plus `RESIDUAL_UNIT`.
- `announced_observation` appends the locations to a module-level list for the duration of the block and removes exactly those entries in `finally`.
- `observed_units`: union of `units_around` for `location_ref(player)` of every `PlayerCharacter.objects.all_family()` (skip a player whose locator raises, with an `# observability: ignore R2:` reason) and for every announced location. The wilderness argument filters wilderness locators to `location.map == wilderness.db_key`.

### D4. Entry points

- `commands/command.py::at_pre_cmd`: after the `cmd_in` event, call `ensure_observed_population_current()` inside `try/except Exception as error:` that emits `log_error("population_catch_up_failed", exc=error, context={"char": char, "cmd": self.key})` and continues. Import inside the method to keep command import order unchanged.
- `world/rules/movement_settlement.py`: in the function that settles one committed edge (find it with `grep -n "advance_bounded\|build_advance_snapshot_registry" world/rules/movement_settlement.py`), before the registry is built and before any transaction opens, call `ensure_locations_current([destination])`, and wrap the rest of the edge settlement in `with announced_observation([destination]):`, where `destination` is the edge's destination `LocationRef`.
- `world/quests/materializer.py` and `world/maps/gm.py` (placement): before the transaction that contains `register_explicit_individual`, call `ensure_locations_current([LocationRef.wilderness(name, x, y)])` for the target cell, using the wilderness and cell the call site already resolved through `regional_population.wilderness_registration_target`.
- `world/maps/gm.py` (removal): before `snapshot_population_surfaces`, call it for the entity's `location_ref`.
- `world/quests/runtime.py`: before `site_living_members(objective.site_key)`, call `ensure_population_current(wilderness, {population_units.site_unit(index, objective.site_key)})`.

Each call must sit outside the caller's own `transaction.atomic()` and before its own snapshot. If a call site can only be reached inside an enclosing transaction opened by another function, move the call to that function's start; if that is not possible within the listed files, stop and report the call chain.

### D5. Writers refuse a lagging unit

In `population_units.py`:

```python
class PopulationUnitNotCurrent(RegionalPopulationError): ...

def pass_running() -> bool            # True inside _run_pass (set by population_lifecycle._run_pass, scope or not)
def require_current(wilderness, locations: Iterable[LocationRef | None]) -> None
```

`require_current` returns at once when `pass_running()` or the wilderness is not provisioned or has no cursor record; otherwise, for each non-`None` location, it raises `PopulationUnitNotCurrent` naming the unit, its cursor and the world tick when `unit_cursor(...) < regional_population.current_population_tick()`.

Call it as the first statement after argument validation in:

- `regional_population.register_explicit_group` (the target cell);
- `regional_population.record_population_transition` (the `before` and `after` positions, converted with `LocationRef.wilderness(position.wilderness, position.x, position.y)`);
- `regional_population.record_population_protection` (the cell);
- `monster_activity.commit_monster_departure` (the plan's source and destination).

`population_lifecycle._run_pass` sets the `pass_running` flag for its duration (a module global in `population_units` with a context manager `running_pass()`).

### D6. GM view

In `web/gm/readers/monsters.py::placement_section`, when the wilderness is provisioned and the monster has an actual cell, append one row `{"label": "結算進度", "value": <cursor>}` and, when the cursor is below `current_population_tick()`, a second row `{"label": "結算落後", "value": <world tick - cursor>}`. Use the row shape the function already uses for its other rows (copy the keys of the existing "下一次決策" row). The function performs reads only.

### D7. Tests

New `world/maps/tests/test_population_catch_up.py` on `ActivityFixture` with the two-zone synthetic world of `test_scoped_population_settlement.py` (import its builder; if it is a method, move it to a module-level helper in that file first).

- To make a unit lag in a test, set the world tick forward (`get_world_clock().tick = 700`) while the cursor record stays at 100.
- Catch-up scenarios: compare with `settle_population_scope` on a rebuilt world; patch `world.maps.population_lifecycle.log_info`; fault injection as in `test_settlement_outer_rollback.py`.
- Observed units: create player characters with the fixture's existing player helper (or `create_object(PlayerCharacter, ...)`) and place them by writing the wilderness coordinate registration the way the fixture places monsters.
- "Command after an untracked relocation" and "Failed catch-up before a command": call `Command.at_pre_cmd` on an instance of `commands.command.Command` with `caller` set, patching `commands.command.log_error` and, for the failure, `world.maps.population_lifecycle.ensure_population_current` with `side_effect=RuntimeError`.
- "Movement into a lagging unit": use the movement test helper of `world/rules/tests/test_world_escape.py` or `world/rules/tests/test_movement_settlement*.py` (find it with `grep -ln "charge_movement\|settle_movement" world/rules/tests`); assert with a `wraps=` patch that `ensure_population_current` returned `True` before `WorldClock.advance` was entered.
- Writers: the four writers, lagging, current, and inside `running_pass()`.
- GM view: extend the existing `placement_section` label test in `world/maps/tests/test_monster_activity.py` with the two new labels for a lagging unit and assert the cursor is unchanged after the read.

### D8. Documentation

- `docs/development/regional-monster-population.md`: section "Catch-up and observed units" with D2-D5 and the rule: any new code that writes population state for a cell, or reads it to decide something, calls `ensure_locations_current` before its own transaction.
- `docs/superpowers/specs/2026-09-02-observability-logging-design.md` §4.2: rows for `population_caught_up` (`units`, `tick_from`, `tick_to`) and `population_catch_up_failed` (`char`, `cmd` + `exc`, error level), in the file's language.

## Risks / Trade-offs

- [A population entry point is missing from D4] → its writer raises `PopulationUnitNotCurrent` (D5) instead of corrupting state; a pure read that is missing shows the unit's last settled state, which the next command corrects.
- [A catch-up runs inside an enclosing transaction that later rolls back, leaving caches ahead of the database] → D4 places every call before the caller's transaction; the rule is documented in D8.
- [A catch-up of a unit that lagged for a long game time is slow] → `population-backlog-drain` bounds the lag; until `observed-unit-advance` merges no unit lags at all.
