# Spec Delta

## MODIFIED Requirements

### Requirement: WildernessGateExit moves a traversing object from a grid room into the wilderness
`typeclasses.exits.py::WildernessGateExit`, an ordinary `Exit`, SHALL fully override `at_traverse`
to call `evennia.contrib.grid.wilderness.wilderness.enter_wilderness(traversing_object,
coordinates=WILDERNESS_ENTRY_REGISTRY[<its anchor_key>].approach_cell(<its gate>),
name=WILDERNESS_NAME)` instead of moving to a fixed `destination`, where `<its anchor_key>` is
read from `self.db.anchor_key` and `<its gate>` is the registered gate whose `return_direction`
equals `self.db.gate_direction`.

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
  plus the resolved physical traversal duration

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

#### Scenario: Gate attributes are provisioned at creation
- **WHEN** gate exits are created
- **THEN** `self.db.anchor_key` and `self.db.gate_direction` are both attributes this change's
  `sync_wilderness()` (the `wilderness-gateway` capability's own provisioning requirement
  below) SHALL set at creation time

#### Scenario: Arrival cell formula per anchor kind
- **WHEN** the arrival cell is computed for a traversal
- **THEN** for a footprint anchor it is the exterior approach cell (never a footprint cell), and
  for a point-shape anchor `approach_cell` is the anchor cell itself, so the same formula lands
  the traveler on the entry cell

#### Scenario: Pre-move veto honors the game-wide convention
- **WHEN** a traversal is attempted
- **THEN** the exit calls the traversing object's `at_pre_move(None)` hook before attempting to
  move and aborts with no state change if it returns falsy, matching the veto convention every
  other exit in the game (including the stock `WildernessExit`) honors

#### Scenario: Successful traversal completes through the shared helper
- **WHEN** a traversal succeeds
- **THEN** the exit sends departure/arrival room announcements, calls `at_post_move(None)` on
  the traversing object, and completes through the shared movement-completion helper
  `typeclasses.exits.after_successful_movement(traversing_object, source_location,
  cost_key="wilderness_move",
  wilderness_coordinates=WILDERNESS_ENTRY_REGISTRY[<its anchor_key>].approach_cell(<its gate>),
  wilderness_name=WILDERNESS_NAME)`

#### Scenario: Shared completion preserves the observable charge
- **WHEN** `after_successful_movement` completes the traversal
- **THEN** it — not the exit — calls `world.rules.movement.charge_movement(traversing_object,
  cost_key)` (the `movement-cost-charging` capability) and
  `world.rules.map_knowledge.record_arrival(traversing_object)` (the `map-knowledge`
  capability), rather than calling `world.rules.clock.get_world_clock().advance()` directly
- **AND** the observable cost, success-only condition, and `AdvanceSource.COMMAND` source are
  unchanged; only the call sites are now the shared functions every movement lineage uses
- **AND** the arrival recording SHALL NOT alter the charge

### Requirement: Every successful WildernessReturnExit traversal advances the clock, not only the registered return branch
Every successful traversal through `WildernessReturnExit` — both the special-cased branch that routes
back to a grid room, and the ordinary `super().at_traverse()` fallback that governs every other
coordinate and direction — SHALL complete through the shared movement-completion helper
`typeclasses.exits.after_successful_movement(...)` with `cost_key="wilderness_move"`. No
successful step through this exit SHALL be free, and every successful step SHALL record its
destination node.

#### Scenario: Traversing south from the registered entry coordinate advances the clock and records the grid node
- **WHEN** a character successfully traverses the `"south"` exit at a registered entry coordinate
- **THEN** `get_world_clock().tick` after the traversal equals its value before the traversal plus
  the resolved physical traversal duration, and the character's map-knowledge record
  contains the returned grid room's `grid:` node

#### Scenario: An ordinary intermediate step advances the clock and records the wilderness node
- **WHEN** a character at a coordinate that is not any `WILDERNESS_ENTRY_REGISTRY` entry's
  `wilderness_xy` successfully traverses any directional exit (an ordinary wilderness step, taking
  neither special-cased branch)
- **THEN** `get_world_clock().tick` after the traversal equals its value before the traversal plus
  the resolved physical traversal duration, and the character's map-knowledge record
  contains the destination's `wild:` node

#### Scenario: An N-step round trip advances the clock by exactly N times wilderness_move
- **WHEN** a party completes an N-edge round trip
- **THEN** the clock advances by the sum of all individually resolved edge durations, including diagonal and approach distances, subject to the existing flight waiver; arrivals record actual nodes.

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

#### Scenario: The helper performs both side effects on both branches
- **WHEN** either branch completes successfully through the shared helper
- **THEN** the helper calls `world.rules.movement.charge_movement(traversing_object, cost_key)`
  (the `movement-cost-charging` capability) and
  `world.rules.map_knowledge.record_arrival(traversing_object)` (the `map-knowledge` capability)
  on both branches
- **AND** neither branch nor helper calls `world.rules.clock.get_world_clock().advance()`
  directly

#### Scenario: An unsuccessful traversal charges and records nothing
- **WHEN** a traversal is unsuccessful (the underlying
  `at_traverse_coordinates`/`at_pre_move` check fails, per the stock `WildernessExit`'s own
  logic)
- **THEN** it SHALL NOT advance the clock and SHALL NOT record an observation

#### Scenario: Background — the both-branches fix closes a free-step defect
- **WHEN** the authored eight-edge round trip succeeds
- **THEN** its cost equals the sum of its eight resolved physical edge durations and every actual arrival is recorded once, retaining the existing flight waiver.



### Requirement: wilderness_move is a new, distinct clock cost, not a reuse of the grid's move constant
The wilderness traversal context SHALL remain distinct for the existing flight waiver. Physical outdoor edge distance and sustainable speed SHALL determine duration; no fixed wilderness seconds authority SHALL remain. Non-distance connectors SHALL use explicit authored durations.

#### Scenario: wilderness_move is present and distinct from move
- **WHEN** `world/rules/rulebook/clock.yaml` is inspected after this change lands
- **THEN** both entries are valid authored durations and wilderness traversal uses wilderness_move while grid traversal uses move

#### Scenario: Grid traversal is unaffected
- **WHEN** a character traverses an intra-city `CostedXYZExit` created by change 12's `sync_grid()`
  with this change's `("*", "*", "*")` wildcard prototype override
- **THEN** `get_world_clock().tick` increases by exactly the resolved physical edge duration, and
  no grid-traversal code reads the wilderness travel context ;  grid traversal is unaffected by the wilderness
  cost, charging the ordinary `move` cost instead

#### Scenario: Amended 2026-08-01 change map-movement-clock background
- **WHEN** the previous wording's claim that intra-city grid traversal "remains unwired to the
  clock" is re-read
- **THEN** that statement is false, since `map-movement-clock` wires every intra-city link to
  charge the authored non-distance connector duration or resolved outdoor edge duration through `CostedXYZExit` (the `sample-city-altoria`
  capability)
- **AND** the distinctness claim that is this requirement's real subject is unchanged:
  wilderness steps pay the wilderness travel context, grid steps pay `move`, and the two lineages never
  read each other's constant; the amended scenario above asserts exactly that
