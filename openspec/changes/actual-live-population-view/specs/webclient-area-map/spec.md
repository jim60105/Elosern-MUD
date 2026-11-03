# Spec Delta

## MODIFIED Requirements

### Requirement: Wilderness area maps cover a revealed forty-one-cell neighbourhood
Wilderness area_map SHALL cover the centred41-by-41 window using permanent ground reveal and exact unknown runs; only legal revealed neighbouring steps carry canonical movement descriptors and invalid/replaced cells never become fabricated walkable nodes.

#### Scenario: Neighbourhood is bounded around the current cell
- **WHEN** the player opens area scope in wilderness
- **THEN** the coordinate window is current minus twenty through current plus twenty in each axis, with out-of-frame cells unknown, actual visits distinguished from reveal, and only legal revealed immediate steps actionable

#### Scenario: Entity presence is actual
- **WHEN** revealed map cells contain actual living individuals and empty configured recovery habitats
- **THEN** entity annotations include only actual current IDs with canonical threat facts; habitat commission markers remain separate and do not assert live presence

