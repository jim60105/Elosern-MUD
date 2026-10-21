# Spec Delta

## ADDED Requirements

### Requirement: The continent remains virtual with bounded local lookup
The wilderness SHALL comprise 2700 by 2700 one-kilometer logical cells with east/north axes and authoritative coastline/terrain validity. Sea, closed ridges, cliffs and water SHALL be impassable on foot. Ordinary movement SHALL use bounded local masks and sparse indices without whole-frame scans or room materialization.

#### Scenario: Frame and sea margin
- **WHEN** (-1,0), (2700,0), and ocean-margin (0,0) are queried
- **THEN** all are invalid for foot movement; land-side ordinary cells are valid subject to local obstacles and footprints; seven million rooms are never pre-created.

#### Scenario: Anchor and port land
- **WHEN** all nine declared anchor centers and six harbor centers are evaluated
- **THEN** all lie inside the mainland polygon while knowledge visibility remains authoritative and seven unbuilt anchors create no invented settlement maps.

## MODIFIED Requirements

### Requirement: ElosernWildernessMapProvider bounds the map to a 224x224 grid at 10 km per cell
<!-- Requirement title retained verbatim: a MODIFIED block may not rename the requirement ID.
     The body below is the current one-kilometre contract. -->
`world/maps/wilderness_provider.py` SHALL define `WILDERNESS_KM_PER_CELL = 1`,
`WILDERNESS_MAX_X = 2699`, `WILDERNESS_MAX_Y = 2699`, and `ElosernWildernessMapProvider`, a subclass
of `evennia.contrib.grid.wilderness.wilderness.WildernessMapProvider`, whose
`is_valid_coordinates` accepts exactly the coordinates `0 <= x <= WILDERNESS_MAX_X` and
`0 <= y <= WILDERNESS_MAX_Y` that are land-side, passable terrain and NOT an anchor footprint cell of any
`WILDERNESS_ENTRY_REGISTRY` entry (`WildernessEntryPoint.footprint_cells`). The single shared rule
is `is_valid_wilderness_cell`: frame, mainland polygon at the cell centre, off the closed summit
ridge and authored waterways, and outside every live footprint.

#### Scenario: Coordinates inside the bound and outside every footprint are valid
- **WHEN** a land-side passable fixture and an ocean-margin fixture lie inside the frame
- **THEN** only the land-side non-footprint fixture is valid; frame corners (0,0) and (2699,2699) being in bounds never imply land validity.

#### Scenario: Coordinates outside the bound are invalid
- **WHEN** `ElosernWildernessMapProvider().is_valid_coordinates(wilderness, (-1, 0))` and
  `(WILDERNESS_MAX_X + 1, 0)` are checked
- **THEN** both return `False`

#### Scenario: Anchor footprint cells are invalid
- **WHEN** `is_valid_coordinates` is checked for the `capital_altoria` anchor cell `(860, 1080)`,
  a corner footprint cell `(857, 1076)`, and the two gate approach cells `(860, 1077)` and
  `(864, 1080)`
- **THEN** the two footprint cells return `False` and the two approach cells return `True`

#### Scenario: Registry patches change footprint validity without patching the provider
- **WHEN** a test patches `WILDERNESS_ENTRY_REGISTRY` with an extra point-shape entry and with an
  extra multi-cell entry, leaving the provider untouched
- **THEN** the point-shape anchor cell stays valid, its gate cell behaves as a gateway (valid),
  and the multi-cell entry's mask cells become invalid while its neighbors stay valid; restoring
  the registry restores validity

#### Scenario: The bound approximates world_info.md's stated continent area
- **WHEN** the coastline polygon and enclosing frame areas are computed
- **THEN** vector mainland area is 5000000km² and the 2700km square frame is 7290000km² including ocean; raster counts need not equal vector area.

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
`ElosernWildernessMapProvider.get_location_name(coordinates)` SHALL return
`WILDERNESS_REGION_REGISTRY[region_for_coordinates(*coordinates)].display_name_zh`.
`at_prepare_room(coordinates, caller, room)` SHALL set
`room.ndb.active_desc` from `terrain_description(*coordinates)` and `room.scene_archetype` from
`region_for_coordinates(*coordinates)`, unconditionally, on every call. It SHALL additionally
ensure the coordinate's deterministic monster population per the scenarios below.

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
- **WHEN** `at_prepare_room((860, 1077), caller, room)` is called on a `TerrainRoom` carrying the
  eight directional exits
- **THEN** the `"north"` exit's locks allow `traverse` and `view`, and no other exit's locks are
  modified by the hook

#### Scenario: at_prepare_room touches no locks away from approach cells
- **WHEN** `at_prepare_room` is called for an ordinary wilderness cell or for the opposite gate's
  approach cell `(864, 1080)`
- **THEN** at the ordinary cell no exit's locks are modified, and at `(864, 1080)` only the
  `"west"` exit's locks are opened — an approach cell never opens another gate's exit

#### Scenario: A point-shape anchor opens all eight exits
<!-- Scenario name retained verbatim: a MODIFIED block may not rename a scenario. A concealed
     point entry now exposes only its authored entry direction. -->
- **WHEN** a concealed point entry is prepared or resolved
- **THEN** only its authored eligible entry direction is gateway-visible; unrelated directions
  follow ordinary terrain validity and unknown players learn no concealed destination.

#### Scenario: A gate lock does not leak when the pooled room moves to a non-approach coordinate
- **WHEN** a pooled `TerrainRoom` was activated at `(860, 1077)` (opening its `"north"` exit) and
  is later activated at a coordinate that is not any approach cell
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

#### Scenario: Population assurance calls the capability resolver
- **WHEN** `at_prepare_room` ensures the coordinate's deterministic monster population — the
  `wilderness-monster-population` capability
- **THEN** it does so by calling
  `world.maps.wilderness_population.ensure_population(room.wilderness, coordinates)` when
  `room.wilderness` resolves to the wilderness script, and SHALL be a population no-op (setting
  only the description and scene archetype) when no wilderness script is attached, so a pooled or
  unit-test `TerrainRoom` is never required to have one

#### Scenario: Gate exit locks use the stock lock-string form
- **WHEN** `coordinates` equal some registered gate's `approach_cell`
- **THEN** `at_prepare_room` SHALL set that gate's `return_direction` long-form exit (the contrib's
  normalized exit key) on the room to `traverse:true();view:true()` locks — the same lock-string
  form the stock `set_active_coordinates` pass uses for valid neighbors — so the gate exit is
  visible and offered from the approach cell even though the footprint cell beyond it is
  provider-invalid
- **AND** the gateway step itself is performed by `WildernessReturnExit`'s registry branch, not by
  ordinary coordinate movement

#### Scenario: Non-approach coordinates leave locks alone
- **WHEN** `coordinates` name a coordinate that is not an approach cell
- **THEN** `at_prepare_room` SHALL NOT touch any exit's locks

#### Scenario: Point anchors open all eight exits to match the resolver
<!-- Scenario name retained verbatim: a MODIFIED block may not rename a scenario. The resolver
     and the exit now agree on one authored entry direction, not eight. -->
- **WHEN** a concealed point entry is prepared or resolved
- **THEN** only its authored eligible entry direction is gateway-visible; unrelated directions
  follow ordinary terrain validity and unknown players learn no concealed destination.
