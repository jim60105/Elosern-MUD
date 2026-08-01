## Purpose

The single, shared `scene_archetype` seam across map-layer room types: `SceneArchetypeMixin` adopted
independently by the grid layer's `GridRoom` and the wilderness/Virtual layer's `TerrainRoom`, so a
future art system (change 22) can read one attribute contract without `isinstance` branches per room
type.

## Requirements


### Requirement: SceneArchetypeMixin is the single, shared scene_archetype seam
`typeclasses/rooms.py` SHALL define `SceneArchetypeMixin`, a plain mixin class carrying a persistent
`scene_archetype: str | None` attribute defaulting to `None`, unvalidated against any registry.

#### Scenario: scene_archetype defaults to None and accepts any string
- **WHEN** a room whose class includes `SceneArchetypeMixin` is created with no `scene_archetype`
  supplied, and the value is later set to an arbitrary string
- **THEN** it defaults to `None` and accepts the arbitrary string with no registry lookup

### Requirement: GridRoom is retrofitted onto SceneArchetypeMixin without changing its contract
`typeclasses/rooms.py::GridRoom` SHALL include `SceneArchetypeMixin` in its base classes instead of
declaring `scene_archetype` directly. `GridRoom`'s observable behavior (default value, unvalidated
assignment, persistence across a reload) SHALL be unchanged from change 12's own
`grid-room-typeclasses` specification.

#### Scenario: GridRoom's scene_archetype behavior is unchanged
- **WHEN** change 12's own `grid-room-typeclasses` test suite (scene_archetype defaults to `None`,
  accepts an arbitrary string with no registry lookup, persists across a reload) is run unmodified
  against `GridRoom` after this change lands
- **THEN** every one of those tests still passes with no edit to its assertions

#### Scenario: GridRoom includes SceneArchetypeMixin in its MRO
- **WHEN** `GridRoom`'s method resolution order is inspected after this change lands
- **THEN** `SceneArchetypeMixin` appears in it

### Requirement: TerrainRoom adopts the identical mixin
`typeclasses/rooms.py::TerrainRoom`, subclassing `SceneArchetypeMixin` and
`evennia.contrib.grid.wilderness.wilderness.WildernessRoom`, SHALL expose the identical
`scene_archetype` attribute contract as `GridRoom`.

#### Scenario: TerrainRoom and GridRoom share the same attribute contract
- **WHEN** a `TerrainRoom` and a `GridRoom` are each created with no `scene_archetype` supplied
- **THEN** both default to `None`, and setting either to the same string succeeds identically on both,
  with no registry lookup on either

#### Scenario: TerrainRoom is not an XYZRoom
- **WHEN** `TerrainRoom`'s method resolution order is inspected
- **THEN** it includes `WildernessRoom` and `SceneArchetypeMixin` but does not include
  `evennia.contrib.grid.xyzgrid.xyzroom.XYZRoom`, confirming the Grid and Virtual layers remain
  architecturally disjoint apart from the shared mixin
