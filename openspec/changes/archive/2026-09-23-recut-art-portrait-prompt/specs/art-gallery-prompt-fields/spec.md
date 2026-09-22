# art-gallery-prompt-fields delta

## MODIFIED Requirements

### Requirement: The prompt library remains the sole source of the composed template
The `{equipment}` and `{custom}` sections SHALL be slots of the `art.character_description` template
in `prompts/art.yaml`, declared in the `art.character_description` `PromptSpec`'s
`allowed_placeholders`; `world/art/` SHALL NOT embed their surrounding text as Python constants. The
declared placeholder set SHALL be exactly `race`, `age`, `appearance`, `equipment`, and `custom`: a
template naming a placeholder outside that set, and a render passing a value the set does not
declare, SHALL both fail at the library boundary, so a removed slot cannot be reintroduced by an
edit on one side alone. When the prompt library cannot resolve the template, the existing
registry-driven fallback SHALL be used unchanged in kind: it reads no persona, no equipment, and no
free text, and it carries the race label and the apparent age only — never the display name.

#### Scenario: The template owns every section's surrounding text
- **WHEN** the composed character description is generated
- **THEN** its appearance, equipment, and free-text sections are rendered from the `art.character_description` template, and no surrounding text is defined in Python

#### Scenario: The declared placeholder set is closed on both sides
- **WHEN** the shipped `art.character_description` template and its declared `allowed_placeholders` are compared
- **THEN** both name exactly `race`, `age`, `appearance`, `equipment`, and `custom`, and neither declares `name` or `style`

#### Scenario: A broken library key degrades without reading equipment
- **WHEN** the prompt library cannot resolve `art.character_description`
- **THEN** the fallback description is built from the race label and the apparent age only, with no persona, equipment, or free-text read, and with no display name
