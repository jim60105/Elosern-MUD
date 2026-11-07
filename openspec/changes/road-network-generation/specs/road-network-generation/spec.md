# Spec Delta

## Purpose

Generate the wilderness road network offline and deterministically from the authored map sources, so that moving or adding a settlement needs one regeneration and no hand-authored road data.

## ADDED Requirements

### Requirement: Road parameters are a validated authored document
The authored source set SHALL include one optional road parameter document. A supplied document SHALL be validated with no default substitution, and generation SHALL refuse to run when the document is absent.

#### Scenario: Invalid content is rejected
- **WHEN** a candidate road parameter document has an unknown field, an unknown node kind, or a value outside its declared range
- **THEN** authoring load rejects the candidate with a source diagnostic naming the field

#### Scenario: Unknown forbidden region is rejected
- **WHEN** a road parameter document forbids a region the continent does not declare
- **THEN** authoring load rejects the candidate with a diagnostic naming that region

#### Scenario: An absent document stops generation only
- **WHEN** a synthetic world has no road parameter document
- **THEN** authoring load succeeds and building the generation input raises an error naming the missing document

#### Scenario: Tuning leaves other artifacts current
- **WHEN** only the road parameter document changes
- **THEN** the district partition signature and the elevation source signature do not change

### Requirement: Road nodes are the gated settlements of the configured kinds
Generation SHALL make a node of every location whose kind is configured and whose settlement document declares a wilderness gate, and of no other location.

#### Scenario: Excluded locations
- **WHEN** a synthetic world holds a configured-kind location with gates, one with no settlement document, one whose settlement has no gates, and a gated location of an unconfigured kind
- **THEN** only the first location is a node

#### Scenario: A new settlement document joins with no other change
- **WHEN** a settlement document with gates is added for a configured-kind location that previously had none
- **THEN** that location becomes a node and no other source needs editing

### Requirement: The road cost field admits only legal walkable steps
Road cells SHALL lie on walkable cells outside forbidden regions, anchor footprints and non-node gateway cells, and road steps SHALL obey the eight-direction no-corner-cutting rule.

#### Scenario: Rivers are crossed only at fords
- **WHEN** a synthetic river separates two settlements and has one ford away from the straight line between them
- **THEN** the road between them crosses the river only on the ford cell

#### Scenario: Corners are not cut
- **WHEN** a diagonal step would pass an unwalkable orthogonal neighbour
- **THEN** no generated road contains that step

#### Scenario: A forbidden region separates networks
- **WHEN** a forbidden region is the only connection between two groups of settlements
- **THEN** generation produces two networks with no road between them

#### Scenario: Roads stay off settlements and hidden gateways
- **WHEN** an anchor footprint and the point gateway cell of an unconfigured-kind location lie on the cheapest line between two nodes
- **THEN** the road passes around both cells

### Requirement: Road topology is a relative neighbourhood graph with detour repair
Generation SHALL keep a settlement pair unless a third settlement is closer to both by terrain distance, then SHALL add terrain-neighbour pairs while the worst network detour ratio exceeds the configured limit.

#### Scenario: A middle settlement removes the long pair
- **WHEN** three settlements lie in a line on uniform ground
- **THEN** the two adjacent pairs have roads and the outer pair has none

#### Scenario: A large detour adds a road
- **WHEN** two terrain-neighbour settlements are joined by the network only through a detour above the limit
- **THEN** the pair gains a direct road, and with a limit above that detour it gains none

#### Scenario: Terrain changes the neighbourhood
- **WHEN** a synthetic wall lengthens the walking path between two settlements that are close in straight-line distance
- **THEN** topology follows the walking cost and not the straight-line distance

### Requirement: Roads are routed cheapest first and reuse earlier cells
Generation SHALL route kept pairs from cheapest to most expensive between gate approach cells, with steps on earlier road cells priced by the configured reuse factor.

#### Scenario: Later roads merge into a trunk
- **WHEN** two roads to one settlement run close together on uniform ground
- **THEN** a reuse factor below one yields more shared cells than a reuse factor of one

#### Scenario: Roads end at gates
- **WHEN** a settlement with several gates is joined to a neighbour
- **THEN** the road's first and last cells are gate approach cells of its two end settlements, and one gate may serve several roads

### Requirement: Generation refuses an invalid network
Generation SHALL check every candidate network independently of the routing that produced it and SHALL fail with an error naming the node or road at fault, writing no artifact.

#### Scenario: Isolated node
- **WHEN** a node has no walkable connection to any other node
- **THEN** generation fails naming that node

#### Scenario: Unusable gate approach
- **WHEN** a node's gate approach cell is not walkable or lies in a forbidden region
- **THEN** generation fails naming that node and cell

#### Scenario: Hand-built invalid networks
- **WHEN** the self-check receives a road with an unwalkable cell, an illegal step, a wrong end cell, a split network, or a road joining two separate networks
- **THEN** it reports each fault naming the road or nodes involved

### Requirement: The road artifact reproduces deterministically and reports freshness
Identical inputs SHALL produce identical artifact bytes. Artifact decoding, metadata and freshness SHALL work without the generation extra, and any change to a road input SHALL read as stale.

#### Scenario: Repeat runs match
- **WHEN** generation runs twice on identical synthetic input
- **THEN** the two outputs match byte for byte

#### Scenario: Codec round trip
- **WHEN** a synthetic artifact is decoded
- **THEN** its roads and cell set equal the generator's result

#### Scenario: Changed input reads as stale
- **WHEN** a continent, location, settlement or road parameter source, the elevation fingerprint or a region speed changes
- **THEN** the source signature changes and the artifact is not current

#### Scenario: Unrelated sources stay current
- **WHEN** only an interior document or the district document changes
- **THEN** the source signature does not change

#### Scenario: Corrupt artifact is rejected
- **WHEN** an artifact has a wrong version, a malformed field, an odd cell list, a cell outside the frame or a fingerprint that disagrees with its roads
- **THEN** decoding raises the road document error

#### Scenario: Independent decoding
- **WHEN** the codec is imported in a fresh interpreter with NumPy and SciPy blocked
- **THEN** decoding and freshness complete

### Requirement: The regeneration command reports stale artifacts
The regeneration command SHALL write the generated artifact, and its check mode SHALL exit non-zero without writing when the committed artifact differs from the generated bytes.

#### Scenario: Check mode
- **WHEN** check mode runs against a file that differs from the generated text and then against an identical file
- **THEN** it exits non-zero for the first, zero for the second, and leaves both files unchanged

#### Scenario: Failed generation leaves the artifact
- **WHEN** generation raises its self-check error
- **THEN** the command exits non-zero and the output file keeps its previous bytes

#### Scenario: Preview is explicit
- **WHEN** the command receives a preview path
- **THEN** it writes an image to that path, and without a preview path it writes no image
