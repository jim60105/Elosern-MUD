# Design

## Context

See proposal.md - Why. Facts (symbols from commit `f9925e49` and from earlier changes of the chain):

- `population_lifecycle.register_regional_population()` registers `settle_population_lifecycle` (stage), `snapshot_population_lifecycle_surfaces` (registry contract) and `next_population_lifecycle_boundary` (forecast) under `STAGE_KIND`.
- `population_lifecycle._run_pass(wilderness, scope, start_tick, end_tick, *, contact)` runs one pass; `scope=None` is the whole world.
- `population_units`: `observed_units(wilderness)`, `build_scope`, `scope_start_tick`, `unit_closure`, `PopulationScope`, `read_unit_cursors`, `unit_cursor`, `current_unit_index`, `RESIDUAL_UNIT`.
- `monster_activity.snapshot_activity_surfaces(wilderness, *, member_ids=None)` already narrows to given member ids. `monster_sites.snapshot_monster_site_surfaces(start_tick, end_tick)` iterates `MONSTER_SITE_REGISTRY`.
- `regional_population._living_monsters()` enumerates every `Monster` row; `_coordinate_registration(wilderness)` is the in-memory map of registered entity → cell; `reused_living_presence()` holds the pass-scoped facts (`settlement-decode-reuse`).
- `population_forecast.capture_activity_snapshot(*, start_tick)` captures groups, journeys, zones, sites and protection for `project_activity_window`.
- Many existing tests call `settle_population_lifecycle(start, end)` directly and expect the whole world to settle. Some advance the clock with the stage registered through `ActivityFixture._register_lifecycle()` and no player character.
- Design documents that describe the simulation: `2026-11-03-monster-field-behaviour-and-escape-design.md` §1 row "Simulation" ("Global due events driven by game time, including unobserved areas; no wall-clock simulation or player-proximity freeze") and §5.2; `2026-11-03-regional-monster-population-design.md`; `2026-07-29-ai-mud-engine-design.md` D4 and §6.5.

## Goals / Non-Goals

**Goals:**

- The stage, its registry contract and its forecast all use one observed scope.
- `settle_population_lifecycle` keeps its whole-world meaning as a function.

**Non-Goals:**

- No background work (next change).
- No change to unit resolution, scoped owner filters, catch-up, entry points or writers.
- No narrowing of the activity record decode and store, or of the coordinate map scan: they remain one whole-record operation per pass (D7 records this limit).
- No world-save code change.

## Decisions

### D1. Observed pass

Add to `population_units.py`:

```python
def closed_sets(index: UnitIndex, state: MonsterActivityState, seeds: Iterable[str]) -> tuple[frozenset[str], ...]
```

the distinct closures of the seeds, each a `frozenset`, sorted by their smallest unit identifier.

Add to `population_lifecycle.py`:

```python
def settle_observed_population(start_tick: int, end_tick: int) -> list[ScheduledEvent]:
    """The clock stage: settle the observed units through ``end_tick``."""
```

1. Resolve the wilderness; return `[]` when absent or not provisioned (as today).
2. `seeds = population_units.observed_units(wilderness)`.
3. For each set of `closed_sets(...)` whose `scope_start_tick` is below `start_tick`: `_run_pass(wilderness, build_scope(wilderness, set), cursor, start_tick, contact=False)`; collect its events.
4. `scope = build_scope(wilderness, seeds)`; `_run_pass(wilderness, scope, start_tick, end_tick, contact=True)`; collect its events. When step 3 left every set at `start_tick`, `scope_start_tick(scope)` equals `start_tick`; a mismatch raises `PopulationScopeCursorMismatch` (fail closed).
5. Return the events.

A set whose cursor is above `start_tick` cannot exist (cursors never pass the world tick); if one is found raise `PopulationScopeCursorMismatch`.

`register_regional_population()` registers `settle_observed_population` as the stage. `settle_population_lifecycle` is unchanged and stays in `__all__`.

### D2. Registry contract

`snapshot_population_lifecycle_surfaces(start_tick, end_tick, *, scope=None)`:

- When `scope is None`: compute `scope = build_scope(wilderness, observed_units(wilderness))`; the wilderness-absent and unprovisioned cases return what they return today.
- Regional surfaces: unchanged (wilderness attributes only).
- Activity surfaces: `monster_activity.snapshot_activity_surfaces(wilderness, member_ids=<sorted member ids of groups in scope.group_ids and of journeys of those groups>)`.
- Site surfaces: `monster_sites.snapshot_monster_site_surfaces(start_tick, end_tick, scope=scope)`, which iterates only `scope.site_keys`.

`ensure_population_current` passes its own scope. A world pass through `settle_population_lifecycle` outside an advance has no registry, as today.

### D3. Scoped living scan

`regional_population.reused_living_presence(scope=None)` stores the scope in `_PresenceReuse`. When a scope is stored, the fill of `reuse.living` uses:

```python
def _scope_living_monsters(wilderness, scope) -> tuple[Monster, ...]
```

ids = member ids of every group in `scope.group_ids` (from `read_monster_activity`) plus every `Monster` key of `_coordinate_registration(wilderness)` whose cell satisfies `scope.covers_cell(cell)`; rows = `Monster.objects.all_family().filter(pk__in=ids)`; keep `persisted_hp(row) > 0`; sort by `pk`. `_run_pass` opens `reused_living_presence(scope=scope)`. With `scope=None` the scan is unchanged.

