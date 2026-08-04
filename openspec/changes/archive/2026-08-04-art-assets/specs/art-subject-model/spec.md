## Purpose

Namespaced art subject identity — `scene:<archetype>`, `portrait:character:<stable-key>`,
`portrait:monster:<archetype>` — with typed prefix/key storage, validation before any queue access,
the explicit named-character portrait-policy rule (eligibility is metadata, never inferred), and
deterministic adult-safe subject descriptions.

## ADDED Requirements

### Requirement: Art subject keys are typed, namespaced, and validated before queue access
`world/art/subjects.py` SHALL define `ArtSubjectKind` (`scene`, `portrait:character`,
`portrait:monster`) and a frozen `ArtSubject(kind, key)` whose serialized full key is
`<kind>:<key>`. `parse_subject(full_key)` SHALL return an `ArtSubject` for a full key whose prefix is
one of the three known kinds and whose subject key is non-empty, free of `:`, and free of control
characters; anything else SHALL raise a named `ArtSubjectError`. No queue, store, worker, command, or
presenter function SHALL accept a raw full-key string; every access path SHALL go through a parsed
`ArtSubject`.

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

### Requirement: Scene and generic-monster subjects resolve from immutable registries
A scene subject SHALL re-validate its archetype against `SCENE_ARCHETYPE_REGISTRY`; a monster subject
SHALL re-validate its archetype against `MONSTER_TIER_REGISTRY`. An unresolvable registry key SHALL
raise a named `ArtSubjectError` and produce no record.

#### Scenario: A registered archetype yields a valid scene subject
- **WHEN** a room carries `scene_archetype = "tavern_interior"` and that key exists in the registry
- **THEN** the subject resolves to `scene:tavern_interior`

#### Scenario: An unknown archetype is rejected
- **WHEN** a room's `scene_archetype` or a forged monster subject names a key absent from the
  registries
- **THEN** resolution raises a named `ArtSubjectError` and no asset record is created

### Requirement: Named-character portrait eligibility is explicit policy, never inferred
`world/art/subjects.py` SHALL derive a `portrait:character` subject only from an explicit
`portrait_policy` attribute whose value is `{"mode": "named", "stable_key": "<key>"}` on the
character. `None` or `{"mode": "generic"}` SHALL produce no unique portrait. Eligibility SHALL NOT be
inferred from display-name capitalization or uniqueness, quest role, database key shape, or whether an
LLM wrote the NPC.

#### Scenario: An explicit named policy yields a unique portrait subject
- **WHEN** a player or imported NPC carries the explicit named policy with a stable key
- **THEN** its subject is `portrait:character:<stable_key>` and is unique to that character

#### Scenario: Characters without a named policy get no unique portrait
- **WHEN** a role-based scene NPC carries `None` and another character carries `{"mode": "generic"}`
- **THEN** neither resolves to a unique portrait subject

#### Scenario: Eligibility is not inferred from display-name uniqueness
- **WHEN** two characters share the same display name but only one carries an explicit named policy
- **THEN** only the policy-bearing character resolves to a unique portrait subject

### Requirement: Subject descriptions are deterministic, adult-safe, and exclude non-physical truth
`world/art/subjects.py` (or the provider it composes) SHALL produce exactly one deterministic
description per subject from allowed immutable or validated data: the one-sentence `scene_sentence`
for scenes, the bestiary archetype description for generic monsters, and a template over
`display_name`, race/subrace, and adult age for characters. A character description SHALL NOT include
persona text, secret state, mutable combat resources, or `disguised_stats` presented as physical
truth.

#### Scenario: Character descriptions contain only allowed stable data
- **WHEN** a character description is generated for a character with a persona and a disguise
- **THEN** it contains the display name, race/subrace, and adult age but no persona content, no
  combat-resource values, and no disguised stats as physical truth

#### Scenario: Scene and monster descriptions are registry text
- **WHEN** scene and generic-monster descriptions are generated
- **THEN** they equal the immutable archetype/archetype-description text and are identical across
  regenerations for the same subject
