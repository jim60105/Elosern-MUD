# art-subject-model Specification

## Purpose
Defines typed, namespaced, pre-validated art subject keys (ArtSubjectKind and frozen ArtSubject with a strict parser) so no queue, store, worker, command, or presenter path ever handles a raw full-key string. Requires scene and generic-monster subjects to resolve from immutable registries, named-character portrait eligibility to be explicit policy, and subject descriptions to be deterministic and physical-truth only.

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
race/subrace, APPARENT age, and the entity's authored physical appearance for characters. A
character description SHALL be composed exclusively of the subject's visual truth; it SHALL NOT
carry the character's `display_name` or any other identity string, because a proper noun is not a
visual instruction and no checkpoint renders it. The description templates SHALL be rendered from
the prompt library via `render_prompt("art.character_description", …)` and
`render_prompt("art.monster_description", …)` — the library is the sole source of the description
templates, and the module SHALL NOT embed them as Python constants. No separate visual-style
fragment SHALL be rendered into the description: the deployment's visual style is configured
through `ART_SD_STYLES` and reaches the server as a first-class request field, so the prompt
library SHALL NOT carry an `art.style` key and the description SHALL NOT quote one. Scene
descriptions SHALL continue to return the lore-owned `scene_sentence` verbatim.

The age the character template renders SHALL be the entity's validated `apparent_age`, never its
canonical `age`. The composition seam SHALL name the value it takes `apparent_age`, so a caller
cannot pass the canonical age without the mismatch being visible at the call site. Both ages SHALL
remain validated before any prompt render or queue write; only which one reaches the prompt changes.

The appearance contribution SHALL be read exclusively from the persona record's `appearance` block
and SHALL render its sub-keys in the declared `world/rules/persona.py::_SUBKEY_ORDER` order, so the
same entity always yields the same prompt regardless of storage iteration order. An entity with no
appearance data SHALL render an empty appearance section and produce the description it produced
before this contribution existed.

A character description SHALL be composable by an explicit FIELD SELECTION. The appearance
contribution SHALL be included when, and only when, the caller selects the `appearance` field; the
existing deterministic seams SHALL select it, and a caller that selects nothing SHALL produce exactly
the description this capability produces for the unselected case. A caller MAY additionally
select one or more EQUIPMENT fields (`weapon_main`, `weapon_off`, `armor`, `accessories`), each of
which contributes the registry-owned `ItemPresentation` visual text of the items currently occupying
that slot, read read-only from `world/lore/items.py`; an empty slot and an item key absent from the
registry contribute nothing. A caller MAY additionally supply bounded free-form text, which SHALL be
appended verbatim after every selected field's contribution. Field selection SHALL NOT change the
description produced for any unselected field, and the same entity, the same selection, and the same
free text SHALL always produce byte-identical output.

A character description SHALL NOT include any other persona key — `personality`, `life_story`,
`habit`, `background`, `identity` (public or hidden), or `social_connection` — and SHALL NOT include
secret state, mutable combat resources, or `disguised_stats` presented as physical truth. The
`PromptUnavailableError` fallback SHALL remain registry-driven, SHALL read no persona data, and
SHALL likewise carry no display name — the degraded path SHALL NOT reintroduce what the template
removed.

#### Scenario: Character descriptions contain the appearance block and nothing else from the persona
- **WHEN** a character description is generated for a character with a full persona and a disguise
- **THEN** it contains the race/subrace label, the apparent age, and the authored appearance sub-keys, and contains no display name, no personality, life story, habit, background, identity, or social-connection text, no combat-resource values, and no disguised stats as physical truth

#### Scenario: The rendered age is the apparent age
- **WHEN** a character description is generated for a character whose canonical age and apparent age differ
- **THEN** the rendered age equals the apparent age, the canonical age appears nowhere in the description, and a character whose two ages are equal renders the same value either way

#### Scenario: The hidden identity layer never reaches the prompt
- **WHEN** a character description is generated for a character whose persona declares `identity.hidden`
- **THEN** the hidden text is absent from the description, as is the public identity layer

#### Scenario: Appearance rendering is deterministic
- **WHEN** the same character's description is generated twice
- **THEN** the two results are byte-identical, with appearance sub-keys in the declared order

#### Scenario: A character with no appearance data is unchanged
- **WHEN** a character description is generated for a character whose persona has an empty appearance block
- **THEN** the appearance section is empty and the result is the bare template stem with no dangling separator

#### Scenario: Scene and monster descriptions are registry text
- **WHEN** scene and generic-monster descriptions are generated
- **THEN** they equal the immutable archetype/archetype-description text and are identical across
  regenerations for the same subject

#### Scenario: The style fragment and templates are sourced from the prompt library
- **WHEN** a character or monster description is generated, and the shipped prompt library is enumerated
- **THEN** the description equals the corresponding `art.*` template render, the prompt-library files are the only place that text is defined, and the library carries no `art.style` key for any code path to render

#### Scenario: Editing the style fragment surfaces a changed source hash, never a silent replacement
- **WHEN** an admin edits an `art.*` description template and the server restarts
- **THEN** the deterministic description changes, its source hash changes, and the art pipeline
  reports the changed hash for staff review instead of silently replacing the completed image

#### Scenario: The degraded fallback reads no persona
- **WHEN** the prompt library cannot resolve `art.character_description`
- **THEN** the fallback description is built from the race label and the apparent age only, with no persona read and no display name

#### Scenario: An unselected appearance field reproduces the pre-appearance description
- **WHEN** a character description is generated with no field selected
- **THEN** the appearance section is empty and the result equals the description for the same character with an empty persona

#### Scenario: Selected equipment fields contribute registry visual text only
- **WHEN** a character description is generated with `armor` and `accessories` selected for a character wearing registered items
- **THEN** it contains those items' registry `ItemPresentation` visual text, contains nothing from the unselected weapon slots, and contains no item mechanics, stat, or price data

#### Scenario: Empty and unregistered slots contribute nothing
- **WHEN** a character description is generated with an equipment field selected for an empty slot, or for a slot holding an item key absent from the item registry
- **THEN** that field contributes no text and the description is otherwise unchanged

#### Scenario: Free-form text is appended verbatim and bounded
- **WHEN** a character description is generated with bounded free-form text supplied
- **THEN** the text appears verbatim after the selected field contributions, and text exceeding the bound or carrying control characters is rejected before any render

#### Scenario: The same selection is byte-identical across generations
- **WHEN** the same character's description is generated twice with the same field selection and free text
- **THEN** the two results are byte-identical, with fields in the declared order

### Requirement: Subject producer validation rejects unrepresentable keys
`_validate_subject_key` SHALL reject keys containing `|`, `/`, `:`, `{`, `}`, or control
characters, and keys longer than the shared 64-character maximum, so no subject can pass producer
validation and then fail the media route or the wire bounds.

#### Scenario: Slash key is rejected with a named error and no queue record
- **WHEN** a portrait subject is derived from a key containing `/`
- **THEN** the subject resolution is rejected with a named error and no queue record is created
