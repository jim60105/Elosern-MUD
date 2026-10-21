# Spec Delta

## ADDED Requirements

### Requirement: Physical footprints and concealed point entries preserve approaches
Urban routing masks SHALL rasterize authored irregular physical footprints. Capital south/east gates SHALL retain facing and exact transformed entrance geometry with exterior approaches outside the mask. Ciaran SHALL be a hidden point entrance without a village-wide wilderness obstacle.

#### Scenario: Capital mask and approaches
- **WHEN** capital geometry is rasterized at 1km scale
- **THEN** the approximately 40km² physical city controls the irregular mask rather than old 5x5 cells; south/east approaches lie outside it and crossing geometry charges once.

#### Scenario: Point direction does not hijack routes
- **WHEN** a traveller selects an unrelated neighboring direction at Ciaran’s entry cell
- **THEN** ordinary wilderness movement remains ordinary; only the authored eligible entrance direction resolves to the hidden path and unknown players receive no village disclosure.

## MODIFIED Requirements

### Requirement: WILDERNESS_ENTRY_REGISTRY links a grid-placed anchor to an authored wilderness footprint and gates
`world/lore/wilderness_entry.py` SHALL define the frozen `WildernessGate` and
`WildernessEntryPoint` dataclasses and a module-level
`WILDERNESS_ENTRY_REGISTRY: dict[str, WildernessEntryPoint]`, and SHALL expose the derived
pure helpers `footprint_cells`, `anchor_cell`, and `approach_cell(gate)` as the single geometry
source for all consumers. A point-shape entry's `approach_cell(gate)` IS its anchor cell, and only
that gate's authored `return_direction` is a gateway. `gate.grid_xy` remains the destination
`GridRoom`'s logical grid coordinate in this change; `activate-metric-settlements` owns the
meter-coordinate cutover, so this change's transformed entrance geometry is carried by the sparse
graph's authored physical positions, not by new grid coordinates.

#### Scenario: The registry has exactly one v2 entry after this change
- **WHEN** the declared metric settlement geometry is validated and used for routing
- **THEN** Altoria binds plaza (3500,2850) to wilderness (860,1080), south/east gate nodes (3050,150)/(6500,3010) to facing-preserving valid approaches outside its rasterized irregular footprint; Ciaran binds plaza (220,305) to (1340,1220) with hidden path (35,270) as an explicit-direction point entrance. Geometry is frozen, exact transforms supply one approach segment, unrelated directions remain ordinary and hidden knowledge is not disclosed.

#### Scenario: Derived geometry matches the authored mask
- **WHEN** the derived helpers are evaluated against the authored rows
- **THEN** each entry's `footprint_cells` equals its own `#` cells at `origin_xy` (empty for a
  point shape), `anchor_cell` is the floor-division midpoint of the `#` bounding box, and
  `approach_cell(gate)` walks from the anchor along the gate's opposite face to the first cell
  outside the footprint (the anchor cell itself for a point shape)

#### Scenario: Gate identity is globally unique

- **WHEN** the derived `(approach_cell, return_direction)` pairs of all gates in the registry
  are collected
- **THEN** no pair occurs twice, and no footprint cell of any entry equals another entry's gate
  approach cell or point-shape anchor cell

#### Scenario: A point-shape entry expresses cave semantics with no footprint
- **WHEN** a `WILDERNESS_ENTRY_REGISTRY` entry's mask contains exactly one `#`
- **THEN** `is_point_shape` is true, `footprint_cells` is empty, `approach_cell(gate)` is the
  anchor cell, and the entry must author exactly one gate

