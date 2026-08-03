## MODIFIED Requirements

### Requirement: MovementCostMixin charges via at_post_traverse, not at_traverse's return value
`typeclasses/exits.py` SHALL define `MovementCostMixin`, a plain mixin carrying a class attribute
`movement_cost_key: str` (default `"move"`) and overriding `at_post_traverse(traversing_object,
source_location, **kwargs)` to call `super().at_post_traverse(...)` followed by
`charge_movement(traversing_object, self.movement_cost_key)` and then
`world.rules.map_knowledge.record_arrival(traversing_object)`. Recording map knowledge happens only
after the movement transaction has already succeeded, because this hook fires exclusively from the
stock `DefaultExit.at_traverse` success branch — the same structural guarantee that already makes the
charge correct. It SHALL NOT override `at_traverse` or inspect any return value from it. Recording map
knowledge SHALL NOT change the movement-charge behavior in any way.

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
