## Purpose

The bounded `ElosernWildernessMapProvider` instantiating the deterministic terrain model on the
wilderness/Virtual layer: a 224×224 grid at 10 km/cell approximating the continent's stated ~500萬 km²
area, using the project-owned `TerrainRoom` and `WildernessReturnExit` typeclasses.

## Requirements


### Requirement: ElosernWildernessMapProvider bounds the map to a 224x224 grid at 10 km per cell
`world/maps/wilderness_provider.py` SHALL define `WILDERNESS_KM_PER_CELL = 10`,
`WILDERNESS_MAX_X = 223`, `WILDERNESS_MAX_Y = 223`, and `ElosernWildernessMapProvider`, a subclass of
`evennia.contrib.grid.wilderness.wilderness.WildernessMapProvider`, whose `is_valid_coordinates`
accepts exactly the coordinates `0 <= x <= WILDERNESS_MAX_X` and `0 <= y <= WILDERNESS_MAX_Y`.

#### Scenario: Coordinates inside the bound are valid
- **WHEN** `ElosernWildernessMapProvider().is_valid_coordinates(wilderness, (0, 0))` and
  `(WILDERNESS_MAX_X, WILDERNESS_MAX_Y)` are checked
- **THEN** both return `True`

#### Scenario: Coordinates outside the bound are invalid
- **WHEN** `ElosernWildernessMapProvider().is_valid_coordinates(wilderness, (-1, 0))` and
  `(WILDERNESS_MAX_X + 1, 0)` are checked
- **THEN** both return `False`

#### Scenario: The bound approximates world_info.md's stated continent area
- **WHEN** `(WILDERNESS_MAX_X + 1) * WILDERNESS_KM_PER_CELL` is computed for both axes and squared
- **THEN** the result is within 1% of `world_info.md`'s stated ~5,000,000 km² continent area

### Requirement: get_location_name and at_prepare_room delegate to the deterministic terrain model
`ElosernWildernessMapProvider.get_location_name(coordinates)` SHALL return
`WILDERNESS_REGION_REGISTRY[region_for_coordinates(*coordinates)].display_name_zh`.
`ElosernWildernessMapProvider.at_prepare_room(coordinates, caller, room)` SHALL set
`room.ndb.active_desc` from `terrain_description(*coordinates)` and `room.scene_archetype` from
`region_for_coordinates(*coordinates)`, unconditionally, on every call.

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
- **THEN** after the second activation, `room.scene_archetype == region_for_coordinates(x2, y2)`, not
  the value computed for `(x1, y1)`

### Requirement: ElosernWildernessMapProvider uses TerrainRoom and WildernessReturnExit
`ElosernWildernessMapProvider.room_typeclass` SHALL be `typeclasses.rooms.TerrainRoom` and
`ElosernWildernessMapProvider.exit_typeclass` SHALL be `typeclasses.exits.WildernessReturnExit`.

#### Scenario: Rooms created by the provider are TerrainRoom instances
- **WHEN** a character enters the wilderness through `ElosernWildernessMapProvider`
- **THEN** `character.location` is an instance of `typeclasses.rooms.TerrainRoom`

#### Scenario: Every directional exit created by the provider is a WildernessReturnExit instance
- **WHEN** any room created by `ElosernWildernessMapProvider` is inspected
- **THEN** every one of its eight directional exits is an instance of
  `typeclasses.exits.WildernessReturnExit`
