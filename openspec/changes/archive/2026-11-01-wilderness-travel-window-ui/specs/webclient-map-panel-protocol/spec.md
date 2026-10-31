## MODIFIED Requirements

### Requirement: Map panels use exact layer and precision discriminators
Map panels SHALL retain exact versioned layer schemas and existing precision/disclosure rules; wilderness area schema3 SHALL extend schema2 terrain, nodes and entities with bounded display annotations while unknown runs remain minimal.

#### Scenario: Coordinate frames are not interchangeable
- **WHEN** a player crosses from settlement to wilderness or enters another interior
- **THEN** the new panel changes stable map/frame identity and its node geometry has the new declared units, without inheriting coordinates from the prior frame

#### Scenario: Malformed or secretly enriched records are rejected
- **WHEN** a node, unlit district or approximate marker has extra fields or wrong discriminator types
- **THEN** both validators reject it rather than preserving unknown metadata

#### Scenario: Display additions cannot enrich unknowns
- **WHEN** schema3 includes district/terrain/ford labels, settlement flags, landmark names and hostile count/threat
- **THEN** fields validate only in their exact disclosed record variants, old wilderness schemas reject, unknown records gain no metadata and existing logical byte limits remain
