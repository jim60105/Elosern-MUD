# Design

## Context

See proposal.md - Why. Facts verified at commit `f9925e49`:

- `world/lore/monster_placement.py::EcologyZone` has `key`, `region_key`, `rectangles` (inclusive `(x_min, x_max, y_min, y_max)`). `ECOLOGY_ZONE_REGISTRY` holds 175 zones.
- `world/lore/monster_activity.py::ActivityArea` has `key` and either `region_key` + `rectangles` (260 areas) or `home_radius` (3 areas, all radius 0). `MonsterActivity.area_key` names the area.
- Measured on the shipped registries with the rule of D1: 175 units, each of one zone. The design does not rely on that; tests use synthetic registries only.
- `world/maps/monster_activity.py::MonsterGroup` has `home_owner: tuple[str, str]` (kind in `OWNER_KINDS = ("zone", "site", "quest", "explicit")`, then key), `home: LocationRef`, `position: LocationRef | None`, `journey_id`. `MonsterJourney` has `source` and `destination`. `_group_area(group)` returns the resolved locators of the group's area.
- `world/rules/movement_edges.py::LocationRef` has `kind` (`"wilderness"` with `map`, `x`, `y`, or a room with `id`).
- `world/lore/monster_placement.py::MONSTER_SITE_REGISTRY` rows have `key` and `coordinates`.
- `world/maps/regional_population.py::_published_geography().terrain` plus `elosern_map_core.terrain.region_for_coordinates(terrain, x, y)` give a cell's region key.
- `regional_population.initialize_population_seed` is the one fresh-provisioning writer. `snapshot_population_surfaces` lists the wilderness attributes a rollback restores.
- Why units are independent: a group decides from its own record, its members' physiology, its area and cell protection at its destination; ordinary movement never leaves the area; a zone's recovery reads only individuals standing in the zone and individuals whose home is the zone; a site reads only its members and its cell. The only way an individual enters another unit's cell is an escape across the area boundary, which D3 turns into a link.

## Goals / Non-Goals

**Goals:**

- A pure, cheap, deterministic unit index and closure.
- A durable per-unit cursor that is written but not yet read for decisions.

**Non-Goals:**

- No change to which groups, zones or sites a pass settles.
- No terrain-exact intersection: rectangle overlap inside one region is a deliberate superset.
- No change to `population_forecast.py`, the clock, or any owner decision.

## Decisions

### D1. Static unit index

Create `world/maps/population_units.py`:

```python
RESIDUAL_UNIT = "~residual"
POPULATION_UNIT_CURSORS_ATTRIBUTE = "population_unit_cursors"


@dataclass(frozen=True, slots=True)
class UnitIndex:
    unit_of_zone: Mapping[str, str]
    unit_of_area: Mapping[str, str]
    # region_key -> ((x_min, x_max, y_min, y_max), unit_id) for every zone and area rectangle
    rectangles: Mapping[str, tuple[tuple[tuple[int, int, int, int], str], ...]]

    def unit_of_cell(self, region_key: str | None, cell: tuple[int, int]) -> str: ...


def build_unit_index(
    zones: Mapping[str, EcologyZone], areas: Mapping[str, ActivityArea]
) -> UnitIndex: ...
```

Algorithm: nodes are `("zone", key)` for every zone and `("area", key)` for every area with `region_key is not None`. Two nodes are joined (union-find) when they have the same `region_key` and any rectangle of one overlaps any rectangle of the other (`a.x_min <= b.x_max and b.x_min <= a.x_max and a.y_min <= b.y_max and b.y_min <= a.y_max`). The unit identifier of a component is `"zone:" + smallest zone key` in it, or `"area:" + smallest area key` when it has no zone. `unit_of_cell` returns the unit of the first rectangle of that `region_key` that contains the cell, scanning rectangles sorted by `(unit_id, rectangle)`; no match, or `region_key is None`, returns `RESIDUAL_UNIT`. Rectangles of one region that contain the same cell are always in one unit by construction, so the scan order cannot change the answer.

Home-radius areas have no node; a group bound to one is placed by D3 through its home and area cells.

`current_unit_index() -> UnitIndex` memoises `build_unit_index(ECOLOGY_ZONE_REGISTRY, ACTIVITY_AREA_REGISTRY)` on the identity of both registry objects (use `world.maps.monster_activity.SourceMemo` the way `_RESOLVED_AREAS` does), so tests that swap registries get a fresh index.

### D2. Locating a locator

```python
def unit_of_location(index: UnitIndex, location: LocationRef | None) -> str | None
```

`None` for `None`. `RESIDUAL_UNIT` for a room locator. For a wilderness locator: `index.unit_of_cell(region_for_coordinates(terrain, x, y), (x, y))` with the terrain from `regional_population._published_geography().terrain` (expose it through a public function `regional_population.cell_region(cell) -> str | None` that returns `None` outside the frame).

### D3. Group units and closure

