# Spec Delta

## MODIFIED Requirements

### Requirement: WILDERNESS_ENTRY_REGISTRY links a grid-placed anchor to an authored wilderness footprint and gates
Immutable game wilderness-entry views SHALL derive solely from settlement-owned footprint and qualified gate relationships, retaining point-entry, approach, uniqueness and lore-mirroring semantics.

#### Scenario: The registry declares settlement footprints and gate destinations
- **WHEN** `WILDERNESS_ENTRY_REGISTRY` is inspected
- **THEN** it contains the authored entries; `"capital_altoria"` has its declared irregular
  footprint and gates returning to the `south_gate` and `east_gate` sparse nodes on map
  `capital_altoria`; `"village_ciaran"` is a point shape with one gate
  returning to the village's entrance node; and no test asserts that any other
  `ANCHOR_PLACEMENT_REGISTRY` key must also appear

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

