# authored-dialogue-content Specification

## Purpose

Authored dialogue for the static hosts is published through automatically discovered
`world/lore/dialogue/content/<NpcProfile.key>.yaml` files. Each content slice owns only its
own YAML files plus a human review document; the capability's verifiable contract is
filename-derived ownership, stable topic identity and atomic snapshot rejection. Editorial
quality (voice, source fidelity, register) is reviewed in `docs/lore/*-dialogue-review.md`,
not asserted by tests.

## Requirements

### Requirement: guild content has exclusive profile-key YAML ownership
The owned hosts SHALL obtain rewritten topics and greetings from automatically discovered `world/lore/dialogue/content/<NpcProfile.key>.yaml` files using the exact canonical bindings in design.md. Filenames SHALL derive ownership without duplicate owner fields or manual registration. Content replacement SHALL leave canonical profiles read-only and retain existing stable topic IDs and deterministic effects.

#### Scenario: Owned files are discovered without registration
- **WHEN** all exclusively owned YAML files pass the shared static snapshot validation
- **THEN** each canonical host receives its rewritten greeting and four baseline topics with original stable topic IDs through normal discovery, with no registration-list or profile edit

#### Scenario: Invalid content cannot partially replace the snapshot
- **WHEN** an owned YAML contains duplicate mapping keys, unsafe tags, unknown profile ownership, invalid schema or unresolved declaration references
- **THEN** validation rejects publication of the complete new snapshot and exposes no partially accepted replacement

### Requirement: lower-hospitality content has exclusive profile-key YAML ownership
The owned hosts SHALL obtain their authored topics and greetings from automatically discovered
`world/lore/dialogue/content/<NpcProfile.key>.yaml` files using the exact canonical bindings in
design.md. Filenames SHALL derive ownership without duplicate owner fields or manual
registration. Content replacement SHALL leave canonical profiles read-only and retain existing
stable topic IDs and deterministic effects.

#### Scenario: Owned files are discovered without registration
- **WHEN** the exclusively owned files `altoria_eatery_owner.yaml`、`altoria_tavern_keeper.yaml`、`altoria_innkeeper.yaml` pass the shared static snapshot validation
- **THEN** their canonical hosts `altoria_eatery_owner`、`altoria_tavern_keeper`、`altoria_innkeeper` receive the authored greeting and the four baseline topics with original stable topic IDs through normal discovery, with no registration-list or profile edit

#### Scenario: Invalid content cannot partially replace the snapshot
- **WHEN** an owned YAML contains duplicate mapping keys, unsafe tags, unknown profile ownership, invalid schema or unresolved declaration references
- **THEN** validation rejects publication of the complete new snapshot and exposes no partially accepted replacement

### Requirement: lower-civic content has exclusive profile-key YAML ownership
The owned hosts SHALL obtain their authored topics and greetings from automatically discovered
`world/lore/dialogue/content/<NpcProfile.key>.yaml` files using the exact canonical bindings in
design.md. Filenames SHALL derive ownership without duplicate owner fields or manual
registration. Content replacement SHALL leave canonical profiles read-only and retain existing
stable topic IDs and deterministic effects.

#### Scenario: Owned files are discovered without registration
- **WHEN** the exclusively owned files `altoria_bathhouse_keeper.yaml`、`altoria_guard_captain.yaml` pass the shared static snapshot validation
- **THEN** their canonical hosts `altoria_bathhouse_keeper`、`altoria_guard_captain` receive the authored greeting and the four baseline topics with original stable topic IDs through normal discovery, with no registration-list or profile edit

#### Scenario: Invalid content cannot partially replace the snapshot
- **WHEN** an owned YAML contains duplicate mapping keys, unsafe tags, unknown profile ownership, invalid schema or unresolved declaration references
- **THEN** validation rejects publication of the complete new snapshot and exposes no partially accepted replacement

### Requirement: middle-tools content has exclusive profile-key YAML ownership
The owned hosts SHALL obtain their authored topics and greetings from automatically discovered
`world/lore/dialogue/content/<NpcProfile.key>.yaml` files using the exact canonical bindings in
design.md. Filenames SHALL derive ownership without duplicate owner fields or manual
registration. Content replacement SHALL leave canonical profiles read-only and retain existing
stable topic IDs and deterministic effects.

#### Scenario: Owned files are discovered without registration
- **WHEN** the exclusively owned files `altoria_merchant.yaml`、`altoria_blacksmith.yaml`、`altoria_tailor.yaml` pass the shared static snapshot validation
- **THEN** their canonical hosts `altoria_merchant`、`altoria_blacksmith`、`altoria_tailor` receive the authored greeting and the four baseline topics with original stable topic IDs through normal discovery, with no registration-list or profile edit

#### Scenario: Invalid content cannot partially replace the snapshot
- **WHEN** an owned YAML contains duplicate mapping keys, unsafe tags, unknown profile ownership, invalid schema or unresolved declaration references
- **THEN** validation rejects publication of the complete new snapshot and exposes no partially accepted replacement