```python
def group_units(index: UnitIndex, group: MonsterGroup, journey: MonsterJourney | None) -> frozenset[str]
def site_unit(index: UnitIndex, site_key: str) -> str
def unit_closure(index: UnitIndex, state: MonsterActivityState, seeds: Iterable[str]) -> frozenset[str]
```

`group_units` is the set of: `unit_of_location(home)`, `unit_of_location(position)`, the journey's `source` and `destination` units, the unit of every locator returned by `monster_activity._group_area(group)` (decode each with `world.rules.movement_edges.decode_location_ref`; find the exact name with `grep -n "def decode_location_ref\|def encode_location_ref" world/rules/movement_edges.py`), `index.unit_of_zone[key]` when `home_owner[0] == "zone"` and the key is in the index, and `site_unit(index, key)` when `home_owner[0] == "site"`. `None` entries are dropped. Expose `_group_area` as public `monster_activity.group_area(group)`.

`site_unit` is `unit_of_location` of the site's wilderness cell from `MONSTER_SITE_REGISTRY[site_key].coordinates`; an unknown key gives `RESIDUAL_UNIT`.

`unit_closure`: start from `seeds`; repeat until stable: for every group in `state.groups` whose `group_units` intersects the set, add all its units. The result is a `frozenset`. Groups are visited in sorted `group_id` order; the result does not depend on the order.

### D4. Cursor record

Stored value: `{"default": int, "units": {unit_id: int}}`.

```python
def read_unit_cursors(wilderness) -> UnitCursors          # frozen: default: int, units: Mapping[str, int]
def unit_cursor(cursors: UnitCursors, unit_id: str) -> int # units.get(unit_id, default)
def write_unit_cursors(wilderness, cursors: UnitCursors) -> None   # through world.rules.surfaces.store_attribute
def advance_unit_cursors(wilderness, unit_ids: Iterable[str] | None, tick: int) -> None
```

`read_unit_cursors` raises `regional_population.MalformedPopulationState` for a missing or malformed record. `advance_unit_cursors(..., None, tick)` sets `default = max(default, tick)` and raises every listed unit below `tick` to `tick`; with unit ids it raises only those units and leaves `default` alone. A cursor never decreases.

`regional_population.initialize_population_seed`: after the timeline is created, when the attribute is absent, write `{"default": int(tick), "units": {}}`.

`regional_population.snapshot_population_surfaces`: add `(POPULATION_UNIT_CURSORS_ATTRIBUTE, None)` to the wilderness attributes, so the advance registry and every owner restore cover it.

`population_lifecycle.settle_population_lifecycle`: at the end of the pass body, after `retire_settled_decision_receipts`, call `population_units.advance_unit_cursors(wilderness, None, end_tick)`.

### D5. Startup provisioning for an existing world

Add `population_units.ensure_unit_cursors(wilderness) -> bool`: when the wilderness is provisioned (`regional_population.population_provisioned`) and the attribute is absent, write `{"default": read_monster_activity(wilderness).settled_through_tick, "units": {}}` and return `True`; otherwise return `False`. Call it from the server-start step that registers the lifecycle stage: find it with `grep -rn "register_regional_population()" server/ world/maps/bootstrap.py`, and call `ensure_unit_cursors(regional_population.live_wilderness())` right after that registration when the wilderness is not `None`. Emit `log_info("population_unit_cursors_initialized", context={"tick": ...})` only when it returned `True`.

### D6. Tests

New `world/maps/tests/test_population_units.py`:

- `unittest.TestCase` class for D1 with hand-built `EcologyZone` and `ActivityArea` rows (use `dataclasses.replace` on one synthetic row from `world.tests.synthetic_data` or construct them directly with placeholder pools as `world/maps/tests/test_population_zone_pass.py` does). Scenarios of the first requirement except "Residual" for cells, which needs D2.
- `ActivityFixture`-based class for D2, D3 and D4 and the scenario "Residual". For "Escaped member links two units", write the group's `position` directly into the stored activity record with `dataclasses.replace`, as `world/maps/tests/test_monster_activity.py` does in `test_forced_sleep_receipt_rolls_back_with_a_late_source_fault`. For "Rollback", register a failing synthetic event source after the lifecycle stage the way existing rollback tests in that file do.
- Expected unit identifiers are written literally from the synthetic keys.

### D7. Documentation

Add a section "Settlement units" to `docs/development/regional-monster-population.md`: the rule of D1, the residual unit, group units, closure, the cursor record, and the independence argument from Context.

## Risks / Trade-offs

- [Rectangle overlap merges zones whose real cells do not intersect] → only costs granularity, never correctness.
- [A future rule lets one unit's settlement read another unit's state (for example a zone that counts monsters of a neighbouring zone)] → the independence argument in D7 names what a new rule must respect; `unit-scoped-population-settlement` adds the test that detects a violation.
- [A registry edit changes unit identifiers of a saved world] → unknown identifiers fall back to `default`; `observed-unit-advance` states the consequence for lagging units.
