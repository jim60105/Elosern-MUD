## ADDED Requirements

### Requirement: Exploration move rows advertise canonical destinations

The exploration menu's wilderness move rows SHALL use the canonical destination resolver so the advertised destination equals the node the player actually arrives at.

#### Scenario: Move row destination matches actual arrival

- **WHEN** the exploration menu lists wilderness move rows
- **THEN** each row's destination is the canonical arrival node, including the gateway south row that returns to the grid
