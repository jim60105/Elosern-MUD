## ADDED Requirements

### Requirement: Wilderness minimap nodes are actionable

Every traversable adjacent wilderness node in the local map SHALL carry an `explore.move` action descriptor with the canonical destination node, matching the grid/interior layers' behavior.

#### Scenario: Adjacent wilderness node can be moved to

- **WHEN** the player opens the local map while in wilderness terrain
- **THEN** each traversable adjacent node has a move action whose destination is the canonical node, and activating it moves the player there

#### Scenario: Non-traversable or unreachable nodes stay inert

- **WHEN** a wilderness node is outside the traversable set (e.g. out of bounds)
- **THEN** the node carries no move action
