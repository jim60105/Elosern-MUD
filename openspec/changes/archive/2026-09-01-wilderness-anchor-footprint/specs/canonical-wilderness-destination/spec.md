## RENAMED Requirements

- FROM: `### Requirement: Wilderness destination resolution is canonical and shared`
- TO: `### Requirement: Wilderness destination resolution is canonical, shared, and registry-driven`

## MODIFIED Requirements

### Requirement: Wilderness destination resolution is canonical, shared, and registry-driven
The system SHALL provide one resolver that derives the actual arrival node for a wilderness
direction from the current coordinates, direction, and the gateway rules of
`WILDERNESS_ENTRY_REGISTRY`, matching `WildernessReturnExit.at_traverse` semantics exactly
(including every registered gate step that returns to the grid), and SHALL NOT derive
destinations from the pooled self-loop `exit_obj.destination`. The gateway lookup and the
neighbor-validity rule SHALL each be a single shared helper that `WildernessReturnExit` also
uses — no duplicated per-call-site rule. The resolver SHALL return the `grid:` node of the
gate's destination room when the coordinates equal a registered gate's `approach_cell` and the
direction equals that gate's `return_direction`; SHALL return `None` when the neighbor cell is
provider-invalid (out of the continent rectangle or an anchor footprint cell), mirroring the step
refusal; and SHALL otherwise return the adjacent `wild:` node. The legacy single-pair rule
(direction `"s"` at an entry's single `wilderness_xy`) SHALL NOT exist in any form.

#### Scenario: Wilderness direction resolves to the true neighbor
- **WHEN** the resolver is asked for the north direction from `wild:(60, 96)`
- **THEN** it returns `wild:(60, 97)` (the true neighbor cell), not the current node

#### Scenario: A gate step resolves to its grid room
- **WHEN** the resolver is asked for the north direction from the south approach cell `(60, 97)`
- **THEN** it returns the `grid:` node of the 南門 room `(2, 0, "capital_altoria")`, and the south
  direction from the north approach cell `(60, 103)` returns the `grid:` node of the North Gate
  room `(2, 4, "capital_altoria")`

#### Scenario: The non-gate direction at an approach cell is an ordinary step
- **WHEN** the resolver is asked for the south direction from `(60, 97)` or the north direction
  from `(60, 103)`
- **THEN** it returns the ordinary adjacent `wild:` node, not a `grid:` node

#### Scenario: A step into an anchor footprint resolves to None
- **WHEN** the resolver is asked for the east direction from `(57, 100)` (neighbor `(58, 100)`,
  a footprint cell that is not any gate's approach cell) or for the west direction from
  `(63, 100)` (neighbor `(62, 100)`, likewise)
- **THEN** both return `None`, matching the stock step refusal toward a provider-invalid cell

#### Scenario: Resolver and traversal agree on every direction around a gate
- **WHEN** for each of the eight directions at each approach cell the resolver's prediction is
  compared with the room a real traversal reaches
- **THEN** they agree in all cases (grid room at the gate direction, wild cell at valid ordinary
  directions, refusal where the resolver returned `None`)

#### Scenario: A gateway whose grid room cannot be resolved returns None
- **WHEN** the resolver is asked for a registered gate direction and the gate's destination
  `GridRoom` does not exist
- **THEN** it returns `None`, matching the return exit's fail-closed refusal
