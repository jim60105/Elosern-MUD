## MODIFIED Requirements

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
