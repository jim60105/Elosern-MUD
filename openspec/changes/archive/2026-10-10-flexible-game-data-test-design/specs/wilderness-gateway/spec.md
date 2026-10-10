# Spec Delta

## MODIFIED Requirements

### Requirement: wilderness_move is a new, distinct clock cost, not a reuse of the grid's move constant
`world/rules/rulebook/clock.yaml::command_defaults` SHALL include the distinct authored `wilderness_move`
(seconds) key, independent of the existing `move` entry. No code in this change SHALL read `move` for
wilderness traversal, and no code from change 12 (grid traversal) SHALL be modified to read
`wilderness_move`.

#### Scenario: wilderness_move is present and distinct from move
- **WHEN** `world/rules/rulebook/clock.yaml` is inspected after this change lands
- **THEN** both entries are valid authored durations and wilderness traversal uses wilderness_move while grid traversal uses move

#### Scenario: Grid traversal is unaffected
- **WHEN** a character traverses an intra-city `CostedXYZExit` created by change 12's `sync_grid()`
  with this change's `("*", "*", "*")` wildcard prototype override
- **THEN** `get_world_clock().tick` increases by exactly `CLOCK_YAML["command_defaults"]["move"]`, and
  no grid-traversal code reads `wilderness_move` ;  grid traversal is unaffected by the wilderness
  cost, charging the ordinary `move` cost instead

#### Scenario: Amended 2026-08-01 change map-movement-clock background
- **WHEN** the previous wording's claim that intra-city grid traversal "remains unwired to the
  clock" is re-read
- **THEN** that statement is false, since `map-movement-clock` wires every intra-city link to
  charge `command_defaults.move` through `CostedXYZExit` (the `sample-city-altoria`
  capability)
- **AND** the distinctness claim that is this requirement's real subject is unchanged:
  wilderness steps pay `wilderness_move`, grid steps pay `move`, and the two lineages never
  read each other's constant; the amended scenario above asserts exactly that
