## MODIFIED Requirements

### Requirement: Map panels use exact layer and precision discriminators
Map panels SHALL use exact versioned layer schemas; wilderness area schema2 carries bounded RLE terrain, current sight and approximate sightings, while metric/coordinate-free graph layers and world-map precision retain their existing contracts.

#### Scenario: Coordinate frames are not interchangeable
- **WHEN** a player crosses from settlement to wilderness or enters another interior
- **THEN** the new panel changes stable map/frame identity and its node geometry has the new declared units, without inheriting coordinates from the prior frame

#### Scenario: Malformed or secretly enriched records are rejected
- **WHEN** a node, unlit district or approximate marker has extra fields or wrong discriminator types
- **THEN** both validators reject it rather than preserving unknown metadata


