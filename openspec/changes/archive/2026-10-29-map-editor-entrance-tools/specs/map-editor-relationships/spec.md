# Spec Delta

## Purpose

Implement complete cross-layer entrance editing, navigation and reference-safe deletion from a single owning relationship. This capability defines the observable mechanism boundary for its consumers.

## ADDED Requirements

### Requirement: Cross-layer relationships edit one owner and expose both meanings
Entrance tools SHALL identify and navigate both qualified endpoints and their directional meaning while saving the relationship exactly once in its owning document.

#### Scenario: Edit an entrance
- **WHEN** a two-way exterior/interior relationship endpoint or return label changes
- **THEN** one source document records both meanings and navigation reaches either endpoint with return context

#### Scenario: Protected start and invalid target
- **WHEN** a start entry is edited or an entrance selects an absent/wrong-domain target
- **THEN** one-way start semantics remain and invalid fields identify their relationship without saving

### Requirement: Deletion requires established absence of incoming static references
Object deletion SHALL require no map-internal incoming references and current external context establishing no external incoming static references, without cascading changes.

#### Scenario: Referenced deletion
- **WHEN** a selected object has an interior/district/quest/service incoming target
- **THEN** deletion refuses and locates dependents for separate explicit removal

#### Scenario: Unavailable context
- **WHEN** the index is missing, stale or incompatible
- **THEN** deletion is refused with that reason shown at the delete action while non-destructive inspection/placement/property edits remain possible

#### Scenario: Freshness is checked at execution
- **WHEN** an external source changes after inspection but before a delete or object-removing undo executes
- **THEN** current dependency membership/hashes are rechecked and stale evidence refuses the operation without disk or history changes

