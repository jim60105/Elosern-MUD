# narrative-memory Specification

## Purpose
Preserves character knowledge and beliefs with immutable provenance, permission boundaries, and recoverable effective-state revision history.

## Requirements

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

### Requirement: Adult memories authorize fields per participant
Adult narrative memories SHALL be derived only from fields the memory owner is authorized to know. Event visibility and presence SHALL NOT authorize every participant's private milestone, roll, compliance reasoning or counter. The same recipient-authorized projection SHALL serve nomination and memory boundaries. Unsupported or malformed adult records SHALL remain fail-closed rather than falling through to a raw-content memory branch.

#### Scenario: Public adult event hides another participant's private history
- **WHEN** an adult action is witnessed by a third living participant while one participant has private milestone history and an unknown internal counter
- **THEN** each participant's memory contains only the acts, roles and results that participant can know; the third participant receives no private milestone or counter and no invented participation

#### Scenario: Own experience remains available
- **WHEN** the player is an adult-action participant and the affected fields are knowable to the player
- **THEN** the player's authorized memory retains those fields and source provenance without explicit consent or relationship claims

#### Scenario: Memory projection reuses its source exactly once
- **WHEN** committed adult memory projection is retried or resumes after process restart
- **THEN** the original source and progress are reused once per authorized owner, with no duplicate memory and no newly authorized private fields

#### Scenario: Malformed adult payload does not bypass authorization
- **WHEN** an adult event has an unsupported shape
- **THEN** projection fails closed for that record with a diagnostic and no raw-content memory is created
