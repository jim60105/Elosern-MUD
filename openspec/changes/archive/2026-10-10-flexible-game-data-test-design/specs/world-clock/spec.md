# Spec Delta

## MODIFIED Requirements

### Requirement: move and converse command-default time costs are declared as rulebook data only
`world/rules/rulebook/clock.yaml`'s `command_defaults` mapping SHALL declare valid authored `move` and
`converse` durations (design doc §6.5's flat defaults). `move` SHALL be consumed by every successful
traversal of a `typeclasses.exits.Exit` or `typeclasses.exits.CostedXYZExit` instance by a
`PlayerCharacter`, via `world.rules.movement.charge_movement()` (the `movement-cost-charging`
capability). This change SHALL NOT add a bespoke `move` or `converse` Evennia command.

#### Scenario: move and converse defaults are declared
- **WHEN** `rulebook/clock.yaml`'s `command_defaults` is inspected
- **THEN** it contains valid authored move and converse durations; exact seconds are tunable data

#### Scenario: No move or converse command is added by this change
- **WHEN** `commands/` is inspected for files added by this change
- **THEN** no command named `move` or `converse` is defined in any file this change adds

#### Scenario: The move cost is consumed by ordinary exit traversal, not a bespoke command
- **WHEN** `commands/` is inspected for files added by this change, and the mechanism that invokes
  `world.rules.movement.charge_movement()` is inspected
- **THEN** no command named `move` or `converse` exists anywhere, and the cost is instead consumed
  from inside `typeclasses/exits.py::MovementCostMixin.at_post_traverse` ;  a hook on the exit object
  itself, fired by Evennia's own per-exit, auto-generated traversal command, not by a new command this
  change adds

#### Scenario: A successful exit traversal advances the clock by the move cost
- **WHEN** a `PlayerCharacter` successfully traverses a `typeclasses.exits.Exit` or
  `typeclasses.exits.CostedXYZExit` instance
- **THEN** `WorldClock.tick` increases by exactly `CLOCK_YAML["command_defaults"]["move"]`

#### Scenario: converse remains unconsumed
- **WHEN** `world/rules/rulebook/clock.yaml`'s `converse` value is inspected for any consumer added by
  this change
- **THEN** no code added by this change reads `command_defaults["converse"]`

#### Scenario: Traversal hooks come from Evennia's auto-generated commands
- **WHEN** a player traverses an exit
- **THEN** `at_traverse`/`at_post_traverse` are invoked by Evennia's own per-exit, auto-generated
  traversal commands

#### Scenario: converse stays exactly as changes 11 and 13 left it
- **WHEN** the converse command surface is inspected after this change
- **THEN** `converse` remains unwired, exactly as change 11 and change 13 left it
