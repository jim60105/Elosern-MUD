## MODIFIED Requirements

### Requirement: WILDERNESS_ENTRY_REGISTRY links a grid-placed anchor to an authored wilderness footprint and gates
Immutable game wilderness-entry views SHALL derive solely from settlement-owned footprint and qualified gate relationships, retaining point-entry, approach, uniqueness and lore-mirroring semantics.

#### Scenario: The registry declares settlement footprints and gate destinations
- **WHEN** `WILDERNESS_ENTRY_REGISTRY` is inspected
- **THEN** it contains exactly one entry per discovered settlement document whose
  `wilderness_entry` is set, keyed by that document's `location_ref`, each carrying that
  document's footprint mask and gate destination nodes; every single-`#` entry has exactly one
  gate; and no test asserts a fixed roster of entries, a fixed cell count or a fixed origin

#### Scenario: Derived geometry matches the authored mask
- **WHEN** a synthetic mask with rows `###`, `.##`, `###` is placed at origin `(10,20)` with north and west return gates
- **THEN** its midpoint anchor is `(11,21)`, its occupied cells exclude `(10,21)`, its north-return approach is `(11,19)` and its west-return approach is `(13,21)`; shipped-coordinate preservation belongs to temporary conversion evidence

#### Scenario: Gate identity is globally unique

- **WHEN** the derived `(approach_cell, return_direction)` pairs of all gates in the registry
  are collected
- **THEN** no pair occurs twice, and no footprint cell of any entry equals another entry's gate
  approach cell or point-shape anchor cell

#### Scenario: A point-shape entry expresses cave semantics with no footprint
- **WHEN** an entry is constructed with a single-`#` mask, one gate, and any origin
- **THEN** its `footprint_cells` is empty, its `anchor_cell` is the origin, and its
  `approach_cell(gate)` equals its `anchor_cell`

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
- **WHEN** the dataclasses are defined
- **THEN** entry/gate values are immutable and resolve direction, target, mask, origin and gates from the settlement document, with runtime coordinates derived from the qualified target

#### Scenario: Shape mask placement convention
- **WHEN** an entry's `shape` is authored
- **THEN** it is an ASCII mask of `#` (anchor footprint cell) and `.` (outside), placed so that
  `shape[0][0]` corresponds to wilderness cell `origin_xy`

#### Scenario: Point-shape anchor exposes only its authored gate direction
- **WHEN** an entry has exactly one `#` cell
- **THEN** it is a point-shape anchor that owns no footprint cells, and only the single gate's
  authored `return_direction` at its anchor cell is a gateway; every other direction follows
  ordinary provider validity and resolves as an ordinary wilderness step

#### Scenario: Footprint-anchor gates are reachable only at their approach cells
- **WHEN** an entry has more than one `#` cell
- **THEN** it owns every mask cell as a footprint cell, and each of its gates is reachable only
  at that gate's exterior approach cell, where `return_direction` names the direction a
  wilderness-side traveler takes to enter the anchor

#### Scenario: Derived helper definitions
- **WHEN** the derived pure helpers are evaluated
- **THEN** `footprint_cells` is origin + mask offsets (empty for point-shape), `anchor_cell` is
  the bounding-box midpoint under floor division, and `approach_cell(gate)` is the anchor cell
  for point-shape entries; otherwise the first cell walking from `anchor_cell` along the face
  opposite `return_direction` that lies outside the footprint

#### Scenario: Anchor coverage is required but not exhaustive
- **WHEN** the registry's `anchor_key` coverage is checked
- **THEN** every entry's `anchor_key` exists as a key in change 12's
  `ANCHOR_PLACEMENT_REGISTRY`, the registry SHALL NOT be required to contain an entry for
  every `ANCHOR_PLACEMENT_REGISTRY` key, and it SHALL hold one entry per settlement reachable
  across the wilderness

#### Scenario: Currently shipped registry contents
- **WHEN** the registry's current authored contents are inspected
- **THEN** the registry owns the entry set, masks, origins, and gate destinations;
  the capital's gates resolve to its declared metric sparse nodes, and the village's
  point entrance returns to its declared entrance node

#### Scenario: Anchor cell uses bounding-box midpoint floor division
- **WHEN** `anchor_cell` is computed
- **THEN** it is the bounding-box midpoint `((min_x + max_x) // 2, (min_y + max_y) // 2)` of the
  `#` cells under Python floor division

#### Scenario: Gate geometry pairs are unique registry-wide
- **WHEN** all gates' `(approach_cell, return_direction)` pairs are collected
- **THEN** no two gates in the whole registry share the same pair, and no entry's footprint
  overlaps another entry's footprint

### Requirement: WildernessReturnExit routes every registered approach-cell-and-direction pair back to the grid
`typeclasses.exits.py::WildernessReturnExit`, subclassing the stock
`evennia.contrib.grid.wilderness.wilderness.WildernessExit`, SHALL be
`ElosernWildernessMapProvider.exit_typeclass`. A gateway step, recognized by one shared registry helper's match
on `approach_cell(gate)` and that gate's `return_direction`, SHALL move the traverser to the
`GridRoom` at the gate's `grid_xy`/`z_map_key`. `grid_xy` is an integer-meter
coordinate in that settlement's local frame.

#### Scenario: Traversing north from the south approach cell returns through the south gate
- **WHEN** a character at the south gate's derived approach cell traverses the `"north"` exit
- **THEN** the character's new location is the `capital_altoria` South Gate `GridRoom` object at
  the gate destination node's current authored grid coordinate

#### Scenario: Traversing west from the east approach cell returns through the east gate
- **WHEN** a character at the east gate's derived approach cell traverses the `"west"` exit
- **THEN** the character's new location is the `capital_altoria` East Gate `GridRoom` object at
  the gate destination node's current authored grid coordinate (the same object instance that existed before the character
  first entered the wilderness through it)

#### Scenario: The return direction at the wrong approach cell is not a gateway
- **WHEN** a character at a gate's approach cell traverses a direction other than that gate's
  `return_direction`
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
- **THEN** it goes through one shared registry helper, also used by the canonical resolver,
  that returns the owning entry and gate

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
  `wilderness_xy` and exit key `"south"`) SHALL NOT exist in any form

#### Scenario: This requirement governs routing only
- **WHEN** the clock cost of a successful traversal is considered
- **THEN** it is governed by the separate "Every successful WildernessReturnExit traversal
  advances the clock, not only the registered return branch" requirement below, which applies
  uniformly regardless of which routing branch was taken
