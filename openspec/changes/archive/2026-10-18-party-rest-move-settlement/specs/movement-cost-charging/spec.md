# Spec Delta

## MODIFIED Requirements

### Requirement: charge_movement() is the single, shared movement-cost charging function
`world/rules/movement.py` SHALL provide `charge_movement(traversing_object, cost_key: str, *, source_location, wilderness_source_coordinates=None) -> None`,
resolving the cost from `CLOCK_YAML["command_defaults"][cost_key]` and calling
`world.rules.clock.get_world_clock().advance(cost, AdvanceSource.COMMAND, entities)` when
`world.rules.player_control.is_player_driven(traversing_object)` is true, and doing nothing
otherwise. `entities` SHALL be the traverser followed by every party member the follow step moves
with it: the effective companions co-located in `source_location` before the step and, for a
possessed traverser, the commander's body.

#### Scenario: charge_movement advances the clock by the resolved cost for a PlayerCharacter
- **WHEN** `charge_movement(player_character, "move")` is called
- **THEN** `get_world_clock().tick` after the call equals its value before the call plus
  `CLOCK_YAML["command_defaults"]["move"]`

#### Scenario: charge_movement is a no-op for a non-PlayerCharacter traverser
- **WHEN** `charge_movement(npc, "move")` is called for an `NPC`-typeclassed (not `PlayerCharacter`)
  entity
- **THEN** `get_world_clock().tick` is unchanged

#### Scenario: A possessed NPC charges movement like a player
- **WHEN** `charge_movement(npc, "move")` is called for an NPC that is possessed and puppeted
- **THEN** the clock advances by `CLOCK_YAML["command_defaults"]["move"]` with
  `AdvanceSource.COMMAND`, settling the possessed NPC first and then the commander's body and
  every companion co-located with it in the source room

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

#### Scenario: Movement-event clock advancement is exclusive to charge_movement
- **WHEN** any function or inline call site in this project is inspected for movement-event clock
  advancement
- **THEN** none calls `world.rules.clock.get_world_clock().advance()` for a movement event, and
  every exit lineage that charges movement calls `charge_movement()`

#### Scenario: The flight waiver is keyed on the exact owned-skill membership check
- **WHEN** `charge_movement(traversing_object, cost_key)` runs with `cost_key == "wilderness_move"`
  and `"flight" in traversing_object.skills.owned_keys()`
- **THEN** `charge_movement()` returns without advancing the clock, while every other `cost_key`
  charges normally regardless of owned skills

#### Scenario: A player traversal settles its co-located companions
- **WHEN** `charge_movement(player_character, "move", source_location=room)` runs while companion 艾拉
  is in `room` and companion 卡恩 is elsewhere
- **THEN** the single advance settles the player character and 艾拉, and 卡恩's state is unchanged
