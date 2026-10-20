## Purpose

Define the coordinate-aware room typeclasses for the grid layer: `GridRoom` carrying the
`scene_archetype` seam, `AnchorRoom` carrying the `anchor_key` seam, and the explicit decision not to
forward-declare `InstanceRoom`. As of `map-wilderness`, `GridRoom` inherits its `scene_archetype`
seam from the shared `SceneArchetypeMixin` (`scene-archetype-mixin` capability) rather than declaring
it directly.

## Requirements

### Requirement: GridRoom is a coordinate-aware room carrying the scene_archetype seam
`typeclasses/rooms.py` SHALL define `GridRoom`, subclassing `SceneArchetypeMixin` (the
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

### Requirement: AnchorRoom is a GridRoom carrying the anchor_key seam
`typeclasses/rooms.py` SHALL define `AnchorRoom`, subclassing `GridRoom`, adding a persistent
`anchor_key: str | None` attribute defaulting to `None`. Every `AnchorRoom` spawned by this change
SHALL have an `anchor_key` that resolves against `world/lore/anchors.py::ANCHOR_REGISTRY`, verified by
a test — not enforced as a hard constraint by the typeclass itself.

#### Scenario: AnchorRoom inherits GridRoom's coordinate and scene_archetype behavior
- **WHEN** an `AnchorRoom` is created
- **THEN** it exposes `.xyz` and `.scene_archetype` identically to a `GridRoom`

#### Scenario: The sample city's AnchorRoom resolves against ANCHOR_REGISTRY
- **WHEN** the `capital_altoria` sample city's spawned `AnchorRoom` is inspected after `sync_grid()`
  runs
- **THEN** `room.anchor_key == "capital_altoria"`, and that key exists in `ANCHOR_REGISTRY`

#### Scenario: The typeclass itself does not enforce anchor_key validity
- **WHEN** an `AnchorRoom` is created directly with an `anchor_key` that does not exist in
  `ANCHOR_REGISTRY`
- **THEN** creation succeeds without raising — validation is a test-level and `sync_grid()`-level
  concern, not a typeclass-level constraint

### Requirement: The stock Room typeclass is unmodified
`typeclasses/rooms.py`'s existing `Room(ObjectParent, DefaultRoom)` class SHALL remain unchanged and
continue to be usable for non-grid rooms (for example, Limbo).

#### Scenario: Room is unaffected by this change
- **WHEN** `typeclasses/rooms.py::Room` is inspected after this change lands
- **THEN** its class body is unchanged from before this change, and it is neither `GridRoom` nor
  `AnchorRoom` nor a subclass of either

### Requirement: InstanceRoom is not forward-declared by this change
`typeclasses/rooms.py` SHALL NOT contain any class, stub, or placeholder named `InstanceRoom` or
otherwise reserved for change 14 (`map-instance`)'s exclusive use.

#### Scenario: No InstanceRoom symbol exists after this change
- **WHEN** `typeclasses/rooms.py` is inspected after this change lands
- **THEN** it defines no class named `InstanceRoom`, and no other class or comment reserves that name
  for a future stub — change 14 adds it fresh, with no seam from this change to build on beyond
  `GridRoom` itself

### Requirement: Grid rooms disable automatic text maps by default without disabling navigation

Grid-layer rooms, including anchor rooms, SHALL default to disabled automatic ASCII minimaps during ordinary room look on every client. The default SHALL apply to new maps using the project grid-room typeclasses without requiring a per-map display option. Explicit developer rendering overrides SHALL retain their existing precedence. Disabling automatic text-map display SHALL NOT change room coordinates, map connectivity, shortest-path results or ordinary path-following movement.

#### Scenario: A loaded grid map inherits the disabled text-map default

- **GIVEN** a loaded connected grid map whose options contain valid visual-range settings and no explicit text-map display override
- **WHEN** a player looks at a plain grid room or an anchor room through ordinary room appearance
- **THEN** no automatic ASCII-map message is emitted to any attached text or browser session
- **AND** the room still reports its original coordinates and ordinary appearance

#### Scenario: A new map requires no display configuration

- **GIVEN** a newly authored loaded map using the existing project grid and anchor room types with no display override
- **WHEN** a player looks at either room type
- **THEN** automatic ASCII-map output is disabled without adding a display entry to that map's options

#### Scenario: Route reporting remains available without movement

- **GIVEN** a synthetic connected map with an independently known two-step route and automatic text-map display disabled
- **WHEN** the player invokes `path <destination>`
- **THEN** the reported route contains those same two directions in order
- **AND** the player's location is unchanged

#### Scenario: Localized and English goto still follow the route

- **GIVEN** the same two-step route with traversable exits and automatic text-map display disabled
- **WHEN** the player invokes `前往 <destination>` or its `goto` alias and the scheduled steps complete
- **THEN** the player reaches the same destination by those exits under the existing movement-cost rules
- **AND** the automatic room appearances along the route emit no ASCII minimap message
