## MODIFIED Requirements

### Requirement: MovementCostMixin charges via at_post_traverse, not at_traverse's return value

`typeclasses/exits.py` SHALL define `MovementCostMixin`, a plain mixin carrying a class attribute
`movement_cost_key: str` (default `"move"`) and overriding `at_post_traverse(traversing_object,
source_location, **kwargs)` to call `super().at_post_traverse(...)` followed by
`after_successful_movement(traversing_object, source_location, cost_key=self.movement_cost_key,
destination=traversing_object.location)` — the shared movement-completion helper (the
onboarding-skip coverage change's shared boundary) — which SHALL call
`world.rules.movement.charge_movement(traversing_object, cost_key)` and then
`world.rules.map_knowledge.record_arrival(traversing_object)`. Recording map knowledge happens only
after the movement transaction has already succeeded, because this hook fires exclusively from the
stock `DefaultExit.at_traverse` success branch — the same structural guarantee that already makes the
charge correct. The mixin SHALL additionally override `at_traverse(traversing_object,
target_location, **kwargs)` only to open the movement-settlement boundary (the
movement-settlement-atomicity capability): it SHALL delegate the traversal itself to
`super().at_traverse(...)` inside that boundary and SHALL NOT inspect or reinterpret any return value
from it — `at_traverse`'s return value remains `None` in both branches, and success detection stays
with `at_post_traverse` and the callers' location checks. Recording map knowledge SHALL NOT change
the movement-charge behavior in any way.

#### Scenario: A successful traversal through a MovementCostMixin exit charges exactly once and records arrival
- **WHEN** a `PlayerCharacter` successfully traverses an exit whose class includes
  `MovementCostMixin`
- **THEN** `get_world_clock().tick` increases by exactly one `CLOCK_YAML["command_defaults"][
  movement_cost_key]`, the traversing object's location is the exit's destination, and the traversing
  character's map-knowledge record contains the destination's canonical node ID

#### Scenario: A locked exit never charges and never records
- **WHEN** an exit whose class includes `MovementCostMixin` has a `traverse` lock that denies the
  traversing object
- **THEN** the traversal command does not call `at_traverse` at all (the access check runs first, per
  Evennia's own `ExitCommand.func`), the traversing object's location is unchanged,
  `get_world_clock().tick` is unchanged, and no map-knowledge observation is recorded

#### Scenario: A vetoed at_pre_move never charges and never records
- **WHEN** the traversing object's `at_pre_move` returns a falsy value during an attempted traversal
  through a `MovementCostMixin` exit
- **THEN** `move_to()` returns `False`, `at_post_traverse` is never called, the traversing object's
  location is unchanged, `get_world_clock().tick` is unchanged, and no map-knowledge observation is
  recorded

#### Scenario: A teleport-style move_to never records arrival
- **WHEN** `traversing_object.move_to(destination, move_type="teleport")` is called directly, with no
  `Exit` involved
- **THEN** `get_world_clock().tick` is unchanged and no map-knowledge observation is recorded, even
  though the move itself succeeds

#### Scenario: A quiet relocation (instance reclamation style) never records arrival
- **WHEN** `traversing_object.move_to(destination, quiet=True)` is called directly (the exact shape
  change 14's `_relocate_to_default_home()` uses)
- **THEN** `get_world_clock().tick` is unchanged and no map-knowledge observation is recorded, even
  though `at_post_move` still fires on the moved object

#### Scenario: The MovementCostMixin delegates to the shared completion helper
- **WHEN** `typeclasses/exits.py::MovementCostMixin.at_post_traverse` is inspected
- **THEN** it calls `after_successful_movement(...)` with `cost_key=self.movement_cost_key`, the
  shared helper (not the mixin) calls `world.rules.movement.charge_movement(traversing_object,
  cost_key)` and `world.rules.map_knowledge.record_arrival(traversing_object)`, and neither the mixin
  nor the helper calls `world.rules.clock.get_world_clock().advance()` directly

#### Scenario: The MovementCostMixin at_traverse opens the settlement boundary and delegates the traversal
- **WHEN** `typeclasses/exits.py::MovementCostMixin.at_traverse` is inspected
- **THEN** it invokes the movement-settlement boundary (the movement-settlement-atomicity entry point)
  around a call to `super().at_traverse(...)`, contains no inline
  `world.rules.clock.get_world_clock().advance()` call, and its `at_post_traverse` is unchanged
