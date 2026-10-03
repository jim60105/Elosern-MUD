## Purpose

Preserves character knowledge and beliefs with immutable provenance, permission boundaries, and recoverable effective-state revision history.

## ADDED Requirements

### Requirement: Cognition is owner-scoped and provenance-preserving

Memory SHALL identify owner, creation tick, category, tier, content, salience, knowledge scope, confidence, subjects, sources and derived generation when applicable. Content and provenance SHALL be immutable. Access SHALL distinguish witnessed, told, inferred and genuinely public information, excluding private authoring and other owners private cognition.

#### Scenario: Only an observer learns protection
- **WHEN** one synthetic NPC witnesses protection and another does not
- **THEN** only the eligible observer gains witnessed memory

#### Scenario: Claim is not fact
- **WHEN** a source claims a dragon exists without authoritative evidence
- **THEN** the memory records being told the claim and creates no dragon

### Requirement: Revision history remains recoverable

Availability, tier, decay metadata, supersession and record relationships SHALL retain recoverable revisions and originals. Effective changes SHALL atomically increase the owner generation. Normal access SHALL exclude inactive/superseded records; historical access SHALL retain permissions.

#### Scenario: Supersession changes normal results
- **WHEN** a record is superseded
- **THEN** normal access excludes it, historical access preserves provenance, and owner generation increases

### Requirement: Memory projection is idempotent and restart-safe

Durable source processing SHALL atomically create eligible memories and settle progress. Reprocessing SHALL NOT duplicate records; restart SHALL resume unsettled sources.

#### Scenario: Restart after failed projection
- **WHEN** projection fails before its transaction commits and restarts
- **THEN** progress stays pending and success creates one record per eligible owner/source

