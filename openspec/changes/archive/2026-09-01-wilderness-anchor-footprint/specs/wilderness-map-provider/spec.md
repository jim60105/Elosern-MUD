## MODIFIED Requirements

### Requirement: ElosernWildernessMapProvider bounds the map to a 224x224 grid at 10 km per cell
`world/maps/wilderness_provider.py` SHALL define `WILDERNESS_KM_PER_CELL = 10`,
`WILDERNESS_MAX_X = 223`, `WILDERNESS_MAX_Y = 223`, and `ElosernWildernessMapProvider`, a subclass
of `evennia.contrib.grid.wilderness.wilderness.WildernessMapProvider`, whose
`is_valid_coordinates` accepts exactly the coordinates `0 <= x <= WILDERNESS_MAX_X` and
`0 <= y <= WILDERNESS_MAX_Y` that are NOT an anchor footprint cell of any
`WILDERNESS_ENTRY_REGISTRY` entry (`WildernessEntryPoint.footprint_cells`; point-shape entries
contribute no footprint cells). The footprint exclusion SHALL be derived from the live registry
at call time (a cache keyed on registry identity is conforming; a hardcoded cell list is not),
so patching the registry in tests changes validity without patching the provider. The provider
SHALL NOT special-case any anchor key.

#### Scenario: Coordinates inside the bound and outside every footprint are valid
- **WHEN** `ElosernWildernessMapProvider().is_valid_coordinates(wilderness, (0, 0))` and
  `(WILDERNESS_MAX_X, WILDERNESS_MAX_Y)` are checked
- **THEN** both return `True`

#### Scenario: Coordinates outside the bound are invalid
- **WHEN** `ElosernWildernessMapProvider().is_valid_coordinates(wilderness, (-1, 0))` and
  `(WILDERNESS_MAX_X + 1, 0)` are checked
- **THEN** both return `False`

#### Scenario: Anchor footprint cells are invalid
- **WHEN** `is_valid_coordinates` is checked for the `capital_altoria` anchor cell `(60, 100)`,
  a corner footprint cell `(58, 98)`, and the two gate approach cells `(60, 97)` and `(60, 103)`
- **THEN** the two footprint cells return `False` and the two approach cells return `True`

#### Scenario: Registry patches change footprint validity without patching the provider
- **WHEN** a test patches `WILDERNESS_ENTRY_REGISTRY` with an extra point-shape entry and with an
  extra multi-cell entry, leaving the provider untouched
- **THEN** the point-shape anchor cell stays valid, its gate cell behaves as a gateway (valid),
  and the multi-cell entry's mask cells become invalid while its neighbors stay valid; restoring
  the registry restores validity

#### Scenario: The bound approximates world_info.md's stated continent area
- **WHEN** `(WILDERNESS_MAX_X + 1) * WILDERNESS_KM_PER_CELL` is computed for both axes and squared
- **THEN** the result is within 1% of `world_info.md`'s stated ~5,000,000 km² continent area

### Requirement: get_location_name and at_prepare_room delegate to the deterministic terrain model
`ElosernWildernessMapProvider.get_location_name(coordinates)` SHALL return
`WILDERNESS_REGION_REGISTRY[region_for_coordinates(*coordinates)].display_name_zh`.
`ElosernWildernessMapProvider.at_prepare_room(coordinates, caller, room)` SHALL set
`room.ndb.active_desc` from `terrain_description(*coordinates)` and `room.scene_archetype` from
`region_for_coordinates(*coordinates)`, unconditionally, on every call. It SHALL additionally
ensure the coordinate's deterministic monster population by calling
`world.maps.wilderness_population.ensure_population(room.wilderness, coordinates)` — the
`wilderness-monster-population` capability — when `room.wilderness` resolves to the wilderness
script, and SHALL be a population no-op (setting only the description and scene archetype) when
no wilderness script is attached, so a pooled or unit-test `TerrainRoom` is never required to have
one. Finally, when `coordinates` equal some registered gate's `approach_cell`, it SHALL set that
gate's `return_direction` long-form exit (the contrib's normalized exit key) on the room to
`traverse:true();view:true()` locks — the same lock-string form the stock
`set_active_coordinates` pass uses for valid neighbors — so the gate exit is visible and offered
from the approach cell even though the footprint cell beyond it is provider-invalid; the gateway
step itself is performed by `WildernessReturnExit`'s registry branch, not by ordinary coordinate
movement. At a coordinate that is not an approach cell it SHALL NOT touch any exit's locks.
At a coordinate equal to a point-shape entry's `anchor_cell`, it SHALL instead set ALL EIGHT
directional exits' locks to `traverse:true();view:true()` — the resolver advertises the entry's
single gate in every direction at a point anchor, and the hook keeps offered exits identical to
resolver truth regardless of which neighbors the stock validity pass happened to unlock.

