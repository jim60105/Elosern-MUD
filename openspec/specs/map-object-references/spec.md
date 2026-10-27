# map-object-references Specification

## Purpose
Replace static coordinate targets with qualified authored references before converting their owning documents. This capability defines the observable mechanism boundary for its consumers.

## Requirements

### Requirement: Static references resolve by authored identity
Static map targets SHALL use qualified stable identities and derive coordinate-backed game locators at consumer boundaries from current bindings.

#### Scenario: Identity movement
- **WHEN** a settlement node with gate, interior, district, static quest/service and art dependents moves
- **THEN** every dependent resolves the same ID at its new coordinate without rewriting those declarations or changing wire grammar

#### Scenario: Resolution errors
- **WHEN** a static reference names an absent object or wrong domain
- **THEN** validation identifies the target/source and rejects adoption before persistent mutation
