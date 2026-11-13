# Design

## Context

See proposal.md - Why. Facts (symbols from commit `f9925e49` and from earlier changes of the chain):

- `population_units`: `current_unit_index`, `unit_of_location`, `group_units`, `read_unit_cursors`, `unit_cursor`, `pass_running()`, `RESIDUAL_UNIT`.
- `regional_population.current_population_tick()`, `population_provisioned(wilderness)`, `RegionalPopulationError`.
- Writers and their callers outside the owners (`grep -rn "record_population_transition(\|record_population_protection(\|commit_monster_departure(\|register_explicit_group(" --include='*.py' world commands web server`, tests excluded):
  - `record_population_transition`: `world/rules/action/transaction.py`, `world/rules/combat_session/rounds.py` (combat with the player present), `world/rules/gm.py::_record_hp_transition` and `world/maps/gm.py` (caught up by `population-catch-up-entry-points` D4), `world/rules/movement_settlement.py` (passage announced and caught up), and the owners themselves inside a pass;
  - `record_population_protection`: `world/rules/combat_session/settlement.py` (combat);
  - `commit_monster_departure`: `world/rules/disengage.py` (combat escape; the destination is adjacent to the battle cell and therefore inside the observed units);
  - `register_explicit_group`: `world/maps/monster_sites.py::_populate` (inside a pass), `regional_population.register_explicit_individual` (quest materialisation and GM placement, both caught up).
- A cursor never passes the world tick. During a clock advance the stage raises the observed units' cursors to the end tick before the clock's own tick is raised, so "cursor at least the world tick" holds for observed units during and after the stage.
- `web/gm/readers/monsters.py::placement_section(monster)` returns `{"rows": [...]}`; `world/maps/tests/test_monster_activity.py` asserts its labels (`"活動"`, `"下一次決策"`).

## Goals / Non-Goals

**Goals:**

- One guard function, called by five writers.
- A read-only progress row for operators.

**Non-Goals:**

- No new catch-up call site: if a writer's caller is found that is not covered by the Context list, add the catch-up there in the way `population-catch-up-entry-points` D4 describes and name it in the hand-off; do not weaken the guard.
- No guard inside a running pass.
- No catch-up from the GM view.
- No frontend change: the GM portal renders `rows` generically.

## Decisions

### D1. Guard

In `world/maps/population_units.py`:

```python
class PopulationUnitNotCurrent(RegionalPopulationError): ...


def require_units_current(wilderness, units: Iterable[str]) -> None
def require_current(wilderness, locations: Iterable[LocationRef | None]) -> None
```

`require_units_current` returns at once when `pass_running()` is true or the wilderness is not provisioned. Otherwise it reads the cursor record (a missing record raises the owner's malformed-state error, unchanged) and raises `PopulationUnitNotCurrent`, naming the first offending unit in sorted order, its cursor and the world tick, when `unit_cursor(...) < regional_population.current_population_tick()`.

`require_current` maps each non-`None` location through `unit_of_location` and calls `require_units_current`.

### D2. Writers

Call the guard as the first statement after argument validation, before any read that could raise for another reason and before any write:

- `regional_population.register_explicit_group`: `require_current(wilderness, [target cell locator])`.
- `monster_activity.create_group`: `require_units_current(wilderness, group_units(index, new_group, None))`, placed where `unit-scoped-population-settlement` D2 placed `require_units_in_active_scope` (the guard is a no-op inside a pass, the scope check is a no-op outside one).
- `regional_population.record_population_transition`: the `before` and `after` positions, each converted with `LocationRef.wilderness(position.wilderness, position.x, position.y)`; a position of another wilderness name is skipped.
- `regional_population.record_population_protection`: the cell.
- `monster_activity.commit_monster_departure`: the plan's source and destination locators.

### D3. GM view

In `web/gm/readers/monsters.py::placement_section`, when the wilderness is provisioned and the monster has an actual cell, append one row with label `"結算進度"` and the unit's cursor as value, and, when the cursor is below `current_population_tick()`, one row with label `"結算落後"` and `world tick - cursor` as value. Build both rows with the same keys as the existing `"下一次決策"` row. The function performs reads only; it must not call any `ensure_*` function.

### D4. Tests

New `world/maps/tests/test_population_writer_guards.py` on `ActivityFixture` with `build_two_zone_world` (from `world.maps.tests.test_scoped_population_settlement`). A unit is made to lag by setting `get_world_clock().tick = 700` while the cursor record stays at 100; a single unit is made current by writing `{"default": 100, "units": {<unit>: 700}}`.

- One test per writer for the lagging case, asserting the error and that `settlement_projection` plus the raw timeline are unchanged.
- "Group reaching a lagging unit": `create_group` with a home cell in the current unit and an activity key bound to an area of the lagging unit.
- "Current unit and running pass": each writer succeeds for the current unit; each writer succeeds for the lagging unit inside `with population_units.running_pass():`.
- GM view: extend the existing `placement_section` label test in `world/maps/tests/test_monster_activity.py` with both scenarios of the second requirement.

Then run the suites of every caller listed in Context (tasks 3.1) to prove no existing flow is refused.

### D5. Documentation

Extend the section "Catch-up and observed units" of `docs/development/regional-monster-population.md` with: the guard, the five writers, the error name, and the GM rows.

## Risks / Trade-offs

- [After `observed-unit-advance`, an operator action on a remote monster through a path that has no catch-up is refused] → the error names the unit and both ticks; the fix is a catch-up call at that entry point. The known operator paths are covered.
- [A combat writer is refused because the battle cell's unit is behind] → cannot happen while a player stands in the cell (the unit is observed); the caller suites of task 3.1 run those flows.
