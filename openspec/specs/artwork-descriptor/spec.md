# artwork-descriptor Specification

## Purpose
Define one read-only artwork description with independent subject identity, source revision, generation truth, ordered candidates and attributable fault entries.

## Requirements

### Requirement: Descriptors preserve independent artwork facts
Each canonical descriptor SHALL carry stable subject identity, source revision, independent generation state, ordered real-image or known-fault attempts, and a permitted terminal fallback. Candidates SHALL carry canonical resource identity/version, bounded same-origin URL, origin and applicable geometry. Faults SHALL name the failed source and bounded reason without a URL.

#### Scenario: Official image does not complete generation
- **WHEN** an official candidate is available while generation is pending or failed
- **THEN** its origin is official and the original generation state remains unchanged

#### Scenario: Known faults preserve precedence
- **WHEN** a preferred source is broken and a later source is usable
- **THEN** the descriptor puts the known fault at that preferred position before the later candidate

#### Scenario: Resolution reads without writing
- **WHEN** the same descriptor is built repeatedly
- **THEN** no queue, gallery, room, character, asset status, file or narrative state changes

### Requirement: Descriptors reveal only authorized exact subjects
Consolidated descriptors SHALL be built only for subjects already authorized for the requested view. A gallery request SHALL identify its exact original image, never silently select another card. Unsupported or unavailable panels SHALL remain availability failures rather than invented generation progress.

#### Scenario: Unknown subjects remain hidden
- **WHEN** a catalog is consolidated from account-owned and visible view subjects
- **THEN** no undiscovered NPC, unknown location or another owner's private image appears

#### Scenario: Exact gallery card fails
- **WHEN** the selected card file disappears
- **THEN** its descriptor retains that exact card identity and failure without substituting another card as the original

### Requirement: Source priority and retained access are explicit
Canonical attempts SHALL carry stable source identity and source-layer rank independent of array position. Descriptors SHALL carry bounded backend-authorized retention source tokens. Tokens SHALL distinguish valid regeneration retention from binding removal, revoked access and a known invalid retained resource.

#### Scenario: Changing fault count does not change priority
- **WHEN** a room candidate is preceded by metadata faults while generated content is retained
- **THEN** room remains higher priority and can replace retained generated art after decode

#### Scenario: Pending does not revoke valid prior output
- **WHEN** the current generated candidate is absent during regeneration but prior output is still authorized/readable
- **THEN** matching retention source/token allows the known-good image to remain

#### Scenario: Access revocation is explicit
- **WHEN** the same subject loses access or its binding is removed
- **THEN** the new descriptor removes or changes retention authorization so old pixels cannot remain
