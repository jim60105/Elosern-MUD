# art-subject-model delta

## MODIFIED Requirements

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