#### Scenario: Every entry's anchor_key resolves against ANCHOR_PLACEMENT_REGISTRY
- **WHEN** every entry in `WILDERNESS_ENTRY_REGISTRY` is inspected
- **THEN** each entry's `anchor_key` exists as a key in `world.lore.anchor_placement.
  ANCHOR_PLACEMENT_REGISTRY`

#### Scenario: WILDERNESS_ENTRY_REGISTRY is mirrored into LoreRecord Scripts idempotently
- **WHEN** `sync_all()` runs, and then runs a second time
- **THEN** a `LoreRecord` Script keyed `"lore:wilderness_entries:capital_altoria"` exists after
  both calls, and no duplicate exists after the second

#### Scenario: Two settlements' footprints do not overlap
- **WHEN** the footprint cells of every registry entry are collected
- **THEN** no cell belongs to two entries

#### Scenario: Gate and entry dataclass fields
- **WHEN** the dataclasses are inspected
- **THEN** `WildernessGate` carries exactly `return_direction`, `grid_xy` and `z_map_key`, and
  `WildernessEntryPoint` carries exactly `anchor_key`, `shape`, `origin_xy` and `gates`; every
  field is frozen, and `grid_xy` is this change's logical grid destination

#### Scenario: Shape mask placement convention
- **WHEN** a mask row and column are indexed
- **THEN** `shape[row][column]` maps to wilderness cell
  `(origin_xy[0] + column, origin_xy[1] + row)`; row 0 is the smallest Y and column 0 the
  smallest X

#### Scenario: Point-shape anchor opens every direction to its gate
<!-- Scenario name retained verbatim: a MODIFIED block may not rename a scenario. The body is
     narrowed to the concealed-entry rule: only the authored direction is a gateway. -->
- **WHEN** a point-shape entry's anchor cell is prepared or resolved
- **THEN** only its authored `return_direction` is a gateway; every other direction at that
  cell follows ordinary provider validity and resolves as an ordinary wilderness step

#### Scenario: Footprint-anchor gates are reachable only at their approach cells
- **WHEN** an entry has more than one `#` cell
- **THEN** it owns every mask cell as a footprint cell, and each of its gates is reachable only
  at that gate's exterior approach cell, where `return_direction` names the direction a
  wilderness-side traveler takes to enter the anchor

#### Scenario: Derived helper definitions
- **WHEN** the module's public helpers are inspected
- **THEN** `footprint_cells` and `anchor_cell` are properties of `WildernessEntryPoint`,
  `approach_cell(gate)` is its method, `gate_for(return_direction)` returns the authored gate or
  `None`, and `validate_wilderness_entries()` is the module's pure validation entry point

#### Scenario: Anchor coverage is required but not exhaustive
- **WHEN** the registry's `anchor_key` coverage is checked
- **THEN** every entry's `anchor_key` exists as a key in change 12's
  `ANCHOR_PLACEMENT_REGISTRY`, the registry SHALL NOT be required to contain an entry for
  every `ANCHOR_PLACEMENT_REGISTRY` key, and it SHALL hold one entry per settlement reachable
  across the wilderness

#### Scenario: Currently shipped registry contents
- **WHEN** the shipped registry is read
- **THEN** it holds `capital_altoria` (a 7x9 mask at origin (857,1076), 40 `#` cells, anchor
  (860,1080), south gate `"n"` and east gate `"w"` on logical grid `(3,0)`/`(6,3)` of its own
  map) and `village_ciaran` (one `#` cell at (1340,1220), one gate `"n"` on logical grid
  `(0,1)`); no other entry is shipped

#### Scenario: Anchor cell uses bounding-box midpoint floor division
- **WHEN** an entry's `#` cells span columns `min_x..max_x` and rows `min_y..max_y`
- **THEN** `anchor_cell` is
  `(origin_x + (min_x + max_x) // 2, origin_y + (min_y + max_y) // 2)` using Python floor
  division, never rounding

#### Scenario: Gate geometry pairs are unique registry-wide
- **WHEN** all gates' `(approach_cell, return_direction)` pairs are collected
- **THEN** no two gates in the whole registry share the same pair, and no entry's footprint
  overlaps another entry's footprint

### Requirement: WildernessReturnExit routes every registered approach-cell-and-direction pair back to the grid
`typeclasses.exits.py::WildernessReturnExit`, subclassing the stock
`evennia.contrib.grid.wilderness.wilderness.WildernessExit`, SHALL be
`ElosernWildernessMapProvider.exit_typeclass`. A gateway step — recognized through one shared
registry helper, true if and only if the traverser's current coordinates equal some entry's
`approach_cell(gate)` and the exit's direction equals that gate's `return_direction` — SHALL
move the traversing object to the `GridRoom` at the gate's `grid_xy`/`z_map_key`. In this change
`grid_xy` is still the settled logical grid coordinate; `activate-metric-settlements` performs the
meter-coordinate cutover of the authored settlement maps, so the gate's physical entrance position
already comes from the sparse graph's metre table while the room lookup keeps the logical cell.

