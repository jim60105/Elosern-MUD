## Purpose

Define the immutable grid-placement registry that gives geographic anchors their position on the
xyzgrid layer, kept separate from the frozen `Anchor` lore dataclass.

## Requirements


### Requirement: AnchorPlacement is a frozen dataclass separate from Anchor
`world/lore/anchor_placement.py` SHALL define a frozen `AnchorPlacement` dataclass with fields
`anchor_key: str`, `zcoord: str`, and `entrance_xy: tuple[int, int]`, and a module-level
`ANCHOR_PLACEMENT_REGISTRY: dict[str, AnchorPlacement]`. `world/lore/anchors.py`'s frozen `Anchor`
dataclass (change 2) SHALL NOT be modified to add any placement, coordinate, or grid field.

#### Scenario: Anchor dataclass is untouched
- **WHEN** `world/lore/anchors.py` is inspected after this change lands
- **THEN** the `Anchor` dataclass still has exactly the fields `key`, `kind`, `display_name_zh`,
  `nation_key`, `population`, `floors`, `description`, with no new field added

#### Scenario: AnchorPlacement carries no lore fact
- **WHEN** `AnchorPlacement` is inspected
- **THEN** it has exactly the fields `anchor_key`, `zcoord`, `entrance_xy`, and none of `Anchor`'s
  lore fields (`population`, `floors`, `nation_key`, `description`, `display_name_zh`) are duplicated
  onto it

### Requirement: Every placement's anchor_key resolves against ANCHOR_REGISTRY
Every entry in `ANCHOR_PLACEMENT_REGISTRY` SHALL have an `anchor_key` that exists as a key in
`world/lore/anchors.py::ANCHOR_REGISTRY`.

#### Scenario: capital_altoria's placement resolves
- **WHEN** `ANCHOR_PLACEMENT_REGISTRY["capital_altoria"]` is inspected
- **THEN** its `anchor_key` (`"capital_altoria"`) exists as a key in `ANCHOR_REGISTRY`

#### Scenario: No placement references a nonexistent anchor
- **WHEN** every entry in `ANCHOR_PLACEMENT_REGISTRY` is inspected
- **THEN** each entry's `anchor_key` exists in `ANCHOR_REGISTRY`

### Requirement: ANCHOR_PLACEMENT_REGISTRY is intentionally partial
`ANCHOR_PLACEMENT_REGISTRY` SHALL NOT be required to contain an entry for every key in
`ANCHOR_REGISTRY`. This change SHALL populate exactly one entry, keyed `"capital_altoria"`.

#### Scenario: The registry has exactly one entry after this change
- **WHEN** `ANCHOR_PLACEMENT_REGISTRY` is inspected
- **THEN** it contains exactly one entry, keyed `"capital_altoria"`, and no test in this change's
  own suite asserts that any other `ANCHOR_REGISTRY` key must also appear

#### Scenario: capital_altoria's placement matches the sample city's spawned AnchorRoom
- **WHEN** `sync_grid()` (the `grid-room-sync` capability) has run and the spawned `AnchorRoom` for
  `capital_altoria` is inspected
- **THEN** `ANCHOR_PLACEMENT_REGISTRY["capital_altoria"].zcoord` equals that room's `.xyz[2]` and
  `ANCHOR_PLACEMENT_REGISTRY["capital_altoria"].entrance_xy` equals `(room.xyz[0], room.xyz[1])`

### Requirement: ANCHOR_PLACEMENT_REGISTRY is mirrored into LoreRecord Scripts idempotently
`world/lore/sync.py::_ALL_REGISTRIES` SHALL include `ANCHOR_PLACEMENT_REGISTRY` under the category
key `"anchor_placements"`, so `sync_all()` mirrors it into `LoreRecord` Scripts exactly as it mirrors
every other lore registry, including idempotency across repeated calls.

#### Scenario: sync_all mirrors anchor placements
- **WHEN** `sync_all()` runs
- **THEN** a `LoreRecord` Script exists keyed `"lore:anchor_placements:capital_altoria"` with
  `db.fields` matching `ANCHOR_PLACEMENT_REGISTRY["capital_altoria"]`

#### Scenario: Repeated sync creates no duplicate placement records
- **WHEN** `sync_all()` is called twice in succession
- **THEN** exactly one `LoreRecord` Script exists for `"lore:anchor_placements:capital_altoria"`
  after the second call

#### Scenario: lore-startup-sync's own spec is unmodified
- **WHEN** `openspec/specs/lore-startup-sync/spec.md` is inspected after this change lands
- **THEN** its text is unchanged — this change extends `sync_all()`'s behavior without altering any
  requirement or scenario that spec already documents
