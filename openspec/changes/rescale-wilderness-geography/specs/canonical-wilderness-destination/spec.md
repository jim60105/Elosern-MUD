# Spec Delta

## MODIFIED Requirements

### Requirement: Wilderness destination resolution is canonical, shared, and registry-driven
The system SHALL provide one resolver that derives the actual arrival node for a wilderness
direction from the current coordinates, direction, and the gateway rules of
`WILDERNESS_ENTRY_REGISTRY`, and SHALL NOT derive destinations from the pooled self-loop
`exit_obj.destination`. It returns the gate's destination room `grid:` node at a registered
gate's `approach_cell` and `return_direction`, `None` on a provider-invalid neighbor cell,
and otherwise the adjacent `wild:` node. A point-shape entry answers only its authored
`return_direction`; its other directions resolve as ordinary wilderness steps.

#### Scenario: Wilderness direction resolves to the true neighbor
- **WHEN** the resolver is asked for the north direction from `wild:(500, 700)`
- **THEN** it returns `wild:elosern:500:701` (the true neighbor cell), not the current node

#### Scenario: A gate step resolves to its grid room
- **WHEN** the resolver is asked for the north direction from the south approach cell `(860, 1077)`
- **THEN** it returns the `grid:` node of the 南門 room `(3, 0, "capital_altoria")`, and the west
  direction from the east approach cell `(864, 1080)` returns the `grid:` node of the East Gate
  room `(6, 3, "capital_altoria")` (logical grid coordinates; the meter cutover belongs to
  `activate-metric-settlements`)

#### Scenario: The non-gate direction at an approach cell is an ordinary step
- **WHEN** the resolver is asked for the south direction from `(860, 1077)` or the north direction
  from `(864, 1080)`
- **THEN** it returns the ordinary adjacent `wild:` node, not a `grid:` node

#### Scenario: A step into an anchor footprint resolves to None
- **WHEN** the resolver is asked for the east direction from `(856, 1080)` (neighbor `(857, 1080)`,
  a footprint cell that is not any gate's approach cell) or for the west direction from
  `(864, 1081)` (neighbor `(863, 1081)`, likewise)
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

#### Scenario: Resolver semantics mirror the return exit exactly
- **WHEN** the resolver's rules are compared with `WildernessReturnExit.at_traverse`
- **THEN** they match exactly, including every registered gate step that returns to the grid

#### Scenario: Gateway lookup and validity rule are shared helpers
- **WHEN** the gateway lookup or the neighbor-validity rule is invoked by any caller
- **THEN** each is a single shared helper that `WildernessReturnExit` also uses — no duplicated per-call-site rule

#### Scenario: Provider-invalid spans out-of-rectangle and footprint cells
- **WHEN** a neighbor cell is provider-invalid — outside the 2700-cell frame, at sea, on the closed
  ridge or an inland waterway, or an anchor footprint cell
- **THEN** resolution returns `None`, mirroring the step refusal

#### Scenario: The legacy single-pair rule is gone entirely
- **WHEN** destination resolution is searched for the legacy single-pair rule (direction `"s"` at an entry's single `wilderness_xy`)
- **THEN** it does not exist in any form
