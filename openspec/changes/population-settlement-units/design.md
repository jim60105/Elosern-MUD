# Design

## Context

See proposal.md - Why. Facts verified at commit `f9925e49`:

- `world/lore/monster_placement.py::EcologyZone` has `key`, `region_key`, `rectangles` (inclusive `(x_min, x_max, y_min, y_max)`). `ECOLOGY_ZONE_REGISTRY` holds 175 zones.
- `world/lore/monster_activity.py::ActivityArea` has `key` and either `region_key` + `rectangles` (260 areas) or `home_radius` (3 areas, all radius 0). `MonsterActivity.area_key` names the area.
- Measured on the shipped registries with the rectangle-overlap rule alone: 175 units, each of one zone (the 260 region-bound areas all overlap a zone). The birth-binding links of D1 can merge some of them, but on the shipped data they merge none: 42 further units hold site activity areas that no zone covers, so the world resolves to 217 units. The design does not rely on that; tests use synthetic registries only.
- `world/maps/monster_activity.py::MonsterGroup` has `home_owner: tuple[str, str]` (kind in `OWNER_KINDS = ("zone", "site", "quest", "explicit")`, then key), `home: LocationRef`, `position: LocationRef | None`, `journey_id`. `MonsterJourney` has `source` and `destination`. `group_area(group)` returns the resolved locators of the group's area.
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
    zones: Mapping[str, EcologyZone],
    areas: Mapping[str, ActivityArea],
    bound_areas: Mapping[str, frozenset[str]],   # zone key -> area keys its births can be bound to
) -> UnitIndex: ...


def zone_bound_areas() -> dict[str, frozenset[str]]: ...
```

Algorithm: nodes are `("zone", key)` for every zone and `("area", key)` for every area with `region_key is not None`. Two nodes are joined (union-find) when they have the same `region_key` and any rectangle of one overlaps any rectangle of the other (`a.x_min <= b.x_max and b.x_min <= a.x_max and a.y_min <= b.y_max and b.y_min <= a.y_max`). A zone node is also joined with the node of every region-bound area in `bound_areas[zone key]`. `zone_bound_areas()` builds that mapping from the live registries: for every zone and every `WeightedComposition` of `zone.pool`, take `composition_row_bindings(ENCOUNTER_COMPOSITION_REGISTRY[row.composition_key])` (both in `world/lore/monster_placement.py`), map each activity key through `MONSTER_ACTIVITY_REGISTRY[key].area_key`, and keep the areas with `region_key is not None`. For every site of `MONSTER_SITE_REGISTRY`, do the same with `composition_row_bindings(composition, site=site)` for the site's composition (find the site's composition attribute with `grep -n "class MonsterSite" -A25 world/lore/monster_placement.py`) and add those areas to the entry of the zone whose rectangles contain `site.coordinates` in the site's region; a site inside no zone contributes a join between its areas only (join them with each other). This link is what keeps a group born by a pass inside the pass's own units: its home is in the zone and its area is in the same unit.

The unit identifier of a component is `"zone:" + smallest zone key` in it, or `"area:" + smallest area key` when it has no zone. `unit_of_cell` returns the unit of the first rectangle of that `region_key` that contains the cell, scanning rectangles sorted by `(unit_id, rectangle)`; no match, or `region_key is None`, returns `RESIDUAL_UNIT`. Rectangles of one region that contain the same cell are always in one unit by construction, so the scan order cannot change the answer.

Home-radius areas have no node; a group bound to one is placed by D3 through its home and area cells.

`current_unit_index() -> UnitIndex` memoises `build_unit_index(ECOLOGY_ZONE_REGISTRY, ACTIVITY_AREA_REGISTRY, zone_bound_areas())` on the identity of the zone, area, activity, composition and site registry objects (use `world.maps.monster_activity.SourceMemo` the way `_RESOLVED_AREAS` does), so tests that swap registries get a fresh index.

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

`group_units` is the set of: `unit_of_location(home)`, `unit_of_location(position)`, the journey's `source` and `destination` units, the unit of every locator returned by `monster_activity.group_area(group)` (decode each with `world.rules.movement_edges.decode_location_ref`; find the exact name with `grep -n "def decode_location_ref\|def encode_location_ref" world/rules/movement_edges.py`), `index.unit_of_zone[key]` when `home_owner[0] == "zone"` and the key is in the index, and `site_unit(index, key)` when `home_owner[0] == "site"`. `None` entries are dropped. `monster_activity.group_area` is public: the former `_group_area` now serves the decision path and this index from one reader.

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

### D5. No migration; hand-provisioned fixtures write the record

There is no startup repair and no compatibility read: `read_unit_cursors` raises `MalformedPopulationState` when the attribute is absent. A development world created before this change is re-provisioned (`docs/development/database-reset.md`).

Test fixtures that provision a population without `initialize_population_seed` must write the record themselves. Find them with `grep -rln "population_timeline = " --include='*.py' world commands server web tools`. In each fixture found, next to the statement that writes `population_timeline`, write `population_unit_cursors = {"default": <the same tick>, "units": {}}`. `world/maps/tests/test_monster_activity.py::ActivityFixture._reset_activity` is one of them. The two smoke tools `tools/monster_population_smoke.py` and `tools/monster_field_behaviour_smoke.py` provision through `initialize_population_seed` and need no edit; confirm with the same grep.

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
- [An existing development world has no cursor record and every advance on it refuses] → intended fail-closed behaviour of a pre-release project; the proposal states the re-provisioning step.
- [A registry edit changes unit identifiers of a saved world] → unknown identifiers fall back to `default`; `observed-unit-advance` states the consequence for lagging units.
