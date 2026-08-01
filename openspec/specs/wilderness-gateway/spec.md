## Purpose

The concrete, bidirectional connection between the grid layer and the wilderness/Virtual layer: the
`WILDERNESS_ENTRY_REGISTRY` linking a grid-placed anchor to one wilderness coordinate, the two exit
typeclasses (`WildernessGateExit` for grid→wilderness, `WildernessReturnExit` for wilderness→grid and
ordinary wilderness steps), the `wilderness_move` clock cost that every successful wilderness step
charges, and the idempotent `sync_wilderness()` provisioning wired into server startup.

## Requirements


### Requirement: WILDERNESS_ENTRY_REGISTRY links a grid-placed anchor to one wilderness coordinate
`world/lore/wilderness_entry.py` SHALL define a frozen `WildernessEntryPoint` dataclass (`anchor_key:
str`, `wilderness_xy: tuple[int, int]`) and a module-level `WILDERNESS_ENTRY_REGISTRY: dict[str,
WildernessEntryPoint]`. Every entry's `anchor_key` SHALL exist as a key in change 12's
`ANCHOR_PLACEMENT_REGISTRY`. The registry SHALL NOT be required to contain an entry for every
`ANCHOR_PLACEMENT_REGISTRY` key. This change SHALL populate exactly one entry, keyed
`"capital_altoria"`, with `wilderness_xy` inside `ElosernWildernessMapProvider`'s valid coordinate
bounds.

#### Scenario: The registry has exactly one entry after this change
- **WHEN** `WILDERNESS_ENTRY_REGISTRY` is inspected
- **THEN** it contains exactly one entry, keyed `"capital_altoria"`, and no test in this change's own
  suite asserts that any other `ANCHOR_PLACEMENT_REGISTRY` key must also appear

