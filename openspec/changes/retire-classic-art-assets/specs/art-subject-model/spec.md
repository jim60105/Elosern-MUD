## MODIFIED Requirements

### Requirement: Art subject keys are typed, namespaced, and validated before queue access
Art accesses SHALL use frozen parsed subject identities with the existing scene, portrait:character and portrait:monster namespaces. Queue jobs and gallery cards SHALL retain those identities. No fixed subject-output identity or subject-keyed classic record SHALL be produced; invalid raw keys SHALL reject before any access.

#### Scenario: Known kinds parse into typed subjects
- **WHEN** `scene:forest_path`, `portrait:character:42`, and `portrait:monster:gray_wolf` are parsed
- **THEN** each returns the typed subject with the correct kind and un-prefixed key, and the full key
  round-trips unchanged

#### Scenario: Malformed keys are rejected before any queue access
- **WHEN** an empty key, a subject key containing `:`, a subject key containing a control character, or
  an unknown prefix is parsed
- **THEN** a named `ArtSubjectError` is raised and no queue or store record is touched

#### Scenario: A subject cannot change kind while keeping the same full key
- **WHEN** a scene subject and a character subject would serialize to the same full string
- **THEN** they serialize to different strings (`scene:<k>` vs `portrait:character:<k>`), so a
  record keyed by one can never be read or overwritten as the other

#### Scenario: parse_subject is the gate between full-key strings and typed subjects
- **WHEN** `parse_subject(full_key)` is called
- **THEN** it returns an `ArtSubject` for a full key whose prefix is one of the three known kinds and whose subject key is non-empty, free of `:`, and free of control characters
- **AND** anything else raises a named `ArtSubjectError`
