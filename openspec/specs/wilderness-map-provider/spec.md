## Purpose

The bounded `ElosernWildernessMapProvider` instantiating the deterministic terrain model on the
wilderness/Virtual layer, using the 2700 × 2700 one-kilometer frame around the
mainland polygon and the project-owned `TerrainRoom` and `WildernessReturnExit` typeclasses.

## Requirements

### Requirement: ElosernWildernessMapProvider bounds the map to the declared one-kilometer frame
`world/maps/wilderness_provider.py` SHALL define `WILDERNESS_KM_PER_CELL = 1`,
`WILDERNESS_MAX_X = 2699`, `WILDERNESS_MAX_Y = 2699`, and `ElosernWildernessMapProvider`,
subclassing `WildernessMapProvider`, whose `is_valid_coordinates` accepts exactly `0 <= x <=
WILDERNESS_MAX_X` and `0 <= y <= WILDERNESS_MAX_Y` that are land-side, passable, and outside every
`WILDERNESS_ENTRY_REGISTRY` footprint; the single shared rule is `is_valid_wilderness_cell` (frame,
mainland, ridge, water, footprints).

#### Scenario: Coordinates inside the bound and outside every footprint are valid
- **WHEN** `ElosernWildernessMapProvider().is_valid_coordinates(wilderness, (500, 700))` and the
  two frame corners `(0, 0)` / `(WILDERNESS_MAX_X, WILDERNESS_MAX_Y)` are checked
- **THEN** only the land-side non-footprint cell returns `True`; the ocean-margin corners return
  `False` even though they are inside the frame

#### Scenario: Coordinates outside the bound are invalid
- **WHEN** `ElosernWildernessMapProvider().is_valid_coordinates(wilderness, (-1, 0))` and
  `(WILDERNESS_MAX_X + 1, 0)` are checked
- **THEN** both return `False`

#### Scenario: Anchor footprint cells are invalid
- **WHEN** `is_valid_coordinates` is checked for a registered settlement's derived anchor cell, a
  cell of its derived footprint mask, and each of its gates' derived approach cells
- **THEN** the footprint cells return `False` and the approach cells return `True`

#### Scenario: Registry patches change footprint validity without patching the provider
- **WHEN** a test patches `WILDERNESS_ENTRY_REGISTRY` with an extra point-shape entry and with an
  extra multi-cell entry, leaving the provider untouched
- **THEN** the point-shape anchor cell stays valid, its gate cell behaves as a gateway (valid),
  and the multi-cell entry's mask cells become invalid while its neighbors stay valid; restoring
  the registry restores validity

#### Scenario: The bound approximates world_info.md's stated continent area
- **WHEN** the coastline polygon and enclosing frame areas are computed
- **THEN** the mainland polygon's shoelace area is exactly 5,000,000 km² and the 2700-cell frame is
  7,290,000 km² including ocean; raster counts need not equal vector area

#### Scenario: Point-shape entries contribute no footprint
- **WHEN** a `WILDERNESS_ENTRY_REGISTRY` entry has point shape
- **THEN** it contributes no footprint cells to the exclusion

#### Scenario: The footprint exclusion is derived live from the registry
- **WHEN** the footprint exclusion is implemented and exercised
- **THEN** it SHALL be derived from the live registry at call time (a cache keyed on registry
  identity is conforming; a hardcoded cell list is not), so patching the registry in tests changes
  validity without patching the provider

#### Scenario: No anchor key is special-cased
- **WHEN** the provider validates coordinates
- **THEN** it SHALL NOT special-case any anchor key

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

The scene archetype SHALL come from the continent source, validated at publication, never a Python
region table; the hook SHALL also initialize monster population.

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
- **WHEN** `at_prepare_room` is called at a registry gate's derived `approach_cell` on a `TerrainRoom` carrying the
  eight directional exits
- **THEN** the `"north"` exit's locks allow `traverse` and `view`, and no other exit's locks are
  modified by the hook

#### Scenario: at_prepare_room touches no locks away from approach cells
- **WHEN** `at_prepare_room` is called for an ordinary wilderness cell or for another gate's
  approach cell
- **THEN** at the ordinary cell no exit's locks are modified, and at another gate's approach cell only the
  `"west"` exit's locks are opened; an approach cell never opens another gate's exit

#### Scenario: A point-shape anchor opens only its authored gate direction
- **WHEN** the registry is patched with a point-shape entry anchored at `(500, 500)` and
  `at_prepare_room((500, 500), caller, room)` is called on a `TerrainRoom` carrying the eight
  directional exits, all initially closed
- **THEN** only the single gate's authored `return_direction` exit allows `traverse` and `view`,
  matching the resolver's authored-direction gateway advertisement at that cell

#### Scenario: A gate lock does not leak when the pooled room moves to a non-approach coordinate
- **WHEN** a pooled `TerrainRoom` was activated at a gate's approach cell (opening that gate's exit) and is
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

### Requirement: The continent remains virtual with bounded local lookup
The wilderness SHALL comprise 2700 by 2700 one-kilometer logical cells with east/north axes and authoritative coastline/terrain validity. Sea, closed ridges, cliffs and water SHALL be impassable on foot. Ordinary movement SHALL use bounded local masks and sparse indices without whole-frame scans or room materialization.

#### Scenario: Frame and sea margin
- **WHEN** (-1,0), (2700,0), and ocean-margin (0,0) are queried
- **THEN** all are invalid for foot movement; land-side ordinary cells are valid subject to local obstacles and footprints; the frame is never pre-created as rooms.

#### Scenario: Anchor and port land
- **WHEN** all declared anchor centers and harbor centers are evaluated
- **THEN** all lie inside the mainland polygon while knowledge visibility remains authoritative and unbuilt anchors create no invented settlement maps.

#### Scenario: The closed ridge and waterways are impassable
- **WHEN** a summit-ridge cell away from every authored pass, or an ordinary river cell, is queried
- **THEN** it is invalid for foot movement, while the authored pass window and declared fords are walkable.