Assumption, stated in D7 and in the docs: every living home-owned individual is a member of a group or is registered on a cell. Every construction path since `global-monster-activity` forms a group, and the scoped differential tests include wave births and site births.

### D4. Forecast

`population_forecast.capture_activity_snapshot(*, start_tick, scope=None)`: after the function has built its group, journey, zone and site snapshots, drop every group not in `scope.group_ids`, every journey of a dropped group, every zone not in `scope.zone_keys` and every site not in `scope.site_keys` when a scope is given. `next_population_lifecycle_boundary` passes `build_scope(wilderness, observed_units(wilderness))`. Field observers always stand inside the observed units, and at a boundary query every observed unit is current (the previous advance left it so; the command pre-hook guarantees it otherwise), so the answer equals the whole-world projection.

### D5. New tests

New `world/maps/tests/test_observed_unit_advance.py` on `ActivityFixture`, with the two-zone synthetic world and the player placement helper of `test_population_catch_up.py`; the stage is registered with `self._register_lifecycle()`; advances are `get_world_clock().advance(seconds, AdvanceSource.COMMAND, [])`.

- First requirement: four scenarios; "Rollback" registers a failing synthetic source after the stage.
- Second requirement: `run(observed)`; the reference world calls `population_lifecycle.settle_population_lifecycle(tick, tick + seconds)` for the same three intervals with the clock tick set by hand; the observed world advances the clock three times and then calls `catch_up_world(self.wilderness)`.
- Third requirement: `CaptureQueriesContext` statement count; `patch.object(monster_activity, "plan_group_decision", wraps=...)` group ids; `patch.object(monster_activity, "snapshot_activity_surfaces", wraps=...)` and the length of the `member_ids` argument. The two worlds differ only in the number of groups built in the far zone.
- Fourth requirement: `patch.object(population_forecast, "project_activity_window", wraps=...)` to read the captured snapshot's groups; the whole-world answer comes from calling `project_activity_window` with a `capture_activity_snapshot(start_tick=...)` taken with no scope.

Add to `world/maps/tests/_settlement_projection.py`:

```python
def catch_up_world(wilderness) -> None:
    """Catch every unit up to the current tick (test helper)."""
```

It calls `population_lifecycle.ensure_population_current(wilderness, {unit})` for `RESIDUAL_UNIT` and every unit of `current_unit_index()` (zones and areas), in sorted order.

### D6. Existing tests

Run the modules listed in tasks 3.x. A test fails because of this change only when it advances the clock through the registered stage and then asserts state of groups no player observes. Fix such a test by calling `catch_up_world(self.wilderness)` after the advance and before the assertions. Do not weaken an assertion, do not place a player to make a test pass, and do not change production code for a test. A test that asserts an *event returned by the advance* for an unobserved group (`ScheduledEvent` kinds such as `monster_arrived`) is changed to call `settle_population_lifecycle` directly, because the advance no longer returns that event; record every such test in the hand-off.

### D7. Documentation and design amendments

Each amendment is a dated blockquote `> **Amended 2026-11-14 (change observed-unit-advance).**` placed directly under the amended text; the original text stays.

- `docs/superpowers/specs/2026-11-03-monster-field-behaviour-and-escape-design.md`, under the "Confirmed decisions" table of §1 and under §5.2: unobserved groups still decide and travel on game time with outcomes independent of the player's position and of when they are computed; the computation is deferred per settlement unit until the unit is observed, an entry point needs it, or the background drain reaches it; there is still no wall-clock simulation and no proximity freeze of outcomes.
- `docs/superpowers/specs/2026-11-03-regional-monster-population-design.md`, under its timing rule (the section containing "equal clock advancement partitions preserve due-wave outcomes"): due waves of an unobserved zone are computed at catch-up with their original due ticks.
- `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` §6.5: a clock advance settles the party and the observed population units; other units keep their own settled-through tick; decision D4 is unchanged.
- `docs/development/regional-monster-population.md`: section "Observed-only advance" with D1-D4, the D3 assumption, the remaining whole-record operations (activity record decode and store, coordinate map scan) and the statement that a world save stores the cursor record and needs no flush.
- `docs/development/monster-field-behaviour.md`: in the section "Global Monster Activity", one paragraph pointing to the section above.

## Risks / Trade-offs

- [A unit unobserved for a long game time is caught up in one long step when first observed] → bounded by `population-backlog-drain`, the next change of the chain; until then the lag of a unit is at most the game time since this change was deployed.
- [The stored activity record and the coordinate map are still decoded, scanned and stored whole once per pass] → a constant number of whole-record operations per advance, independent of how many boundaries unobserved units have; recorded in the docs as the remaining world-size term.
- [A registry edit renames a unit; the renamed unit falls back to the record's default cursor, which no longer moves] → the unit is caught up from that older tick with its current state; outcomes stay lawful but include extra elapsed time. Documented in "Observed-only advance".
- [An existing test silently loses meaning when changed per D6] → D6 forbids weakening and requires listing every test moved to the direct call.

## Migration Plan

No data step. A world saved before this change has every unit at the same tick. Rollback: revert the change; the whole-world stage accepts units with different cursors only through `settle_population_lifecycle`, so before rolling back run one catch-up of every unit (`catch_up_world` logic from a shell).
