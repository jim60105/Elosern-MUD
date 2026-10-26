# Spec Delta

## MODIFIED Requirements

### Requirement: Room official references are explicit authored keys
Static room scene/art references SHALL come from map documents and be checked against authoritative game catalogs before adoption; map owners synchronize them without inferring keys or generating undeclared art.

#### Scenario: Permanent interior metadata converges
- **WHEN** startup runs twice for an authored permanent interior
- **THEN** its valid scene archetype and declared optional artwork key converge without duplicate rooms or inferred keys

#### Scenario: Instance accepts an explicit key
- **WHEN** a supported instance declaration supplies a registered key
- **THEN** construction preserves that key; undeclared instances have none

