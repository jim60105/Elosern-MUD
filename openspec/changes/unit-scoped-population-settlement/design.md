# Design

## Context

See proposal.md - Why. Facts verified at commit `f9925e49` (re-locate by symbol name), plus the modules added by earlier changes of the chain:

- `world/maps/population_lifecycle.py`: `settle_population_lifecycle(start_tick, end_tick)` runs the pass; `_settle_population_at(wilderness, tick, contact_tick=...)` is one boundary; `_next_population_boundary(wilderness, tick, end_tick)` merges the candidates; `_zone_keys(wilderness)` returns `regional_population.initialized_zone_keys`.
- Owner steps a pass calls:
  - `monster_activity.settle_monster_activity_at(wilderness, tick)` → `_settle_due_journeys` (iterates `state.journeys`);
  - `monster_activity.settle_group_decisions_at(wilderness, tick)` (iterates `state.groups`);
  - `monster_activity.settle_idle_physiology(wilderness, tick)` (iterates `state.groups`);
  - `monster_activity.next_monster_activity_boundary(wilderness, after, end)`;
  - `monster_activity.retire_room_protection(wilderness, tick)`, `retire_settled_decision_receipts(wilderness, tick)`;
  - `regional_population.note_population_boundaries(wilderness, zone_keys, tick=...)`, `due_recovery_zone_keys(wilderness, tick=...)`, `settle_recovery_due(wilderness, zone_key, tick=...)`, `settle_timeline_through(wilderness, tick, retain=...)`, `presence_fingerprint`;
  - `monster_sites.settle_monster_sites_at(tick)`, `next_site_boundary(start_tick, end_tick)`, `retained_loss_ids(wilderness)`; all three iterate `MONSTER_SITE_REGISTRY`.
- `regional_population.PopulationTransition` has `source_id`, `individual_id`, `occurred_tick`, `before`, `after`; `PopulationPresence` has `alive`, `position` (`PopulationPosition(wilderness, x, y)` or `None`), the home zone key and the site key. `PopulationProtection` has `cell`, `start_tick`, `end_tick`.
- `PopulationTimeline.settled_through_tick` is read in exactly one place: the early return of `settle_timeline_through`.
- `MonsterActivityState.settled_through_tick` is only ever raised with `max(...)`.
- `population_units` (from `population-settlement-units`): `UnitIndex`, `current_unit_index`, `unit_of_location`, `group_units`, `site_unit`, `unit_closure`, `read_unit_cursors`, `unit_cursor`, `advance_unit_cursors`, `RESIDUAL_UNIT`.
- Test helpers: `ActivityFixture` (`world/maps/tests/test_monster_activity.py`), `settlement_projection` (`world/maps/tests/_settlement_projection.py`).

## Goals / Non-Goals

**Goals:**

- One optional `scope` argument through the pass. `scope=None` is byte-for-byte today's whole-world path.
- A differential test that would fail if any owner step read state of another unit.

**Non-Goals:**

- The clock stage, the advance snapshot registry, `population_forecast.py` and `world/rules/field_contact.py` are not edited.
- No narrowing of the living-individual scan or of the activity record write (they stay whole-world reads here; `observed-unit-advance` narrows the scan).
- No catch-up entry point and no background work.

## Decisions

### D1. Scope object

Add to `world/maps/population_units.py`:

```python
class PopulationScopeViolation(RegionalPopulationError): ...


@dataclass(frozen=True, slots=True)
class PopulationScope:
    units: frozenset[str]
    group_ids: frozenset[str]
    zone_keys: tuple[str, ...]      # initialized zones of the scope, sorted
    site_keys: frozenset[str]
    start_ticks: Mapping[str, int]  # unit id -> its cursor when the scope was built

    def behind(self, tick: int) -> "PopulationScope": ...   # same scope, zones and sites limited to units with start_ticks[unit] < tick
    def covers(self, location: LocationRef | None) -> bool: ...
    def covers_cell(self, cell: tuple[int, int]) -> bool: ...


def build_scope(wilderness, seeds: Iterable[str]) -> PopulationScope
def scope_start_tick(wilderness, scope: PopulationScope) -> int
def active_scope() -> PopulationScope | None
def scoped(scope: PopulationScope | None) -> ContextManager[None]
def require_in_active_scope(location: LocationRef) -> None
```