#### Scenario: Every entry's anchor_key resolves against ANCHOR_PLACEMENT_REGISTRY
- **WHEN** every entry in `WILDERNESS_ENTRY_REGISTRY` is inspected
- **THEN** each entry's `anchor_key` exists as a key in `world.lore.anchor_placement.
  ANCHOR_PLACEMENT_REGISTRY`

#### Scenario: WILDERNESS_ENTRY_REGISTRY is mirrored into LoreRecord Scripts idempotently
- **WHEN** `sync_all()` runs, and then runs a second time
- **THEN** a `LoreRecord` Script keyed `"lore:wilderness_entries:capital_altoria"` exists after both
  calls, and no duplicate exists after the second

### Requirement: WildernessGateExit moves a traversing object from a grid room into the wilderness
`typeclasses/exits.py::WildernessGateExit`, an ordinary `Exit`, SHALL fully override `at_traverse` to
call `evennia.contrib.grid.wilderness.wilderness.enter_wilderness(traversing_object, coordinates=
WILDERNESS_ENTRY_REGISTRY[<its anchor_key>].wilderness_xy, name=WILDERNESS_NAME)` instead of moving to
a fixed `destination`, where `<its anchor_key>` is read from `self.db.anchor_key`, an attribute this
change's `sync_wilderness()` (the `wilderness-gateway` capability's own provisioning requirement below)
SHALL set at creation time. Before attempting to move, it SHALL call the traversing object's
`at_pre_move(None)` hook and abort with no state change if it returns falsy, matching the veto
convention every other exit in the game (including the stock `WildernessExit`) honors. On a successful
traversal, it SHALL send departure/arrival room announcements, call `at_post_move(None)` on the
traversing object, and call `world.rules.movement.charge_movement(traversing_object,
"wilderness_move")` (the `movement-cost-charging` capability), rather than calling
`world.rules.clock.get_world_clock().advance()` directly — the observable cost, success-only
condition, and `AdvanceSource.COMMAND` source are unchanged; only the call site is now the shared
function every exit lineage uses.

#### Scenario: Traversing the gate exit places the object in the wilderness at the registered coordinate
- **WHEN** a character traverses a `WildernessGateExit` configured for `"capital_altoria"`
- **THEN** the character's new location is a `TerrainRoom` whose `.coordinates` equals
  `WILDERNESS_ENTRY_REGISTRY["capital_altoria"].wilderness_xy`

#### Scenario: A successful traversal advances the world clock by the wilderness_move cost
- **WHEN** a character successfully traverses a `WildernessGateExit`
- **THEN** `get_world_clock().tick` after the traversal equals its value before the traversal plus
  `CLOCK_YAML["command_defaults"]["wilderness_move"]`

#### Scenario: An unsuccessful traversal does not advance the clock
- **WHEN** `enter_wilderness()` returns `False` (for example, the registered coordinate is somehow
  invalid)
- **THEN** `get_world_clock().tick` is unchanged by the attempted traversal

#### Scenario: A vetoed at_pre_move blocks the traversal entirely
- **WHEN** the traversing object's `at_pre_move(None)` returns a falsy value
- **THEN** `WildernessGateExit.at_traverse` returns `False`, `enter_wilderness()` is never called, the
  traversing object's location is unchanged, and `get_world_clock().tick` is unchanged

#### Scenario: The clock charge goes through the shared charge_movement function
- **WHEN** `typeclasses/exits.py::WildernessGateExit.at_traverse` is inspected
- **THEN** its successful branch calls `world.rules.movement.charge_movement(traversing_object,
  "wilderness_move")`, not `world.rules.clock.get_world_clock().advance()` directly

### Requirement: WildernessReturnExit routes exactly one registered coordinate-and-direction pair back to the grid
`typeclasses/exits.py::WildernessReturnExit`, subclassing
`evennia.contrib.grid.wilderness.wilderness.WildernessExit`, SHALL be
`ElosernWildernessMapProvider.exit_typeclass`. For a traversing object currently at a coordinate
matching some `WILDERNESS_ENTRY_REGISTRY` entry's `wilderness_xy`, on the direction that leads back
toward the grid (`"south"`), it SHALL move the traversing object to that entry's anchor's grid room
instead of another wilderness coordinate. For every other coordinate, or every other direction at a
registered coordinate, its **routing** (destination room, coordinate movement) SHALL behave identically
to the stock `WildernessExit`. This requirement governs routing only — every successful traversal's
**clock cost** is governed by the separate "Every successful WildernessReturnExit traversal advances
the clock, not only the registered return branch" requirement below, which applies uniformly
regardless of which routing branch was taken.

#### Scenario: Traversing south from the registered entry coordinate returns to the grid room
- **WHEN** a character at `WILDERNESS_ENTRY_REGISTRY["capital_altoria"].wilderness_xy` traverses the
  `"south"` exit
- **THEN** the character's new location is the `capital_altoria` North Gate `GridRoom` object (the
  same object instance that existed before the character first entered the wilderness through it)

#### Scenario: Every other coordinate and direction routes like a stock WildernessExit
- **WHEN** a character traverses any directional exit at a coordinate that is not any
  `WILDERNESS_ENTRY_REGISTRY` entry's `wilderness_xy`, or traverses a direction other than `"south"`
  at a registered coordinate
- **THEN** the traversal's destination behaves identically to `evennia.contrib.grid.wilderness.
  wilderness.WildernessExit.at_traverse` (ordinary coordinate movement within the wilderness)

### Requirement: Every successful WildernessReturnExit traversal advances the clock, not only the registered return branch
Every successful traversal through `WildernessReturnExit` — both the special-cased branch that routes
back to a grid room, and the ordinary `super().at_traverse()` fallback that governs every other
coordinate and direction — SHALL call `world.rules.movement.charge_movement(traversing_object,
"wilderness_move")` (the `movement-cost-charging` capability), rather than calling
`world.rules.clock.get_world_clock().advance()` directly, before returning. No successful step through
this exit SHALL be free. An unsuccessful traversal (the underlying `at_traverse_coordinates`/
`at_pre_move` check fails, per the stock `WildernessExit`'s own logic) SHALL NOT advance the clock.

This is the concrete fix for a defect a rubber-duck review found in an earlier draft of this
capability: `ElosernWildernessMapProvider.exit_typeclass = WildernessReturnExit` installs this class on
all eight directional exits at every wilderness coordinate (the `wilderness-map-provider` capability),
so if only the registered return branch advanced the clock, every intermediate step of a continent
crossing would cost nothing — contradicting the whole point of wiring wilderness movement to
`WorldClock` at all. Folding both call sites onto `charge_movement()` (rather than each duplicating
`get_world_clock().advance()` independently) is this change's own contribution: the same fix, now
expressed once instead of twice, and consistent with how every other movement lineage in the project
charges (`movement-cost-charging` capability).

#### Scenario: Traversing south from the registered entry coordinate advances the clock
- **WHEN** a character successfully traverses the `"south"` exit at a registered entry coordinate
- **THEN** `get_world_clock().tick` after the traversal equals its value before the traversal plus
  `CLOCK_YAML["command_defaults"]["wilderness_move"]`

#### Scenario: An ordinary intermediate step advances the clock by exactly one wilderness_move
- **WHEN** a character at a coordinate that is not any `WILDERNESS_ENTRY_REGISTRY` entry's
  `wilderness_xy` successfully traverses any directional exit (an ordinary wilderness step, taking
  neither special-cased branch)
- **THEN** `get_world_clock().tick` after the traversal equals its value before the traversal plus
  `CLOCK_YAML["command_defaults"]["wilderness_move"]`

#### Scenario: An N-step round trip advances the clock by exactly N times wilderness_move
- **WHEN** a character enters the wilderness through `WildernessGateExit`, takes three consecutive
  intermediate steps in one direction, three consecutive steps back in the opposite direction, and
  finally traverses `"south"` from the registered entry coordinate back to the grid — eight successful
  traversals in total, only two of which (the entry and the final return) take a special-cased
  routing branch
- **THEN** `get_world_clock().tick` after the whole round trip equals its value before the trip plus
  exactly `8 * CLOCK_YAML["command_defaults"]["wilderness_move"]` — proving no step, including the six
  ordinary intermediate ones, is free

#### Scenario: A failed traversal does not advance the clock
- **WHEN** a traversal through `WildernessReturnExit` fails its underlying validity/veto check (for
  example, the target coordinate is invalid, or the traverser's `at_pre_move` vetoes)
- **THEN** `get_world_clock().tick` is unchanged

#### Scenario: A return to a missing grid room does not advance the clock
- **WHEN** the special-cased return branch resolves no grid room for the entry's anchor (e.g. the gate
  exit `sync_wilderness()` provisioned has been deleted, so `_grid_room_for_anchor` returns `None`) or
  the resulting `move_to()` fails its pre-move veto
- **THEN** `WildernessReturnExit.at_traverse` returns `False`, the traverser's location is unchanged,
  and `get_world_clock().tick` is unchanged — a failed return is never reported as a successful,
  clock-charged step

#### Scenario: Both branches charge through the shared charge_movement function
- **WHEN** `typeclasses/exits.py::WildernessReturnExit.at_traverse` is inspected
- **THEN** both its special-cased return branch and its `super().at_traverse()` fallback branch call
  `world.rules.movement.charge_movement(traversing_object, "wilderness_move")`, and neither calls
  `world.rules.clock.get_world_clock().advance()` directly

### Requirement: Leaving the wilderness through WildernessReturnExit triggers ordinary cleanup
When a traversing object leaves a `TerrainRoom` through `WildernessReturnExit`'s grid-routing branch,
the wilderness's own per-object bookkeeping (`itemcoordinates` entry removal, room recycling into
`unused_rooms` when no one remains) SHALL fire exactly as it does for an ordinary
`move_to()`-driven departure, with no additional cleanup code in this change.

#### Scenario: The departing object is no longer tracked by the wilderness after returning
- **WHEN** a character returns to the grid via `WildernessReturnExit`
- **THEN** the character no longer appears as a key in the `WildernessScript`'s
  `itemcoordinates` mapping

#### Scenario: A vacated wilderness room is not leaked, and is reused on a later return
- **WHEN** a character who was alone in a `TerrainRoom` returns to the grid via `WildernessReturnExit`
- **THEN** the vacated room is not orphaned: it remains owned by the `WildernessScript` (either
  recycled into `unused_rooms` when the contrib's recycling condition is met, or retained in
  `db.rooms` keyed by its coordinates for an account-character `move_to()`-driven departure, which
  the contrib does not recycle because the departing account is still in the room's contents when
  `_destroy_room` runs), and re-entering the same coordinates later reuses that same room object
  rather than spawning a new one

### Requirement: sync_wilderness() idempotently provisions the wilderness map and the one grid-side gate
`world/maps/bootstrap.py::sync_wilderness()` SHALL call `create_wilderness(name=WILDERNESS_NAME,
mapprovider=ElosernWildernessMapProvider())` and, when the `capital_altoria` North Gate `GridRoom`
exists, SHALL idempotently ensure exactly one `WildernessGateExit` exists there **with its
`db.anchor_key` set to `"capital_altoria"`** — the gate exit is not usable without this attribute
(`WildernessGateExit.at_traverse` reads `self.db.anchor_key` and raises `KeyError` on lookup if it is
unset), so a `sync_wilderness()` that creates the exit without setting it is not a conforming
implementation of this requirement even though the exit object itself exists. When the North Gate
room does not exist, `sync_wilderness()` SHALL log a warning and skip creating the gate exit, and
SHALL NOT raise. `sync_wilderness()` SHALL be distinct in name and module role from change 12's
`sync_grid()`, and SHALL NOT modify `sync_grid()`'s own behavior.

#### Scenario: sync_wilderness creates the wilderness map and the gate exit
- **WHEN** `sync_wilderness()` runs after `sync_grid()` has already created the sample city
- **THEN** a `WildernessScript` keyed `WILDERNESS_NAME` exists, and the North Gate `GridRoom` has
  exactly one `WildernessGateExit` whose `db.anchor_key == "capital_altoria"`

#### Scenario: The created gate exit is immediately usable, not merely present
- **WHEN** a character traverses the `WildernessGateExit` that `sync_wilderness()` created, immediately
  after `sync_wilderness()` returns, with no further setup
- **THEN** the traversal succeeds and does not raise `KeyError` — the concrete regression check for the
  defect this requirement's `db.anchor_key` clause exists to prevent

#### Scenario: Repeated calls create no duplicates
- **WHEN** `sync_wilderness()` is called twice in succession
- **THEN** exactly one `WildernessScript` keyed `WILDERNESS_NAME` exists, and the North Gate room still
  has exactly one `WildernessGateExit`

#### Scenario: A restarted server restores deterministic room descriptions
- **WHEN** a wilderness room that was retained in `WildernessScript.db.rooms` (e.g. a player's current
  or vacated room) loses its non-persistent `ndb.active_desc`/`scene_archetype` across a server
  restart, and `sync_wilderness()` runs again
- **THEN** each room still registered in the script's `db.rooms` has `ndb.active_desc` and
  `scene_archetype` re-computed from its current coordinates via the provider's `at_prepare_room()` —
  the deterministic terrain description survives a restart

#### Scenario: A mis-keyed project gate is healed, a foreign same-key exit is left alone
- **WHEN** the North Gate's `WildernessGateExit` has a wrong `db.anchor_key`, and `sync_wilderness()`
  runs again
- **THEN** the existing `WildernessGateExit`'s `db.anchor_key` is corrected to `"capital_altoria"`
  with no new exit spawned; and if a non-`WildernessGateExit` with the same key exists there, it is
  left in place and no second gate is created atop it

#### Scenario: A missing North Gate degrades gracefully
- **WHEN** `sync_wilderness()` runs against a database where the `capital_altoria` North Gate room
  does not exist
- **THEN** the `WildernessScript` is still created, no exception is raised, and no gate exit is
  created anywhere

#### Scenario: sync_wilderness runs automatically at server start, after sync_grid
- **WHEN** `server/conf/at_server_startstop.py::at_server_start()` is inspected
- **THEN** the call to `sync_wilderness()` appears after the call to `sync_grid()` in source order

### Requirement: wilderness_move is a new, distinct clock cost, not a reuse of the grid's move constant
`world/rules/rulebook/clock.yaml::command_defaults` SHALL include a new key, `wilderness_move: 9000`
(seconds), distinct from the existing `move: 30` entry. No code in this change SHALL read `move` for
wilderness traversal, and no code from change 12 (grid traversal) SHALL be modified to read
`wilderness_move`.

**Amended 2026-08-01 (change `map-movement-clock`):** the previous wording asserted that intra-city
grid traversal "remains unwired to the clock" — a statement `map-movement-clock` makes false, since it
wires every intra-city link to charge `command_defaults.move` through `CostedXYZExit` (the
`sample-city-altoria` capability). The distinctness claim that is this requirement's real subject is
unchanged: wilderness steps pay `wilderness_move`, grid steps pay `move`, and the two lineages never
read each other's constant. The amended scenario below asserts exactly that.

#### Scenario: wilderness_move is present and distinct from move
- **WHEN** `world/rules/rulebook/clock.yaml` is inspected after this change lands
- **THEN** `command_defaults.wilderness_move == 9000` and `command_defaults.move == 30` (unchanged
  from change 11)

#### Scenario: Grid traversal is unaffected
- **WHEN** a character traverses an intra-city `CostedXYZExit` created by change 12's `sync_grid()`
  with this change's `("*", "*", "*")` wildcard prototype override
- **THEN** `get_world_clock().tick` increases by exactly `CLOCK_YAML["command_defaults"]["move"]`, and
  no grid-traversal code reads `wilderness_move` — grid traversal is unaffected by the wilderness
  cost, charging the ordinary `move` cost instead
