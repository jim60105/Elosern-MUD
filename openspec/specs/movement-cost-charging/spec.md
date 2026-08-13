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
movement SHALL call `charge_movement()`. When `cost_key == "wilderness_move"` and `traversing_object`
owns the `flight` skill (`"flight" in traversing_object.skills.owned_keys()`), `charge_movement()`
SHALL return without advancing the clock — the flight waiver. This waiver applies only to
`"wilderness_move"`; every other `cost_key` charges normally regardless of owned skills.

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

#### Scenario: A flight-owning PlayerCharacter is waived the wilderness_move cost
- **WHEN** `charge_movement(player_character, "wilderness_move")` is called on a `PlayerCharacter`
  owning `flight`
- **THEN** `get_world_clock().tick` is unchanged

#### Scenario: The waiver does not extend to other cost keys
- **WHEN** `charge_movement(player_character, "move")` is called on the same flight-owning
  `PlayerCharacter`
- **THEN** the clock advances by `CLOCK_YAML["command_defaults"]["move"]` exactly as it would for a
  non-flight-owning entity

#### Scenario: A non-flight-owning PlayerCharacter still pays the wilderness_move cost
- **WHEN** `charge_movement(player_character, "wilderness_move")` is called on a `PlayerCharacter` not
  owning `flight`
- **THEN** the clock advances by `CLOCK_YAML["command_defaults"]["wilderness_move"]`

### Requirement: MovementCostMixin charges via at_post_traverse, not at_traverse's return value
`typeclasses/exits.py` SHALL define `MovementCostMixin`, a plain mixin carrying a class attribute
`movement_cost_key: str` (default `"move"`) and overriding `at_post_traverse(traversing_object,
source_location, **kwargs)` to call `super().at_post_traverse(...)` followed by
`after_successful_movement(traversing_object, source_location, cost_key=self.movement_cost_key,
destination=traversing_object.location)` — the shared movement-completion helper (the
onboarding-skip-coverage change's shared boundary) — which SHALL call
`world.rules.movement.charge_movement(traversing_object, cost_key)` and then
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

#### Scenario: The MovementCostMixin delegates to the shared completion helper
- **WHEN** `typeclasses/exits.py::MovementCostMixin.at_post_traverse` is inspected
- **THEN** it calls `after_successful_movement(...)` with `cost_key=self.movement_cost_key`, the
  shared helper (not the mixin) calls `world.rules.movement.charge_movement(traversing_object,
  cost_key)` and `world.rules.map_knowledge.record_arrival(traversing_object)`, and neither the mixin
  nor the helper calls `world.rules.clock.get_world_clock().advance()` directly

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

### Requirement: Flight-required exits pass only for flight/flash_step owners
`typeclasses/exits.py` SHALL support an opt-in `requires_flight: bool` class/instance attribute
(default `False`) on exit typeclasses using `MovementCostMixin`. An exit with `requires_flight=True`
SHALL deny traversal (via its access-lock check, alongside any other existing lock) to a
`PlayerCharacter` that owns neither `flight` nor `flash_step`. No exit shipped by this change sets
`requires_flight=True` — the flag exists for future map content to opt into.

#### Scenario: An entity without flight or flash_step cannot traverse a flight-required exit
- **WHEN** a `PlayerCharacter` owning neither `flight` nor `flash_step` attempts to traverse an exit
  with `requires_flight=True`
- **THEN** the traversal is denied the same way a locked exit denies traversal (per this capability's
  existing "A locked exit never charges and never records" scenario)

#### Scenario: An entity with flight or flash_step can traverse a flight-required exit
- **WHEN** a `PlayerCharacter` owning `flight` (or, separately, one owning only `flash_step`) attempts
  to traverse an exit with `requires_flight=True`
- **THEN** the traversal succeeds (subject to any other unrelated lock on the same exit)

#### Scenario: No existing exit is flight-required by default
- **WHEN** any exit shipped before this change is inspected
- **THEN** its `requires_flight` is `False`