## MODIFIED Requirements

### Requirement: Subject descriptions are deterministic, adult-safe, and exclude non-physical truth
`world/art/subjects.py` (or the provider it composes) SHALL produce exactly one deterministic
description per subject from allowed immutable or validated data: the one-sentence `scene_sentence`
for scenes, the bestiary archetype description for generic monsters, and a template over
`display_name`, race/subrace, and adult age for characters. The description templates and the
approved-visual-style fragment SHALL be rendered from the prompt library via
`render_prompt("art.style")`, `render_prompt("art.character_description", …)`, and
`render_prompt("art.monster_description", …)` — the library is the sole source of the style
fragment and description templates, and the module SHALL NOT embed them as Python constants.
Scene descriptions SHALL continue to return the lore-owned `scene_sentence` verbatim. A character
description SHALL NOT include persona text, secret state, mutable combat resources, or
`disguised_stats` presented as physical truth.

#### Scenario: Character descriptions contain only allowed stable data
- **WHEN** a character description is generated for a character with a persona and a disguise
- **THEN** it contains the display name, race/subrace, and adult age but no persona content, no
  combat-resource values, and no disguised stats as physical truth

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