#### Scenario: get_location_name matches the region registry
- **WHEN** `get_location_name((x, y))` is called
- **THEN** it returns the same string as `WILDERNESS_REGION_REGISTRY[region_for_coordinates(x, y)].
  display_name_zh`

#### Scenario: at_prepare_room sets both the description and the scene_archetype seam
- **WHEN** `at_prepare_room((x, y), caller, room)` is called on a `TerrainRoom`
- **THEN** `room.ndb.active_desc == terrain_description(x, y)` and `room.scene_archetype ==
  region_for_coordinates(x, y)`

#### Scenario: scene_archetype is re-set, not left stale, when a pooled room is reused at a new coordinate
- **WHEN** a `TerrainRoom` object previously activated at coordinates `(x1, y1)` (with
  `region_for_coordinates(x1, y1) != region_for_coordinates(x2, y2)`) is later reused by the
  wilderness system and activated at different coordinates `(x2, y2)`
- **THEN** after the second activation, `room.scene_archetype == region_for_coordinates(x2, y2)`,
  not the value computed for `(x1, y1)`

#### Scenario: at_prepare_room opens exactly the gate exit at an approach cell
- **WHEN** `at_prepare_room((60, 97), caller, room)` is called on a `TerrainRoom` carrying the
  eight directional exits
- **THEN** the `"north"` exit's locks allow `traverse` and `view`, and no other exit's locks are
  modified by the hook

#### Scenario: at_prepare_room touches no locks away from approach cells
- **WHEN** `at_prepare_room` is called for an ordinary wilderness cell or for the opposite gate's
  approach cell `(60, 103)`
- **THEN** at the ordinary cell no exit's locks are modified, and at `(60, 103)` only the
  `"south"` exit's locks are opened — an approach cell never opens another gate's exit

#### Scenario: A point-shape anchor opens all eight exits
- **WHEN** the registry is patched with a point-shape entry anchored at `(120, 120)` and
  `at_prepare_room((120, 120), caller, room)` is called on a `TerrainRoom` carrying the eight
  directional exits
- **THEN** all eight exits' locks allow `traverse` and `view`, matching the resolver's
  every-direction gateway advertisement at that cell

#### Scenario: A gate lock does not leak when the pooled room moves to a non-approach coordinate
- **WHEN** a pooled `TerrainRoom` was activated at `(60, 97)` (opening its `"north"` exit) and is
  later activated at a coordinate that is not any approach cell
- **THEN** the stock activation pass recomputes every self-loop exit's locks from provider
  validity before `at_prepare_room` runs, and after activation no exit carries a hook-opened
  lock

#### Scenario: at_prepare_room ensures population when a wilderness script is attached
- **WHEN** `at_prepare_room(coordinates, caller, room)` is called on a `TerrainRoom` whose
  `room.wilderness` is the live wilderness script
- **THEN** `ensure_population(room.wilderness, coordinates)` is invoked for those coordinates

#### Scenario: at_prepare_room is a population no-op without a wilderness script
- **WHEN** `at_prepare_room(coordinates, caller, room)` is called on a `TerrainRoom` with no
  attached wilderness script (as in the provider's unit tests)
- **THEN** only the description, scene archetype, and (at approach cells) gate locks are set, no
  exception is raised, and no monster is created
