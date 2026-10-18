# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: The character drawer shows and edits the four persona sections`
- TO: `### Requirement: The party window member tab shows and edits the four persona sections`

## MODIFIED Requirements

### Requirement: The party window member tab shows and edits the four persona sections
The party window's 成員 tab SHALL render the commander's persona area as four labelled sections (個性, 生平, 習慣, 背景) from the `party_member` panel's commander `persona` section, and its 編輯人物設定 action SHALL let the player edit each section, submitting exactly one `character.persona.update` action with the section's field key and the edited text (or null when cleared), then reflect the refreshed panel.

#### Scenario: Four sections render with placeholders
- **WHEN** a commander with only a `background` value is selected on the rail
- **THEN** the 背景 section shows the text, the other three sections show the unset placeholder, and no structural persona key is rendered

#### Scenario: Editing a section submits one action
- **WHEN** the player edits the 習慣 section and submits
- **THEN** exactly one `character.persona.update` action carries `field` `habit` with the edited text and the refreshed 成員 tab shows the new value without a page reload

#### Scenario: Null persona values render the localized placeholder
- **WHEN** a persona value rendered by the 成員 tab is null
- **THEN** the tab shows the localized unset placeholder for it

#### Scenario: Structural persona keys stay hidden
- **WHEN** the 成員 tab renders the persona area
- **THEN** it does not expose the `identity`, `appearance`, or `social_connection` persona keys
