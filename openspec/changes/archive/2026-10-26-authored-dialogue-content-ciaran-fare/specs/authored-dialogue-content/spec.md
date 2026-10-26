# Spec Delta

## Purpose

Authored dialogue for the ciaran-fare hosts is published through automatically discovered
`world/lore/dialogue/content/<NpcProfile.key>.yaml` files. This slice owns only its own YAML
files plus one human review document; editorial quality (voice, source fidelity, register) is
reviewed there and is deliberately not asserted by a test.

## ADDED Requirements

### Requirement: ciaran-fare content has exclusive profile-key YAML ownership
The owned hosts SHALL obtain their authored topics and greetings from automatically discovered
`world/lore/dialogue/content/<NpcProfile.key>.yaml` files using the exact canonical bindings in
design.md. Filenames SHALL derive ownership without duplicate owner fields or manual
registration. Content replacement SHALL leave canonical profiles read-only and retain existing
stable topic IDs and deterministic effects.

#### Scenario: Owned files are discovered without registration
- **WHEN** the exclusively owned files `ciaran_lareneth.yaml`、`ciaran_nireth.yaml`、`ciaran_valwyn.yaml` pass the shared static snapshot validation
- **THEN** their canonical hosts `ciaran_lareneth`、`ciaran_nireth`、`ciaran_valwyn` receive the authored greeting and the four baseline topics with original stable topic IDs through normal discovery, with no registration-list or profile edit

#### Scenario: Invalid content cannot partially replace the snapshot
- **WHEN** an owned YAML contains duplicate mapping keys, unsafe tags, unknown profile ownership, invalid schema or unresolved declaration references
- **THEN** validation rejects publication of the complete new snapshot and exposes no partially accepted replacement
