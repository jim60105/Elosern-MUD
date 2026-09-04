# Delta: wilderness-gateway

## MODIFIED Requirements

### Requirement: WildernessGateExit moves a traversing object from a grid room into the wilderness
`typeclasses.exits.py::WildernessGateExit`, an ordinary `Exit`, SHALL fully override `at_traverse`
to call `evennia.contrib.grid.wilderness.wilderness.enter_wilderness(traversing_object,
coordinates=WILDERNESS_ENTRY_REGISTRY[<its anchor_key>].approach_cell(<its gate>),
name=WILDERNESS_NAME)` instead of moving to a fixed `destination`, where `<its anchor_key>` is
read from `self.db.anchor_key` and `<its gate>` is the registered gate whose `return_direction`
equals `self.db.gate_direction` — both attributes this change's `sync_wilderness()` (the
`wilderness-gateway` capability's own provisioning requirement below) SHALL set at creation time.
For a footprint anchor the arrival cell is the exterior approach cell (never a footprint cell);
for a point-shape anchor `approach_cell` is the anchor cell itself, so the same formula lands
the traveler on the entry cell. Before attempting to move, it SHALL call the traversing object's
`at_pre_move(None)` hook and abort with no state change if it returns falsy, matching the veto
convention every other exit in the game (including the stock `WildernessExit`) honors. On a
successful traversal, it SHALL send departure/arrival room announcements, call
`at_post_move(None)` on the traversing object, and complete through the shared
movement-completion helper `typeclasses.exits.after_successful_movement(traversing_object,
source_location, cost_key="wilderness_move",
wilderness_coordinates=WILDERNESS_ENTRY_REGISTRY[<its anchor_key>].approach_cell(<its gate>),
wilderness_name=WILDERNESS_NAME)` — the shared movement boundary —
which SHALL call `world.rules.movement.charge_movement(traversing_object, cost_key)` (the
`movement-cost-charging` capability) and `world.rules.map_knowledge.record_arrival(traversing_object)`
(the `map-knowledge` capability), rather than calling
`world.rules.clock.get_world_clock().advance()` directly. The observable cost, success-only
condition, and `AdvanceSource.COMMAND` source are unchanged; only the call sites are now the
shared functions every movement lineage uses. The arrival recording SHALL NOT alter the charge.

#### Scenario: Traversing a gate exit places the object at that gate's approach cell
- **WHEN** a character traverses a `WildernessGateExit` configured for
  `("capital_altoria", gate facing 南門)`
- **THEN** the character's new location is a `TerrainRoom` whose `.coordinates` equals the `"n"`
  gate's `approach_cell` `(60, 97)` (the cell outside the footprint, never a footprint cell), and
  its map-knowledge record contains the corresponding `wild:elosern:<x>:<y>` node

#### Scenario: Traversing the other gate lands at the other gate's approach cell
- **WHEN** a character traverses the `WildernessGateExit` provisioned on the North Gate room
- **THEN** the arrival coordinates equal the `"s"` gate's `approach_cell` `(60, 103)`,
  independent of which gate was used before

#### Scenario: A successful traversal advances the world clock by the wilderness_move cost
- **WHEN** a character successfully traverses a `WildernessGateExit`
- **THEN** `get_world_clock().tick` after the traversal equals its value before the traversal
  plus `CLOCK_YAML["command_defaults"]["wilderness_move"]`

#### Scenario: An unsuccessful traversal does not advance the clock and records nothing
- **WHEN** `enter_wilderness()` returns `False` (for example, the gate's landing cell is somehow
  invalid)
- **THEN** `get_world_clock().tick` is unchanged by the attempted traversal and no map-knowledge
  observation is recorded

#### Scenario: A vetoed at_pre_move blocks the traversal entirely
- **WHEN** the traversing object's `at_pre_move(None)` returns a falsy value
- **THEN** `WildernessGateExit.at_traverse` returns `False`, `enter_wilderness()` is never
  called, the traversing object's location is unchanged, `get_world_clock().tick` is unchanged,
  and no map-knowledge observation is recorded

#### Scenario: The clock charge and arrival recording go through the shared completion helper
- **WHEN** `typeclasses.exits.py::WildernessGateExit.at_traverse` is inspected
- **THEN** its successful branch calls `after_successful_movement(...)` with
  `cost_key="wilderness_move"`, the shared helper (not the exit) calls
  `world.rules.movement.charge_movement(traversing_object, cost_key)` and
  `world.rules.map_knowledge.record_arrival(traversing_object)`, and neither the exit nor the
  helper calls `world.rules.clock.get_world_clock().advance()` directly

