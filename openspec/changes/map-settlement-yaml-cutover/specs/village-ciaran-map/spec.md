# Spec Delta

## MODIFIED Requirements

### Requirement: The village is a small connected grid with one anchor
The village settlement document SHALL define a connected branching graph in its own metre coordinate space with one anchor and costed directed travel, retaining its existing identities and attachments.

#### Scenario: The village grid spawns connected with one anchor
- **WHEN** grid synchronization runs
- **THEN** the village's declared rooms exist in its own coordinate space, are
  mutually reachable, and exactly one of them is an `AnchorRoom` whose
  anchor key is the village's

#### Scenario: Village movement is costed like city movement
- **WHEN** a character walks between two village rooms
- **THEN** the move charges its actual physical edge cost at the same baseline speed as capital streets

#### Scenario: The village occupies a coordinate space of its own
- **WHEN** a coordinate is queried in each settlement's map
- **THEN** the same coordinate resolves to a different room in each, and
  neither settlement's rooms appear in the other's shortest paths

#### Scenario: The village stays a tree as it grows
- **WHEN** the validated sparse village graph's links are counted against its nodes
- **THEN** there is exactly one fewer link than there are nodes, and removing
  any link disconnects the map

#### Scenario: Existing location identities are undisturbed
- **WHEN** the expanded map is parsed
- **THEN** the entrance, the plaza and the existing dwelling approaches
  occupy the approved meter coordinates while their existing dbids and every landed place attachment remain intact

#### Scenario: Growth preserves branching paths without loops
- **WHEN** the village map grows
- **THEN** it remains a tree with no cycle; growth adds leaves and short
  branches around the declared gathering places, without turning the village
  into a town-like street network

#### Scenario: Village text reads as a lived-in forest settlement
- **WHEN** the village's room keys and descriptions are authored
- **THEN** they SHALL be Traditional Chinese and SHALL read as a lived-in
  underground settlement with skylit basins and ravines: no walls, no city gates, no
  marketplace and no signed premises

### Requirement: Ciaran uses metric skylit underground geography
Village geometry SHALL use integer metres from its settlement document while retaining branching topology, qualified attachments and the separation of physical map data from non-map lore.

#### Scenario: Metric identity preservation
- **WHEN** the existing village map is converted or a bound node is moved
- **THEN** node IDs, directions and room joins remain stable without inferring a new exit from coordinates; existing prose/population remain unchanged by conversion

