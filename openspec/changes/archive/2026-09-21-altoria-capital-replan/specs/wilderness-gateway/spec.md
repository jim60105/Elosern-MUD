## MODIFIED Requirements

### Requirement: WILDERNESS_ENTRY_REGISTRY links a grid-placed anchor to an authored wilderness footprint and gates
`world/lore/wilderness_entry.py` SHALL define frozen `WildernessGate` (`return_direction: str`,
`grid_xy: tuple[int, int]`, `z_map_key: str`) and `WildernessEntryPoint` (`anchor_key: str`,
`shape: tuple[str, ...]`, `origin_xy: tuple[int, int]`, `gates: tuple[WildernessGate, ...]`)
dataclasses and a module-level `WILDERNESS_ENTRY_REGISTRY: dict[str, WildernessEntryPoint]`.
`shape` is an ASCII mask of `#` (anchor footprint cell) and `.` (outside), placed so that
`shape[0][0]` corresponds to wilderness cell `origin_xy`. An entry with exactly one `#` cell is a
point-shape anchor: it owns no footprint cells and every direction at its anchor cell is a
gateway to its single registered gate. An entry with more than one `#` cell owns every mask cell
as a footprint cell, and each of its gates is reachable only at that gate's exterior approach
cell, where `return_direction` names the direction a wilderness-side traveler takes to enter the
anchor. The registry SHALL expose derived pure helpers — `footprint_cells` (origin + mask
offsets, empty for point-shape), `anchor_cell` (integer-rounded centroid of the `#` cells), and
`approach_cell(gate)` (the anchor cell for point-shape entries; otherwise the first cell walking
from `anchor_cell` along the face opposite `return_direction` that lies outside the footprint) —
as the single geometry source for all consumers. Every entry's `anchor_key` SHALL exist as a key
in change 12's `ANCHOR_PLACEMENT_REGISTRY`. The registry SHALL NOT be required to contain an
entry for every `ANCHOR_PLACEMENT_REGISTRY` key. It SHALL hold one entry per settlement
reachable across the wilderness, and currently holds two. The first is keyed
`"capital_altoria"`: a 5×5 all-`#` mask at origin `(58, 98)` (anchor cell `(60, 100)`) with
gates `return_direction="n"` → `(3, 0, "capital_altoria")` (approach cell `(60, 97)`) and
`return_direction="w"` → `(6, 3, "capital_altoria")` (approach cell `(63, 100)`). The second is
keyed `"village_ciaran"`: a smaller mask placed well clear of the capital's footprint, with a
single gate returning to the village's entrance node.
`anchor_cell` SHALL be the bounding-box midpoint `((min_x + max_x) // 2, (min_y + max_y) // 2)`
of the `#` cells under Python floor division, and no two gates in the whole registry SHALL share
the same `(approach_cell, return_direction)` pair. No entry's footprint SHALL overlap another
entry's footprint.

#### Scenario: The registry has exactly one v2 entry after this change
<!-- Scenario name retained verbatim: a MODIFIED block may not drop or rename an existing
     scenario. The "exactly one" wording is historical; the assertion below is the current
     two-entry state. -->
- **WHEN** `WILDERNESS_ENTRY_REGISTRY` is inspected
- **THEN** it contains exactly two entries; the `"capital_altoria"` entry has a 5×5 mask of `#`,
  `origin_xy` `(58, 98)`, and gates exactly `("n" → (3,0)), ("w" → (6,3))` on map
  `capital_altoria`; the `"village_ciaran"` entry has a smaller mask and one gate returning to
  the village's entrance node; and no test asserts that any other `ANCHOR_PLACEMENT_REGISTRY`
  key must also appear

#### Scenario: Derived geometry matches the authored mask
- **WHEN** `footprint_cells`, `anchor_cell`, and `approach_cell` are read for the
  `"capital_altoria"` entry
- **THEN** `footprint_cells` is the 25-cell set `58 <= x <= 62 and 98 <= y <= 102`, `anchor_cell`
  is `(60, 100)`, the `"n"` gate's approach cell is `(60, 97)`, and the `"w"` gate's approach
  cell is `(63, 100)`

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

### Requirement: WildernessReturnExit routes every registered approach-cell-and-direction pair back to the grid
`typeclasses.exits.py::WildernessReturnExit`, subclassing
`evennia.contrib.grid.wilderness.wilderness.WildernessExit`, SHALL be
`ElosernWildernessMapProvider.exit_typeclass`. It SHALL recognize a gateway step through one
shared registry helper — the same helper the canonical resolver uses — that returns the owning
entry and gate if and only if the traverser's current coordinates equal some entry's
`approach_cell(gate)` and the exit's direction equals that gate's `return_direction`. For a
recognized gateway step it SHALL move the traversing object to the `GridRoom` at the gate's
`grid_xy`/`z_map_key` (resolved via the grid model, not via a hardcoded coordinate or via the
exit object's stored anchor). For every other coordinate or direction, its **routing**
(destination room, coordinate movement) SHALL behave identically to the stock
`WildernessExit`. The hardcoded legacy rule (current coordinates equal to an entry's single
`wilderness_xy` and exit key `"south"`) SHALL NOT exist in any form. This requirement governs
routing only — every successful traversal's **clock cost** is governed by the separate "Every
successful WildernessReturnExit traversal advances the clock, not only the registered return
branch" requirement below, which applies uniformly regardless of which routing branch was taken.

#### Scenario: Traversing north from the south approach cell returns through the south gate
- **WHEN** a character at `(60, 97)` traverses the `"north"` exit
- **THEN** the character's new location is the `capital_altoria` 南門 `GridRoom` object at grid
  `(3, 0, "capital_altoria")`

#### Scenario: Traversing south from the north approach cell returns through the north gate
<!-- Scenario name retained verbatim: a MODIFIED block may not rename a scenario. The capital's
     second gate is now the East Gate, approached from the east and entered travelling west. -->
- **WHEN** a character at `(63, 100)` traverses the `"west"` exit
- **THEN** the character's new location is the `capital_altoria` East Gate `GridRoom` object at
  grid `(6, 3, "capital_altoria")` (the same object instance that existed before the character
  first entered the wilderness through it)

#### Scenario: The return direction at the wrong approach cell is not a gateway
- **WHEN** a character at `(60, 97)` traverses `"south"`, or a character at `(63, 100)` traverses
  `"east"`
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