### Requirement: Every successful WildernessReturnExit traversal advances the clock, not only the registered return branch
Every successful traversal through `WildernessReturnExit` — both the special-cased branch that routes
back to a grid room, and the ordinary `super().at_traverse()` fallback that governs every other
coordinate and direction — SHALL complete through the shared movement-completion helper
`typeclasses.exits.after_successful_movement(...)` with `cost_key="wilderness_move"`, which SHALL call
`world.rules.movement.charge_movement(traversing_object, cost_key)` (the `movement-cost-charging`
capability) and `world.rules.map_knowledge.record_arrival(traversing_object)` (the `map-knowledge`
capability) on both branches — rather than calling
`world.rules.clock.get_world_clock().advance()` directly. No successful step through this exit SHALL
be free, and every successful step SHALL record its destination node. An unsuccessful traversal (the
underlying `at_traverse_coordinates`/`at_pre_move` check fails, per the stock `WildernessExit`'s own
logic) SHALL NOT advance the clock and SHALL NOT record an observation.

This is the concrete fix for a defect a rubber-duck review found in an earlier draft of this
capability: `ElosernWildernessMapProvider.exit_typeclass = WildernessReturnExit` installs this class on
all eight directional exits at every wilderness coordinate (the `wilderness-map-provider` capability),
so if only the registered return branch advanced the clock, every intermediate step of a continent
crossing would cost nothing — contradicting the whole point of wiring wilderness movement to
`WorldClock` at all. Folding both call sites onto the one shared completion helper (rather than each
duplicating `get_world_clock().advance()` independently) is this change's own contribution: the same
fix, now expressed once instead of twice, and consistent with how every other movement lineage in the
project charges (`movement-cost-charging` capability).

#### Scenario: Traversing south from the registered entry coordinate advances the clock and records the grid node
- **WHEN** a character successfully traverses the `"south"` exit at a registered entry coordinate
- **THEN** `get_world_clock().tick` after the traversal equals its value before the traversal plus
  `CLOCK_YAML["command_defaults"]["wilderness_move"]`, and the character's map-knowledge record
  contains the returned grid room's `grid:` node

#### Scenario: An ordinary intermediate step advances the clock and records the wilderness node
- **WHEN** a character at a coordinate that is not any `WILDERNESS_ENTRY_REGISTRY` entry's
  `wilderness_xy` successfully traverses any directional exit (an ordinary wilderness step, taking
  neither special-cased branch)
- **THEN** `get_world_clock().tick` after the traversal equals its value before the traversal plus
  `CLOCK_YAML["command_defaults"]["wilderness_move"]`, and the character's map-knowledge record
  contains the destination's `wild:` node

#### Scenario: An N-step round trip advances the clock by exactly N times wilderness_move
- **WHEN** a character enters the wilderness through `WildernessGateExit`, takes three consecutive
  intermediate steps in one direction, three consecutive steps back in the opposite direction, and
  finally traverses `"south"` from the registered entry coordinate back to the grid — eight successful
  traversals in total, only two of which (the entry and the final return) take a special-cased
  routing branch
- **THEN** `get_world_clock().tick` after the whole round trip equals its value before the trip plus
  exactly `8 * CLOCK_YAML["command_defaults"]["wilderness_move"]` — proving no step, including the six
  ordinary intermediate ones, is free

#### Scenario: A failed traversal does not advance the clock and records nothing
- **WHEN** a traversal through `WildernessReturnExit` fails its underlying validity/veto check (for
  example, the target coordinate is invalid, or the traverser's `at_pre_move` vetoes)
- **THEN** `get_world_clock().tick` is unchanged and no map-knowledge observation is recorded

#### Scenario: A return to a missing grid room does not advance the clock and records nothing
- **WHEN** the special-cased return branch resolves no grid room for the entry's anchor (e.g. the gate
  exit `sync_wilderness()` provisioned has been deleted, so `_grid_room_for_anchor` returns `None`) or
  the resulting `move_to()` fails its pre-move veto
- **THEN** `WildernessReturnExit.at_traverse` returns `False`, the traverser's location is unchanged,
  `get_world_clock().tick` is unchanged, and no map-knowledge observation is recorded — a failed
  return is never reported as a successful, clock-charged step

#### Scenario: Both branches complete through the shared completion helper
- **WHEN** `typeclasses/exits.py::WildernessReturnExit.at_traverse` is inspected
- **THEN** both its special-cased return branch and its `super().at_traverse()` fallback branch call
  `after_successful_movement(...)` with `cost_key="wilderness_move"`, the shared helper (not the
  exit) calls `world.rules.movement.charge_movement(traversing_object, cost_key)` and
  `world.rules.map_knowledge.record_arrival(traversing_object)`, and neither the exit nor the helper
  calls `world.rules.clock.get_world_clock().advance()` directly
