# Spec Delta

## Purpose

Export a deterministic authoritative static-reference closure and support independent freshness checking for safe editor deletion. This capability defines the observable mechanism boundary for its consumers.

## ADDED Requirements

### Requirement: Reference export records authoritative static dependencies
The reference export SHALL reproducibly record external identifiers, incoming qualified map targets and source provenance from authoritative static declarations without reading live database state.

#### Scenario: Authoritative export
- **WHEN** static quest, service, scene/art and lore references are exported twice
- **THEN** identical inputs produce identical output with resolvable incoming targets and no database reads

#### Scenario: Geometry exclusion
- **WHEN** a stable settlement node changes only coordinate
- **THEN** the external source fingerprint remains current and incoming references still identify that node

### Requirement: Reference context freshness covers source closure and membership
Independent reference checking SHALL mark context unavailable when its external source closure, membership, content hashes or supported versions differ from the export.

#### Scenario: Added or removed source
- **WHEN** an external dependency is added, removed or changed, including a transitive source or exporter schema
- **THEN** the independent checker and game CI --check reject freshness without importing game modules

#### Scenario: Deletion evidence
- **WHEN** a current index lists an incoming external static reference
- **THEN** that reference can be identified for deletion refusal; unavailable context cannot establish absence of references

#### Scenario: External source changes before deletion
- **WHEN** an external dependency adds a static map reference while the exported index bytes and browser snapshot remain unchanged
- **THEN** the service's destructive-command freshness check reports unavailable and refuses deletion, including an object-removing undo, without changing disk/history or requiring browser refresh