- `build_scope`: `units = unit_closure(index, read_monster_activity(wilderness), seeds)`; `group_ids` = groups whose `group_units` is a subset of `units` (by closure, intersecting implies subset); `zone_keys` = `regional_population.initialized_zone_keys(wilderness)` filtered by `index.unit_of_zone[key] in units`; `site_keys` = registry sites with `site_unit(index, key) in units`.
- `covers(location)`: `unit_of_location(index, location) in units`; `None` is covered.
- `start_ticks` = `unit_cursor` of every unit of `units`, read once in `build_scope`.
- `scope_start_tick`: `min(scope.start_ticks.values())`. Units of one closed set normally share one cursor; they differ only when a group linked them after they diverged (an escape into another unit, an explicit registration). That state is lawful and D3 settles it.
- `behind(tick)`: a copy whose `zone_keys` and `site_keys` keep only zones and sites of units with `start_ticks[unit] < tick`; `units`, `group_ids` and `start_ticks` are unchanged.
- `require_units_in_active_scope(units: Iterable[str]) -> None`: no active scope → return; else raise `PopulationScopeViolation` when any unit is outside `active_scope().units`.
- `scoped` sets a module global read by `active_scope`, restores the previous value in `finally`.
- `require_in_active_scope`: no active scope → return; else raise `PopulationScopeViolation` when not covered.

`RegionalPopulationError` is imported from `regional_population`; to avoid an import cycle keep `population_units` importing `regional_population` and never the reverse at module level (owners import `population_units` inside functions).

### D2. Owner filters

Every function below gains a keyword-only `scope: PopulationScope | None = None`. With `None` its behaviour is unchanged.

`world/maps/monster_activity.py`:

- `settle_monster_activity_at` → passes to `_settle_due_journeys`, which skips a journey whose `group_id not in scope.group_ids`.
- `settle_group_decisions_at`, `settle_idle_physiology`: skip a group not in `scope.group_ids`.
- `next_monster_activity_boundary`: skip journeys and groups not in scope.
- `retire_room_protection`: with a scope, do nothing unless `RESIDUAL_UNIT in scope.units`.
- `retire_settled_decision_receipts`: with a scope, retire only receipts whose `group_id in scope.group_ids`, or whose group no longer exists when `RESIDUAL_UNIT in scope.units`.
- `_begin_group_journey`: call `population_units.require_in_active_scope(destination)` before the first write. `_arrive`: the same for the arrival destination.
- `create_group`: after the new `MonsterGroup` value is built and before `_write_state`, call `population_units.require_units_in_active_scope(group_units(current_unit_index(), new_group, None))`.

`world/maps/regional_population.py`:

- `due_recovery_zone_keys(wilderness, *, tick, scope=None)`: filter by `scope.zone_keys`.
- `settle_timeline_through(wilderness, tick, *, retain=frozenset(), scope=None)`: D4.
- `_commit_planned_wave`: `require_in_active_scope(LocationRef.wilderness(name, *placement.cell))` before its transaction.

`world/maps/monster_sites.py`:

- `settle_monster_sites_at(tick, *, scope=None)`, `next_site_boundary(start_tick, end_tick, *, scope=None)`, `retained_loss_ids(wilderness=None, *, scope=None)`: iterate only registry sites with `key in scope.site_keys`.
- `_populate`: `require_in_active_scope` for the site cell before its first write.

### D3. Coordinator

In `population_lifecycle.py`:

- `_settle_population_at(wilderness, tick, *, contact_tick, scope)`: `step = None if scope is None else scope.behind(tick)`; `zone_keys = step.zone_keys if step is not None else _zone_keys(wilderness)`; pass `scope=step` to the `regional_population` and `monster_sites` calls of D2 and `scope=scope` to the `monster_activity` calls. A unit that already passed `tick` therefore gets no zone note, no recovery and no site step at that tick, while its groups are still visited and skip themselves through `next_decision_tick`, the journey due tick and each member's `settled_through_tick`. The contact block runs only when `contact_tick is not None` (unchanged condition).
- `_next_population_boundary(wilderness, tick, end_tick, scope)`: pass `scope` to the two owner queries; keep a timeline transition candidate only when `scope is None` or the transition concerns the scope (D4 `concerned_units(...) & scope.units`); keep a protection candidate only when `scope is None or scope.covers_cell(...)`; keep a zone due candidate only when `scope is None or key in scope.behind(candidate_tick).zone_keys`; pass `scope.behind(tick + 1)` to `next_site_boundary`.
- Extract the body of `settle_population_lifecycle` into:

```python
def _run_pass(wilderness, scope, start_tick, end_tick, *, contact: bool) -> list[ScheduledEvent]
```

  It is today's `with ...:` block and loop, with `contact_tick=end_tick if contact else None`, `scope` passed down, wrapped in `population_units.scoped(scope)`, and ending with `advance_unit_cursors(wilderness, None if scope is None else scope.units, end_tick)`.
- `settle_population_lifecycle(start_tick, end_tick)` calls `_run_pass(wilderness, None, start_tick, end_tick, contact=True)`.
- New public function:

