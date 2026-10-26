# Spec Delta

## Purpose

Authored dialogue for the middle-exchange hosts is published through automatically discovered
`world/lore/dialogue/content/<NpcProfile.key>.yaml` files. This slice owns only its own YAML
files plus one human review document; editorial quality (voice, source fidelity, register) is
reviewed there and is deliberately not asserted by a test.

## ADDED Requirements

### Requirement: middle-exchange content has exclusive profile-key YAML ownership
The owned hosts SHALL obtain rewritten topics and greetings from automatically discovered `world/lore/dialogue/content/<NpcProfile.key>.yaml` files using the exact canonical bindings in design.md. Filenames SHALL derive ownership without duplicate owner fields or manual registration. Content replacement SHALL leave canonical profiles read-only and retain existing stable topic IDs and deterministic effects.

#### Scenario: Owned files are discovered without registration
- **WHEN** all exclusively owned YAML files pass the shared static snapshot validation
- **THEN** each canonical host receives its rewritten greeting and four baseline topics with original stable topic IDs through normal discovery, with no registration-list or profile edit

#### Scenario: Invalid content cannot partially replace the snapshot
- **WHEN** an owned YAML contains duplicate mapping keys, unsafe tags, unknown profile ownership, invalid schema or unresolved declaration references
- **THEN** validation rejects publication of the complete new snapshot and exposes no partially accepted replacement
