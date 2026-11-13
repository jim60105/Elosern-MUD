# Design

## Context

See proposal.md - Why. Facts (symbols from commit `f9925e49` and from earlier changes of the chain):

- `regional_population._living_monsters()` returns every `Monster.objects.all_family()` row with `persisted_hp(row) > 0`, sorted by primary key.
- `regional_population._living_presence(wilderness)` builds one `PopulationPresence` per living individual; inside `reused_living_presence()` the individuals come from `_PresenceReuse.living` (`settlement-decode-reuse` D3).
- `regional_population._coordinate_registration(wilderness)` is the read-only in-memory map of registered entity → cell.
- `population_lifecycle._run_pass(wilderness, scope, start_tick, end_tick, *, contact)` opens `regional_population.reused_living_presence()`.
- `PopulationScope` has `group_ids` and `covers_cell(cell)`; `read_monster_activity(wilderness).groups[group_id].member_ids` lists members.
- Zone counts (`counts_from_presence`, `zone_counts_from_presence`) use, per zone, the individuals standing on the zone's cells and the individuals whose home is the zone. By the unit closure, a home-owned individual standing elsewhere is a member of a group of the scope.

## Goals / Non-Goals

**Goals:**

- One narrower enumeration, used only when a pass has a scope.

**Non-Goals:**

- No change to `_living_monsters`, to `presence_at` callers outside a pass, to the forecast, to the activity record or to the coordinate registration.
- No new cache.

## Decisions

### D1. Scoped enumeration

In `world/maps/regional_population.py`:

```python
def _scope_living_monsters(wilderness, scope) -> tuple[Monster, ...]
```

1. `ids` = every member id of every group of `read_monster_activity(wilderness).groups` whose id is in `scope.group_ids`.
2. Add `entity.pk` for every key of `_coordinate_registration(wilderness)` that is a `Monster` instance and whose cell satisfies `scope.covers_cell(cell)`.
3. `rows = Monster.objects.all_family().filter(pk__in=sorted(ids))`.
4. Return the rows with `persisted_hp(row) > 0`, sorted by `pk`.

`reused_living_presence(scope=None)` stores the scope in `_PresenceReuse` (new field `scope: Any = None`). Where `settlement-decode-reuse` D3 fills `reuse.living` from `_living_monsters()`, use `_scope_living_monsters(wilderness, reuse.scope)` when `reuse.scope is not None`. `forget_living_presence()` keeps the scope and clears the rest, as today.

`population_lifecycle._run_pass` opens `reused_living_presence(scope=scope)`.

### D2. Stated assumption

An individual that has a home zone but is neither a member of a group nor registered on a cell is not enumerated by a scoped pass. No construction path creates one: zone births, site births and explicit registration all register the individual and form a group. The whole-world pass still finds it. State this in the documentation section of D4.

### D3. Tests

New `world/maps/tests/test_observed_unit_read_narrowing.py` on `ActivityFixture` with `build_two_zone_world`, `place_player`, `settlement_projection` and `catch_up_world`.

- First three scenarios: build the scope with `population_units.build_scope`, read `presence_at(wilderness, at_tick=...)` inside `with regional_population.reused_living_presence(scope=scope):` and outside any scope, and compare `counts_from_presence` for the zone. The ungrouped individual is created with `construct_species_individual`, given `db.home_ecology_zone`, and written into `wilderness.db.itemcoordinates`.
- "Results are unchanged": `run(narrow)`; `narrow=False` patches `regional_population._scope_living_monsters` to `lambda wilderness, scope: regional_population._living_monsters()`.
- "Growing the far zone": `CaptureQueriesContext(connection)` around `get_world_clock().advance(seconds, AdvanceSource.COMMAND, [])`; the two worlds differ only in the far zone's groups. Warm both worlds identically before capturing (one zero-second advance) so that first-read attribute loads do not differ.

### D4. Documentation

In `docs/development/regional-monster-population.md`, section "Observed-only advance": the scoped enumeration, the assumption of D2, and the remaining whole-record operations named in the proposal.

## Risks / Trade-offs

- [The statement-count scenario still differs because another whole-world read exists that this design did not find] → the failing test names the extra statements; narrow that read in the same way if it is inside `world/maps/regional_population.py` or `world/maps/population_lifecycle.py`, otherwise stop and report the statements.
- [An ungrouped, unregistered home-owned individual is missed] → D2; no construction path creates one.
