# Spec Delta

## ADDED Requirements

### Requirement: Villages and hamlets use a single-cell layout whose entrances follow the roads
For a village or hamlet, generation SHALL emit a one-cell physical footprint on the location cell with one gate per road cell that precedes or follows that cell on any road, each gate approached from that road cell, and at least the budget's node count, all joined to the anchor. A hamlet with no such road cell SHALL get one gate; a village with none SHALL be refused.

#### Scenario: Through road
- **WHEN** a synthetic village and a synthetic hamlet each stand on an inner cell of a road
- **THEN** each has two gates whose approach cells are the two neighbouring road cells, the village has four nodes and the hamlet two

#### Scenario: End of a spur
- **WHEN** a synthetic village's cell is the last cell of a road
- **THEN** it has one gate approached from the preceding road cell and four nodes

#### Scenario: Junction
- **WHEN** three road cells touch the location cell
- **THEN** the map has three gates, and its node count exceeds the budget's minimum by one

#### Scenario: No road
- **WHEN** a synthetic hamlet and a synthetic village have no road cell touching their cells
- **THEN** the hamlet has one gate on a walkable unblocked neighbour and two nodes, and the village is refused naming the missing road, with no file written

#### Scenario: The document is valid and deterministic
- **WHEN** any of those maps is generated twice
- **THEN** the bytes are identical, the document loads, every node lies inside the one footprint cell, every non-anchor node has a two-way road to the anchor, and the terrain-fit lint reports no error

#### Scenario: Beastfolk nation
- **WHEN** the same synthetic sites belong to a configured beast nation
- **THEN** the reported class and morphology are the tribal ones, and the gate and node counts equal those of the other nation

## MODIFIED Requirements

### Requirement: The generator never overwrites and batches in a fixed order
The generator SHALL refuse a location that already has a settlement document and leave every file unchanged. A plan-only run SHALL write nothing. A batch for one nation SHALL generate only national settlements that have no document, in order of descending population and then identifier, optionally narrowed to one kind. Each map SHALL see the footprints written earlier in the same batch.

#### Scenario: Existing document
- **WHEN** generation targets a synthetic location whose settlement document exists
- **THEN** the command exits with status 1 naming the existing file, and the workspace digest is unchanged

#### Scenario: Plan only and batch order
- **WHEN** a plan-only run and then a batch run cover two synthetic national settlements of one nation
- **THEN** the plan-only run leaves the digest unchanged, and the batch writes the larger settlement first, with the second footprint disjoint from the first

#### Scenario: Kind filter
- **WHEN** a nation has a town, a village and a hamlet without documents and the batch runs narrowed to the hamlet kind, and then with no filter
- **THEN** the first run writes only the hamlet, and the second writes the town and the village

#### Scenario: Replace is refused for single-cell kinds
- **WHEN** a replace run targets a synthetic village that has a document
- **THEN** the command exits with status 1 naming the refusal, and the workspace digest is unchanged
