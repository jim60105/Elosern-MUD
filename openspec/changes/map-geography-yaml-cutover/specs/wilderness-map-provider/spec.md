# Spec Delta

## MODIFIED Requirements

### Requirement: get_location_name and at_prepare_room delegate to the deterministic terrain model
`ElosernWildernessMapProvider.get_location_name(coordinates)` SHALL return the published region
view's `display_name_zh` for `region_for_coordinates(*coordinates)`.
`at_prepare_room(coordinates, caller, room)` SHALL unconditionally set these room fields on every
call, and SHALL clear `room.room_art_key` on every activation:

```
room.ndb.active_desc = terrain_description(*coordinates)
room.scene_archetype = the published region view's scene_archetype for the coordinate
room.scene_identity  = wilderness name and current coordinates
```

The region scene association is the continent source's map-owned `scene_archetype` field,
validated against the game scene catalog at publication; no Python region table is read. It SHALL
also initialize the coordinate's deterministic monster population per the scenarios below.

#### Scenario: get_location_name matches the region registry
- **WHEN** `get_location_name((x, y))` is called
- **THEN** it returns the published region view's `display_name_zh` for
  `region_for_coordinates(x, y)`

#### Scenario: at_prepare_room sets both the description and the scene_archetype seam
- **WHEN** `at_prepare_room((x, y), caller, room)` is called on a `TerrainRoom`
- **THEN** `room.ndb.active_desc == terrain_description(x, y)` and `room.scene_archetype` equals the
  published region view's `scene_archetype` for `region_for_coordinates(x, y)`

#### Scenario: scene_archetype is re-set, not left stale, when a pooled room is reused at a new coordinate
- **WHEN** a `TerrainRoom` object previously activated at coordinates `(x1, y1)` (with
  `region_for_coordinates(x1, y1) != region_for_coordinates(x2, y2)`) is later reused by the
  wilderness system and activated at different coordinates `(x2, y2)`
- **THEN** after the second activation, `room.scene_archetype` equals the published region view's
  scene archetype for `(x2, y2)`, not the value computed for `(x1, y1)`

#### Scenario: at_prepare_room opens exactly the gate exit at an approach cell
- **WHEN** `at_prepare_room((860, 1077), caller, room)` is called on a `TerrainRoom` carrying the
  eight directional exits
- **THEN** the `"north"` exit's locks allow `traverse` and `view`, and no other exit's locks are
  modified by the hook

#### Scenario: at_prepare_room touches no locks away from approach cells
- **WHEN** `at_prepare_room` is called for an ordinary wilderness cell or for the opposite gate's
  approach cell `(864, 1080)`
- **THEN** at the ordinary cell no exit's locks are modified, and at `(864, 1080)` only the
  `"west"` exit's locks are opened; an approach cell never opens another gate's exit

#### Scenario: A point-shape anchor opens only its authored gate direction
- **WHEN** the registry is patched with a point-shape entry anchored at `(500, 500)` and
  `at_prepare_room((500, 500), caller, room)` is called on a `TerrainRoom` carrying the eight
  directional exits, all initially closed
- **THEN** only the single gate's authored `return_direction` exit allows `traverse` and `view`,
  matching the resolver's authored-direction gateway advertisement at that cell

#### Scenario: A gate lock does not leak when the pooled room moves to a non-approach coordinate
- **WHEN** a pooled `TerrainRoom` was activated at `(860, 1077)` (opening its `"north"` exit) and is
  later activated at a coordinate that is not any approach cell
- **THEN** the stock activation pass recomputes every self-loop exit's locks from provider
  validity before `at_prepare_room` runs, and after activation no exit carries a hook-opened
  lock

#### Scenario: at_prepare_room initializes population when a wilderness script is attached
- **WHEN** `at_prepare_room(coordinates, caller, room)` is called on a `TerrainRoom` whose
  `room.wilderness` is the live wilderness script
- **THEN** `ensure_population(room.wilderness, coordinates)` is invoked for those coordinates

#### Scenario: at_prepare_room is a population no-op without a wilderness script
- **WHEN** `at_prepare_room(coordinates, caller, room)` is called on a `TerrainRoom` with no
  attached wilderness script (as in the provider's unit tests)
- **THEN** the description, scene archetype, scene identity, cleared room-art key, and (at approach
  cells) gate locks are set, no exception is raised, and no monster is created

#### Scenario: Population assurance calls the capability resolver
- **WHEN** `at_prepare_room` initializes the coordinate's deterministic monster population
  under the `wilderness-monster-population` capability
- **THEN** it does so by calling
  `world.maps.wilderness_population.ensure_population(room.wilderness, coordinates)` when
  `room.wilderness` resolves to the wilderness script, and SHALL be a population no-op (setting
  the scene metadata and any applicable gate locks) when no wilderness script is attached, so a
  pooled or unit-test `TerrainRoom` is never required to have one

#### Scenario: Gate exit locks use the stock lock-string form
- **WHEN** `coordinates` equal some registered gate's `approach_cell`
- **THEN** `at_prepare_room` SHALL set that gate's `return_direction` long-form exit (the contrib's
  lock-string form) and no other lock state

#### Scenario: Non-approach coordinates leave locks alone
- **WHEN** `at_prepare_room` runs at a coordinate that is no registered gate's approach cell
- **THEN** no exit lock is modified by the provider hook

#### Scenario: Point anchors open the authored direction to match the resolver
- **WHEN** a point-shape entry is registered and its anchor cell is prepared
- **THEN** exactly the authored gate direction is opened, matching the resolver's gateway
  advertisement at that cell
