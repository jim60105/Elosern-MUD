## Purpose

Define the single, shared movement-cost charging entry point: `charge_movement()` resolves a cost from
`CLOCK_YAML["command_defaults"]` and advances the world clock only for a `PlayerCharacter`, and every
non-teleport exit lineage charges successful player movement through it via
`MovementCostMixin.at_post_traverse` — never through a bespoke, inline `advance()` call.

## Requirements


### Requirement: charge_movement() is the single, shared movement-cost charging function
`world/rules/movement.py` SHALL provide `charge_movement(traversing_object, cost_key: str) -> None`,
resolving the cost from `CLOCK_YAML["command_defaults"][cost_key]` and calling
`world.rules.clock.get_world_clock().advance(cost, AdvanceSource.COMMAND, [traversing_object])` when
`traversing_object` is a `typeclasses.characters.PlayerCharacter`, and doing nothing otherwise. No
other function or inline call site in this project SHALL call
`world.rules.clock.get_world_clock().advance()` for a movement event; every exit lineage that charges
movement SHALL call `charge_movement()`.

#### Scenario: charge_movement advances the clock by the resolved cost for a PlayerCharacter
- **WHEN** `charge_movement(player_character, "move")` is called
- **THEN** `get_world_clock().tick` after the call equals its value before the call plus
  `CLOCK_YAML["command_defaults"]["move"]`

#### Scenario: charge_movement is a no-op for a non-PlayerCharacter traverser
- **WHEN** `charge_movement(npc, "move")` is called for an `NPC`-typeclassed (not `PlayerCharacter`)
  entity
- **THEN** `get_world_clock().tick` is unchanged

#### Scenario: charge_movement always uses AdvanceSource.COMMAND
- **WHEN** `charge_movement()` is called with any registered `cost_key`
- **THEN** the underlying `WorldClock.advance()` call receives `AdvanceSource.COMMAND`

### Requirement: MovementCostMixin charges via at_post_traverse, not at_traverse's return value
`typeclasses/exits.py` SHALL define `MovementCostMixin`, a plain mixin carrying a class attribute
`movement_cost_key: str` (default `"move"`) and overriding `at_post_traverse(traversing_object,
source_location, **kwargs)` to call `super().at_post_traverse(...)` followed by
`charge_movement(traversing_object, self.movement_cost_key)`. It SHALL NOT override `at_traverse` or
inspect any return value from it.

#### Scenario: A successful traversal through a MovementCostMixin exit charges exactly once
- **WHEN** a `PlayerCharacter` successfully traverses an exit whose class includes
  `MovementCostMixin`
- **THEN** `get_world_clock().tick` increases by exactly one `CLOCK_YAML["command_defaults"][
  movement_cost_key]`, and the traversing object's location is the exit's destination

#### Scenario: A locked exit never charges
- **WHEN** an exit whose class includes `MovementCostMixin` has a `traverse` lock that denies the
  traversing object
- **THEN** the traversal command does not call `at_traverse` at all (the access check runs first, per
  Evennia's own `ExitCommand.func`), the traversing object's location is unchanged, and
  `get_world_clock().tick` is unchanged

#### Scenario: A vetoed at_pre_move never charges
- **WHEN** the traversing object's `at_pre_move` returns a falsy value during an attempted traversal
  through a `MovementCostMixin` exit
- **THEN** `move_to()` returns `False`, `at_post_traverse` is never called, the traversing object's
  location is unchanged, and `get_world_clock().tick` is unchanged

### Requirement: typeclasses.exits.Exit and CostedXYZExit both carry MovementCostMixin with
movement_cost_key "move"
`typeclasses/exits.py::Exit(MovementCostMixin, ObjectParent, DefaultExit)` SHALL include
`MovementCostMixin` in its base classes, with `movement_cost_key = "move"` (the mixin's default,
inherited unmodified). `typeclasses/exits.py` SHALL also define `CostedXYZExit(MovementCostMixin,
evennia.contrib.grid.xyzgrid.xyzroom.XYZExit)`, likewise with `movement_cost_key = "move"`, preserving
every other behavior `XYZExit` already provides (coordinate tags, `.xyz`/`.xyz_destination`
properties, `.create()`).

#### Scenario: Exit charges move on successful traversal
- **WHEN** a `PlayerCharacter` successfully traverses a plain `typeclasses.exits.Exit` instance
- **THEN** `get_world_clock().tick` increases by exactly `CLOCK_YAML["command_defaults"]["move"]`

#### Scenario: CostedXYZExit charges move and preserves XYZExit's own coordinate behavior
- **WHEN** a `CostedXYZExit` is created via `CostedXYZExit.create(key=..., location=..., destination=
  ...)` and a `PlayerCharacter` successfully traverses it
- **THEN** `isinstance(exit_obj, evennia.contrib.grid.xyzgrid.xyzroom.XYZExit)` is `True`,
  `get_world_clock().tick` increases by exactly `CLOCK_YAML["command_defaults"]["move"]`, and the
  traversing object's location is the exit's destination

#### Scenario: An instance-room exit pair charges move with no code change beyond Exit's own retrofit
- **WHEN** an origin/return `Exit` pair is created with `typeclasses.exits.Exit.create()` (the exact
  call shape `world/maps/instance.py::spawn_instance_room()`, change 14, uses) and a
  `PlayerCharacter` successfully traverses either exit of the pair
- **THEN** `get_world_clock().tick` increases by exactly `CLOCK_YAML["command_defaults"]["move"]` per
  successful traversal, with no edit to change 14's own `spawn_instance_room()` required

### Requirement: Movement never charges through a teleport, spawn, or non-exit relocation
No call to `DefaultObject.move_to()` that is not routed through an `Exit`'s own `at_traverse` (for
example, a `move_type="teleport"` call, or a raw `move_to(quiet=True)` relocation such as change 14's
`_relocate_to_default_home()`) SHALL cause `charge_movement()` to be invoked, because
`at_post_traverse` — the hook `MovementCostMixin` relies on — is only ever called from within
`DefaultExit.at_traverse`'s own success branch.

#### Scenario: A teleport-style move_to call does not advance the clock
- **WHEN** `traversing_object.move_to(destination, move_type="teleport")` is called directly, with no
  `Exit` involved
- **THEN** `get_world_clock().tick` is unchanged, even though the move itself succeeds

#### Scenario: A quiet relocation (instance-room reclamation style) does not advance the clock
- **WHEN** `traversing_object.move_to(destination, quiet=True)` is called directly (the exact shape
  change 14's `_relocate_to_default_home()` uses)
- **THEN** `get_world_clock().tick` is unchanged, even though `at_post_move` still fires on the moved
  object (verified: `quiet=True` alone does not suppress `move_hooks`)

### Requirement: Movement charges only for a PlayerCharacter traverser, never for an autonomous NPC
or monster
`charge_movement()` SHALL check `isinstance(traversing_object, typeclasses.characters.
PlayerCharacter)` and SHALL NOT advance `WorldClock` for any other traverser, matching design doc D4
("the world advances only on player action").

#### Scenario: An NPC traversing a MovementCostMixin exit does not advance the clock
- **WHEN** an `NPC`-typeclassed object successfully traverses an exit whose class includes
  `MovementCostMixin`
- **THEN** the traversal itself succeeds (the traverser's location changes), but
  `get_world_clock().tick` is unchanged