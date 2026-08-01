## MODIFIED Requirements

### Requirement: GridRoom is a coordinate-aware room carrying the scene_archetype seam
`typeclasses/rooms.py` SHALL define `GridRoom`, subclassing `SceneArchetypeMixin` (this change's
`scene-archetype-mixin` capability) and `evennia.contrib.grid.xyzgrid.xyzroom.XYZRoom`, inheriting a
persistent `scene_archetype: str | None` attribute defaulting to `None` from `SceneArchetypeMixin`
rather than declaring it directly on `GridRoom` itself. This value SHALL NOT be validated against any
registry, since no `SceneArchetype` registry exists yet (design doc D10, change 22).

#### Scenario: GridRoom inherits full xyzgrid coordinate behavior
- **WHEN** a `GridRoom` is created via `GridRoom.create(key, xyz=(x, y, z))`
- **THEN** its `.xyz` property returns `(x, y, z)`, identically to a plain `XYZRoom`

#### Scenario: scene_archetype defaults to None and is not validated
- **WHEN** a new `GridRoom` is created with no `scene_archetype` supplied
- **THEN** `room.scene_archetype` is `None`, and setting it to an arbitrary string (e.g.
  `"tavern_interior"`) succeeds with no lookup against any registry, since none exists in this change

#### Scenario: scene_archetype persists across a reload
- **WHEN** `room.scene_archetype` is set and the room object is re-fetched from the database
- **THEN** the re-fetched room's `scene_archetype` still holds the previously set value

#### Scenario: GridRoom shares its scene_archetype seam with SceneArchetypeMixin, not a private declaration
- **WHEN** `GridRoom`'s method resolution order is inspected after this change lands
- **THEN** `SceneArchetypeMixin` appears in it, and `GridRoom` itself declares no `scene_archetype`
  class attribute of its own (the attribute resolves via inheritance) — the same
  `SceneArchetypeMixin` also appears in `TerrainRoom.__mro__` (the `scene-archetype-mixin` and
  `wilderness-map-provider` capabilities), confirming both room types share one attribute contract
  rather than two independently-declared, potentially-drifting seams
