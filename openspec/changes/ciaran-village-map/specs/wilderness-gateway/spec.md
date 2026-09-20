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
gates `return_direction="n"` → `(2, 0, "capital_altoria")` (approach cell `(60, 97)`) and
`return_direction="s"` → `(2, 4, "capital_altoria")` (approach cell `(60, 103)`). The second is
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
  `origin_xy` `(58, 98)`, and gates exactly `("n" → (2,0)), ("s" → (2,4))` on map
  `capital_altoria`; the `"village_ciaran"` entry has a smaller mask and one gate returning to
  the village's entrance node; and no test asserts that any other `ANCHOR_PLACEMENT_REGISTRY`
  key must also appear

#### Scenario: Derived geometry matches the authored mask
- **WHEN** `footprint_cells`, `anchor_cell`, and `approach_cell` are read for the
  `"capital_altoria"` entry
- **THEN** `footprint_cells` is the 25-cell set `58 <= x <= 62 and 98 <= y <= 102`, `anchor_cell`
  is `(60, 100)`, the `"n"` gate's approach cell is `(60, 97)`, and the `"s"` gate's approach
  cell is `(60, 103)`

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
