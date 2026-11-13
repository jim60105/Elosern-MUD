# Spec Delta

## MODIFIED Requirements

### Requirement: Road nodes are the gated settlements of the configured kinds
Generation SHALL make a stage-one node of every location whose kind is configured and whose settlement document declares a wilderness gate, and of no other location. A spur kind or an open-cell kind SHALL NOT be accepted as a configured node kind.

#### Scenario: Excluded locations
- **WHEN** a synthetic world holds a configured-kind location with gates, one with no settlement document, one whose settlement has no gates, and a gated location of an unconfigured kind
- **THEN** only the first location is a node

#### Scenario: An absent parameter document stops generation
- **WHEN** a synthetic world has no road parameter document
- **THEN** building the generation input raises an error naming the missing document

#### Scenario: A new settlement document joins with no other change
- **WHEN** a settlement document with gates is added for a configured-kind location that previously had none
- **THEN** that location becomes a node with the same parameter document

#### Scenario: A spur kind cannot be a configured node kind
- **WHEN** the parameter document lists the village kind among its node kinds
- **THEN** building the generation input raises an error naming that kind

### Requirement: The road cost field admits only legal walkable steps
Road cells SHALL lie on walkable cells outside forbidden regions, anchor footprints and non-node gateway cells, and road steps SHALL obey the eight-direction no-corner-cutting rule. The footprint and gateway cells of village and hamlet locations SHALL stay open to roads.

#### Scenario: Rivers are crossed only at fords
- **WHEN** a synthetic river separates two settlements and has one ford away from the straight line between them
- **THEN** the road between them crosses the river only on the ford cell

#### Scenario: Corners are not cut
- **WHEN** a diagonal step would pass an unwalkable orthogonal neighbour
- **THEN** no generated road contains that step

#### Scenario: Steep steps cost more in both directions
- **WHEN** a flat detour and a shorter path crossing a band step connect two settlements, and the slope factor makes the band step dearer than the detour
- **THEN** the road takes the detour, and swapping the two band values on either side of the step does not change that choice

#### Scenario: A forbidden region separates networks
- **WHEN** a forbidden region is the only connection between two groups of settlements
- **THEN** generation produces two networks with no road between them

#### Scenario: Roads stay off settlements and hidden gateways
- **WHEN** an anchor footprint and the point gateway cell of an unconfigured-kind location lie on the cheapest line between two nodes
- **THEN** the road passes around both cells

#### Scenario: Village and hamlet cells stay open
- **WHEN** a hamlet with a point-entry document and a village with a two-cell footprint document lie on the straight line between two nodes on uniform ground
- **THEN** the road between the two nodes passes through the hamlet cell and through a village footprint cell

### Requirement: Generation refuses an invalid network
Generation SHALL check every candidate network independently of the routing that produced it and SHALL fail with an error naming the node or road at fault, writing no artifact.

#### Scenario: Isolated node
- **WHEN** a node has no walkable connection to any other node
- **THEN** generation fails naming that node

#### Scenario: Unusable gate approach
- **WHEN** a node's gate approach cell is not walkable or lies in a forbidden region
- **THEN** generation fails naming that node and cell

#### Scenario: Hand-built invalid networks
- **WHEN** the self-check receives a road with an unwalkable cell, an illegal step, a wrong end cell, a split network, a road joining two separate networks, or a road leaving a point gateway in its gate direction
- **THEN** it reports each fault naming the road or nodes involved

#### Scenario: Unreachable or misplaced village
- **WHEN** one village has no walkable connection to any node, and another village's cell is unwalkable or lies in a forbidden region
- **THEN** generation fails naming each village

#### Scenario: Hand-built invalid spurs
- **WHEN** the self-check receives a spur whose owner is not one of its ends, a village owning two spurs, and an unmarked road ending at a village
- **THEN** it reports each fault naming the road or village involved

## ADDED Requirements

### Requirement: Each village receives one spur to its cheapest node
After stage one, generation SHALL process village locations in identifier order and route one spur from each village's cell to the candidate node with the lowest walking cost on the cost field as repriced by every road routed so far. Candidates SHALL be the stage-one nodes and the villages already processed. A village SHALL need no settlement document.

#### Scenario: One spur per village
- **WHEN** a synthetic world has two towns and one village away from their road, the village having no settlement document
- **THEN** exactly one road is marked as that village's spur, it starts on the village cell and ends on a gate approach cell of a town

#### Scenario: The cheapest node is chosen
- **WHEN** a village is nearer in cells to one town but a costly band makes the other town cheaper to walk to
- **THEN** the spur ends at the cheaper town

#### Scenario: A spur reuses earlier road cells
- **WHEN** a village lies beside a trunk far from both of its ends
- **THEN** a reuse factor below one yields more cells shared between the spur and the trunk than a reuse factor of one

#### Scenario: Fixed order decides village targets
- **WHEN** two villages lie in a line beyond a town and the nearer village sorts first, and then the identifiers are swapped so the farther village sorts first
- **THEN** in the first case the farther village's spur ends on the nearer village's cell, and in the second case it ends on a gate approach cell of the town

### Requirement: Stage one is independent of villages and hamlets
The stage-one roads SHALL be identical with and without village and hamlet locations in the input, and an input with no village SHALL produce an artifact with no spur.

#### Scenario: Trunks do not move
- **WHEN** one synthetic layout is generated with and without added villages and hamlets, some of them with settlement documents
- **THEN** the unmarked roads of the two results are equal

#### Scenario: No village keeps the artifact format
- **WHEN** generation runs on a synthetic input with no village
- **THEN** the output has no spur mark and equals the encoding of the stage-one roads alone, byte for byte
