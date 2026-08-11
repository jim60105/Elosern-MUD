## Purpose

The single canonical resolver that derives the actual arrival node for a wilderness direction from
the current coordinates, direction, and gateway rules, mirroring `WildernessReturnExit.at_traverse`
semantics. The wilderness contrib builds its eight direction exits as self-loops
(`destination=room`), so the pooled exit destination can never name the real arrival node; every
presentation surface (minimap, exploration menu, future surfaces) consumes this resolver instead.

## Requirements


### Requirement: Wilderness destination resolution is canonical and shared
The system SHALL provide one resolver that derives the actual arrival node for a wilderness direction from the current coordinates, direction, and gateway rules, matching `WildernessReturnExit.at_traverse` semantics (including the gateway south exit that returns to the grid), and SHALL NOT derive destinations from the pooled self-loop `exit_obj.destination`.

#### Scenario: Wilderness direction resolves to the true neighbor
- **WHEN** the resolver is asked for the north direction from `wild:(60,100)`
- **THEN** it returns `wild:(60,101)` (or the equivalent true neighbor node), not the current node

#### Scenario: Gateway south resolves to the grid room
- **WHEN** the resolver is asked for the south direction from the gateway coordinate
- **THEN** it returns the grid node the traversal actually reaches
