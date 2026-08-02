## MODIFIED Requirements

### Requirement: get_location_name and at_prepare_room delegate to the deterministic terrain model
`ElosernWildernessMapProvider.get_location_name(coordinates)` SHALL return
`WILDERNESS_REGION_REGISTRY[region_for_coordinates(*coordinates)].display_name_zh`.
`ElosernWildernessMapProvider.at_prepare_room(coordinates, caller, room)` SHALL set
`room.ndb.active_desc` from `terrain_description(*coordinates)` and `room.scene_archetype` from
`region_for_coordinates(*coordinates)`, unconditionally, on every call. It SHALL additionally ensure
the coordinate's deterministic monster population by calling
`world.maps.wilderness_population.ensure_population(room.wilderness, coordinates)` — the
`wilderness-monster-population` capability — when `room.wilderness` resolves to the wilderness script,
and SHALL be a population no-op (setting only the description and scene archetype) when no wilderness
script is attached, so a pooled or unit-test `TerrainRoom` is never required to have one.

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

#### Scenario: at_prepare_room ensures population when a wilderness script is attached
- **WHEN** `at_prepare_room(coordinates, caller, room)` is called on a `TerrainRoom` whose
  `room.wilderness` is the live wilderness script
- **THEN** `ensure_population(room.wilderness, coordinates)` is invoked for those coordinates

#### Scenario: at_prepare_room is a population no-op without a wilderness script
- **WHEN** `at_prepare_room(coordinates, caller, room)` is called on a `TerrainRoom` with no attached
  wilderness script (as in the provider's unit tests)
- **THEN** only the description and scene archetype are set, no exception is raised, and no monster is
  created