#### Scenario: Traversing north from the south approach cell returns through the south gate
- **WHEN** a character at `(860, 1077)` traverses the `"north"` exit
- **THEN** the character's new location is the `capital_altoria` 南門 `GridRoom` object at logical
  grid `(3, 0, "capital_altoria")` (its meter position (3050,150) arrives with
  `activate-metric-settlements`)

#### Scenario: Traversing south from the north approach cell returns through the north gate
<!-- Scenario name retained verbatim: a MODIFIED block may not rename a scenario. The capital's
     second gate is now the East Gate, approached from the east and entered travelling west. -->
- **WHEN** a character at `(864, 1080)` traverses the `"west"` exit
- **THEN** the character's new location is the `capital_altoria` East Gate `GridRoom` object at
  logical grid `(6, 3, "capital_altoria")` (the same object instance that existed before the
  character first entered the wilderness through it; its meter position (6500,3010) arrives with
  `activate-metric-settlements`)

#### Scenario: The return direction at the wrong approach cell is not a gateway
- **WHEN** a character at `(860, 1077)` traverses `"west"`, or a character at `(864, 1080)`
  traverses `"east"`
- **THEN** the traversal routes like the stock `WildernessExit` (ordinary coordinate movement to
  the provider-valid neighbor), reaching no grid room

#### Scenario: A step toward the footprint is refused
- **WHEN** a character at any cell adjacent to the `capital_altoria` footprint on a non-gate face
  traverses the exit pointing into the footprint
- **THEN** the traversal fails like any step toward an invalid coordinate (the exit is hidden and
  blocked by the provider-invalid lock state and `at_traverse_coordinates` refuses it), the
  character's location is unchanged, `get_world_clock().tick` is unchanged, and no
  map-knowledge observation is recorded

#### Scenario: Every other coordinate and direction routes like a stock WildernessExit
- **WHEN** a character traverses any directional exit at a coordinate that is not any
  entry's `approach_cell`, or traverses a direction other than the matching gate's
  `return_direction` at an approach cell that is not covered by the previous scenario
- **THEN** the traversal's destination behaves identically to
  `evennia.contrib.grid.wilderness.wilderness.WildernessExit.at_traverse` (ordinary coordinate
  movement within the wilderness)

#### Scenario: Gateway recognition shares the canonical resolver's helper
- **WHEN** a gateway step is recognized
- **THEN** it goes through one shared registry helper — the same helper the canonical resolver
  uses — that returns the owning entry and gate

#### Scenario: The grid room is resolved through the grid model
- **WHEN** a recognized gateway step resolves its destination
- **THEN** the `GridRoom` is resolved via the grid model, not via a hardcoded coordinate or via
  the exit object's stored anchor

#### Scenario: Non-gateway routing matches the stock exit
- **WHEN** the step is at any other coordinate or direction
- **THEN** the exit's **routing** (destination room, coordinate movement) behaves identically to
  the stock `WildernessExit`

#### Scenario: The hardcoded legacy rule is removed
- **WHEN** gateway recognition is implemented
- **THEN** the hardcoded legacy rule (current coordinates equal to an entry's single
  `wilderness_xy` and exit key `"west"`) SHALL NOT exist in any form

#### Scenario: This requirement governs routing only
- **WHEN** the clock cost of a successful traversal is considered
- **THEN** it is governed by the separate "Every successful WildernessReturnExit traversal
  advances the clock, not only the registered return branch" requirement below, which applies
  uniformly regardless of which routing branch was taken

