# art-subject-model Specification

## Purpose
TBD - created by archiving change art-assets. Update Purpose after archive.
## Requirements
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

### Requirement: Subject descriptions are deterministic and exclude non-physical truth
`world/art/subjects.py` (or the provider it composes) SHALL produce exactly one deterministic
description per subject from allowed immutable or validated data: the one-sentence `scene_sentence`
for scenes, the bestiary archetype description for generic monsters, and a template over
`display_name`, race/subrace, canonical age, and the entity's authored physical appearance for
characters. The description templates and the
approved-visual-style fragment SHALL be rendered from the prompt library via
`render_prompt("art.style")`, `render_prompt("art.character_description", …)`, and
`render_prompt("art.monster_description", …)` — the library is the sole source of the style
fragment and description templates, and the module SHALL NOT embed them as Python constants.
Scene descriptions SHALL continue to return the lore-owned `scene_sentence` verbatim.

The appearance contribution SHALL be read exclusively from the persona record's `appearance` block
and SHALL render its sub-keys in the declared `world/rules/persona.py::_SUBKEY_ORDER` order, so the
same entity always yields the same prompt regardless of storage iteration order. An entity with no
appearance data SHALL render an empty appearance section and produce the description it produced
before this contribution existed.

A character description SHALL NOT include any other persona key — `personality`, `life_story`,
`habit`, `background`, `identity` (public or hidden), or `social_connection` — and SHALL NOT include
secret state, mutable combat resources, or `disguised_stats` presented as physical truth. The
`PromptUnavailableError` fallback SHALL remain registry-driven and SHALL read no persona data.

#### Scenario: Character descriptions contain the appearance block and nothing else from the persona
- **WHEN** a character description is generated for a character with a full persona and a disguise
- **THEN** it contains the display name, race/subrace, canonical age, and the authored appearance sub-keys, and contains no personality, life story, habit, background, identity, or social-connection text, no combat-resource values, and no disguised stats as physical truth

#### Scenario: The hidden identity layer never reaches the prompt
- **WHEN** a character description is generated for a character whose persona declares `identity.hidden`
- **THEN** the hidden text is absent from the description, as is the public identity layer

#### Scenario: Appearance rendering is deterministic
- **WHEN** the same character's description is generated twice
- **THEN** the two results are byte-identical, with appearance sub-keys in the declared order

#### Scenario: A character with no appearance data is unchanged
- **WHEN** a character description is generated for a character whose persona has an empty appearance block
- **THEN** the appearance section is empty and the result equals the description produced before appearance was admitted

#### Scenario: Scene and monster descriptions are registry text
- **WHEN** scene and generic-monster descriptions are generated
- **THEN** they equal the immutable archetype/archetype-description text and are identical across
  regenerations for the same subject

#### Scenario: The style fragment and templates are sourced from the prompt library
- **WHEN** a character or monster description is generated
- **THEN** its style fragment and template equal `render_prompt("art.style")` and the corresponding
  `art.*` template, and the prompt-library files are the only place their text is defined

#### Scenario: Editing the style fragment surfaces a changed source hash, never a silent replacement
- **WHEN** an admin edits `art.style` or an `art.*` description template and the server restarts
- **THEN** the deterministic description changes, its source hash changes, and the art pipeline
  reports the changed hash for staff review instead of silently replacing the completed image

#### Scenario: The degraded fallback reads no persona
- **WHEN** the prompt library cannot resolve `art.character_description`
- **THEN** the fallback description is built from the display name, race label, and age only, with no persona read

### Requirement: Subject producer validation rejects unrepresentable keys
`_validate_subject_key` SHALL reject keys containing `|`, `/`, `:`, `{`, `}`, or control
characters, and keys longer than the shared 64-character maximum, so no subject can pass producer
validation and then fail the media route or the wire bounds.

#### Scenario: Slash key is rejected with a named error and no queue record
- **WHEN** a portrait subject is derived from a key containing `/`
- **THEN** the subject resolution is rejected with a named error and no queue record is created