```python
def settle_population_scope(
    wilderness, seeds: Iterable[str], end_tick: int, *, contact: bool = False
) -> list[ScheduledEvent]:
    """Settle the closed set of units around ``seeds`` from its cursor through ``end_tick``."""
```

  `scope = build_scope(wilderness, seeds)`; `start = scope_start_tick(wilderness, scope)`; when `end_tick <= start` return `[]`; else `_run_pass(wilderness, scope, start, end_tick, contact=contact)`. Add it to `__all__`.

### D4. Timeline retirement by concerned units

Add to `population_units.py`:

```python
def concerned_units(index: UnitIndex, transition: PopulationTransition) -> frozenset[str]
```

the units of `before.position`, `after.position` (through `index.unit_of_cell(regional_population.cell_region(cell), cell)`; `None` positions add nothing) and of each non-empty home zone key in `index.unit_of_zone`. An empty result is `{RESIDUAL_UNIT}`.

`settle_timeline_through` with a scope:

- skip the early return on `timeline.settled_through_tick`;
- compute `cursors = read_unit_cursors(wilderness)`; a unit in `scope.units` counts as settled to `tick`, any other unit to `unit_cursor(cursors, unit)`;
- drop a transition when `occurred_tick <= tick`, its individual is not in `retain`, and every unit of `concerned_units` is settled to at least `occurred_tick`;
- drop a protection interval when `end_tick is not None`, `end_tick < tick` and `scope.covers_cell((cell.x, cell.y))`;
- write the timeline only when something was dropped, with `settled_through_tick = max(old, tick)`.

With `scope=None` the function is unchanged.

### D5. Tests

New `world/maps/tests/test_scoped_population_settlement.py` on `ActivityFixture`, with a module-level helper `build_two_zone_world(fixture)` that later changes import: a synthetic world of two disjoint zones in one region (declare them the way the fixture declares its own zone; if the fixture has a single zone, add the second with `dataclasses.replace(zone, key=..., rectangles=...)` inside the test's registry isolation) and one synthetic site inside the first zone.

- `run(plan)`: `self._reset_activity(tick=100)`, rebuild the scenario, reset the cursor record to `{"default": 100, "units": {}}`, then execute `plan`, a list of `(seeds or None, end_tick)` steps: `None` calls `settle_population_lifecycle(cursor, end_tick)`, otherwise `settle_population_scope(self.wilderness, seeds, end_tick)`; return `settlement_projection(self.wilderness)`.
- "Order and partition": plans `[(None, 1600)]`, `[(A, 1600), (B, 1600)]`, `[(B, 1600), (A, 1600)]`, `[(A, 800), (B, 500), (B, 1100), (A, 1600), (B, 1600)]`. The timeline part of the projection is compared too, because all units end at the same tick.
- "Other units are untouched": project before and after `settle_population_scope(A, 1600)` and compare the sub-projection of unit B's labels; wrap `monster_activity.plan_group_decision` and assert every planned group id belongs to A.
- "Loss recorded ahead of one unit" and "Protection of a lagging cell": write the transition or protection with `regional_population.record_population_transition` / `record_population_protection`.
- "Out-of-scope destination": patch `monster_activity.plan_group_decision` to return an `ActivityDecision` whose edge leads to a cell of zone B while settling A; assert `PopulationScopeViolation`. Run it inside `get_world_clock().advance` is not possible (the stage is whole-world), so assert state equality after the owner's own direct-path restore.
- "Unequal cursors": wrap `regional_population.note_population_boundaries` and `monster_sites.settle_monster_sites_at` and assert the zone keys and scope they received at ticks up to 400.
- "Units linked after diverging": create the linking group with the fixture's `_group` at a cell of zone B with `owner` zone A (or write `home_owner` with `dataclasses.replace` into the stored record) in both worlds at tick 400.
- "Group reaching outside the scope": patch `world.lore.monster_placement.composition_row_bindings` as imported by `regional_population` to return an activity bound to an area of zone B while a wave commits in zone A.
- "Linked units settle together", "Cursor moves only for the scope", "Reload between parts": direct.

### D6. Documentation

Extend the section "Settlement units" of `docs/development/regional-monster-population.md` with: the scope object, the owner filters, evidence retirement, settlement of a closed set with unequal cursors, the named error.

## Risks / Trade-offs

- [An owner step still reads another unit's state and the synthetic scenario does not exercise it] → the scenario contains every category the coordinator merges (journey, idle decision, deficit recovery, site recovery, protection, future loss); a new category must add its case to "Order and partition".
- [A unit ahead of a linked unit is visited again from the lower cursor and a non-idempotent step runs twice] → only zone and site steps are not idempotent by their own cursors, and D3 skips them per unit; the scenario "Units linked after diverging" compares against whole-world settlement.
- [A scoped pass still decodes and stores the whole activity record and scans every living individual once] → accepted here; this is a constant number of whole-world reads per pass, not per boundary. `observed-unit-advance` narrows the scan.