### Requirement: WILDERNESS_ENTRY_REGISTRY authored data is validated before persistence
`world/lore/wilderness_entry.py` SHALL provide `validate_wilderness_entries()` — a pure,
DB-free check of the whole registry — and `world/lore/sync.py`'s wilderness mirror step SHALL
run it before mirroring, so malformed authored data fails at startup rather than producing an
unwalkable or contradictory world. The shipped registry SHALL pass validation. Validation uses the
provider's shared walkability rule (frame, mainland, passable terrain, footprint exclusion) so an
authored footprint or approach can never name impassable ground.

#### Scenario: The shipped registry validates
- **WHEN** `validate_wilderness_entries()` is called against the shipped
  `WILDERNESS_ENTRY_REGISTRY`
- **THEN** it raises nothing

#### Scenario: Malformed authored entries are each rejected
- **WHEN** `validate_wilderness_entries()` is called with a registry patched to contain one
  malformed entry at a time — empty mask, out-of-bounds `#` cell, disconnected footprint,
  non-canonical or duplicated `return_direction`, gate face not crossing the footprint,
  point-shape entry with zero or two gates, `grid_xy` outside its map, or unknown `anchor_key`
- **THEN** each patch raises a validation error naming the offending entry and the rejected rule

#### Scenario: Malformed masks and colliding geometry are each rejected
- **WHEN** `validate_wilderness_entries()` is called with a registry patched to contain one
  malformed entry at a time — ragged mask rows, a character outside `#`/`.`, an all-`.` mask, a
  mask whose bounding-box midpoint falls on a `.` cell, two entries whose footprints overlap, a
  footprint containing another entry's gate approach cell, two gates sharing one destination
  `(grid_xy, z_map_key)` room, or a point anchor with a provider-invalid neighbor direction
- **THEN** each patch raises a validation error naming the offending entry and the rejected rule

#### Scenario: sync_all refuses to mirror a malformed registry
- **WHEN** `sync_all()` runs with the wilderness registry patched to a malformed entry
- **THEN** the run fails with the validation error before any `lore:wilderness_entries:*` Script
  is created or updated

#### Scenario: Per-entry rejection conditions
- **WHEN** `validate_wilderness_entries()` checks an entry
- **THEN** it SHALL reject: an empty mask or one with no `#`; any `#` cell outside the provider's
  frame or on impassable terrain (sea, closed ridge, waterway); a footprint whose `#` cells are
  not 4-connected; a `return_direction` that is not a canonical wilderness direction or is
  duplicated within one entry; a footprint-entry gate whose approach-cell ray from `anchor_cell`
  crosses no footprint cell or whose approach cell is not a walkable cell outside the footprint;
  a point-shape entry with any number of gates other than exactly one, or whose anchor cell or
  authored entry-direction neighbor is not walkable; a `grid_xy` outside the extent of the map
  named by its `z_map_key`; and an `anchor_key` absent from `ANCHOR_PLACEMENT_REGISTRY`

#### Scenario: Mask shape and anchor cell well-formedness
- **WHEN** an entry's mask and derived anchor cell are validated
- **THEN** the mask SHALL be a well-formed rectangle — every row the same non-empty length,
  containing only `#` and `.` (the `altoria_capital.MAPSTR` loading expectation) — and the
  derived `anchor_cell` SHALL itself be a `#` cell

#### Scenario: Global cross-entry constraints
- **WHEN** the validator checks the registry globally
- **THEN** two entries SHALL NOT have overlapping footprints; no footprint SHALL contain
  another entry's gate approach cell or point-shape anchor cell; two gates SHALL NOT share the
  same `(approach_cell, return_direction)` pair; and two gates SHALL NOT share the same
  destination `(grid_xy, z_map_key)` room — one grid room hosts exactly one WildernessGateExit
  slot, so a second gate on that room would silently displace the first at provisioning time

#### Scenario: Point-shape anchors need all neighbors provider-valid
<!-- Scenario name retained verbatim: a MODIFIED block may not rename a scenario. The authored
     rule now covers the anchor cell and the authored entry direction's neighbor only. -->
- **WHEN** a point-shape entry is validated
- **THEN** its anchor cell and the neighbor its authored `return_direction` leads to SHALL be
  provider-valid walkable terrain; the other seven neighbors follow ordinary terrain validity, so a
  coastal cave may be authored next to water
