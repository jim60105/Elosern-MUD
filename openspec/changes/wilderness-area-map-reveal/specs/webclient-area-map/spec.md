## RENAMED Requirements

- FROM: `### Requirement: Wilderness area maps cover a fifteen-cell neighbourhood`
- TO: `### Requirement: Wilderness area maps cover a revealed forty-one-cell neighbourhood`

## MODIFIED Requirements

### Requirement: Wilderness area maps cover a revealed forty-one-cell neighbourhood
Wilderness area_map SHALL cover the centred41-by-41 window using permanent ground reveal and exact unknown runs; only legal revealed neighbouring steps carry canonical movement descriptors and invalid/replaced cells never become fabricated walkable nodes.

#### Scenario: Neighbourhood is bounded around the current cell
- **WHEN** the player opens area scope in wilderness
- **THEN** the coordinate window is current minus twenty through current plus twenty in each axis, with out-of-frame cells unknown, actual visits distinguished from reveal, and only legal revealed immediate steps actionable


