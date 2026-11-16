# Spec Delta

## ADDED Requirements

### Requirement: The village's only outside connection is its concealed wilderness entrance
The village SHALL connect to anything outside it only at its entrance node, which is the return point from the wilderness. No village room SHALL hold an exit into the starting room or receive one from it, and the entrance node SHALL read as a concealed path, not a gate.

#### Scenario: The starting room does not reach the village
- **WHEN** every exit located in the starting room or in a spawned village room is inspected after grid synchronization
- **THEN** none of them joins the starting room and the village

#### Scenario: The entrance does not read as a gate
- **WHEN** the entrance node's key and description are read
- **THEN** they describe a concealed path through the forest, and name no wall, gate or guard

#### Scenario: The wilderness returns to the entrance node
- **WHEN** the village's wilderness entry gates are read
- **THEN** every gate destination is the entrance node

## REMOVED Requirements

### Requirement: The village has exactly one concealed entrance
**Reason**: Its scenarios describe the arrival from 虛境 and the city-gate registry slot,
and both are retired. Characters start in their subrace's settlement
(`subrace-start-settlements`), and 虛境 owns no exits.
**Migration**: Replaced by "The village's only outside connection is its concealed
wilderness entrance". Move the annotations of the tests that covered the old
requirement to the new ID.
