## MODIFIED Requirements

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

## ADDED Requirements

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
