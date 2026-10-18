# Spec Delta

## MODIFIED Requirements

### Requirement: The character drawer shows and edits the four persona sections
The browser character drawer SHALL render the persona area as four labelled sections (個性, 生平, 習慣, 背景) from the `party_member` panel's commander `persona` section, and SHALL offer an inline edit affordance per section that submits exactly one `character.persona.update` action with the section's field key and the edited text (or null when cleared), then reflects the refreshed panel.

#### Scenario: Four sections render with placeholders
- **WHEN** a character with only a `background` value opens the drawer
- **THEN** the 背景 section shows the text, the other three sections show the unset placeholder, and no structural persona key is rendered

#### Scenario: Editing a section submits one action
- **WHEN** the player edits the 習慣 section and submits
- **THEN** exactly one `character.persona.update` action carries `field` `habit` with the edited text and the refreshed drawer shows the new value without a page reload

#### Scenario: Null persona values render the localized placeholder
- **WHEN** a persona value rendered by the drawer is null
- **THEN** the drawer shows the localized unset placeholder for it

#### Scenario: Structural persona keys stay hidden
- **WHEN** the drawer renders the persona area
- **THEN** it does not expose the `identity`, `appearance`, or `social_connection` persona keys

### Requirement: The character.persona.update action edits one persona field
The production action registry SHALL register `character.persona.update` with a payload of exactly `field` (a member of the four-key whitelist) and `text` (a string of 1..600 code points after trimming, or null to clear). The adapter SHALL resolve the actor through the standard ownership rule (the session's own puppet, activated, exploration mode) and call `update_persona_field` directly.

#### Scenario: A browser edit updates the panel
- **WHEN** an activated character's owner submits `character.persona.update` with `field` `life_story` and a bounded text
- **THEN** the persona record's `life_story` equals the trimmed text, the result is a confirmed success with a Traditional Chinese message, and the refreshed `party_member` panel's commander section renders the new value

#### Scenario: A non-whitelisted field is rejected
- **WHEN** a client submits `character.persona.update` with `field` `identity` or any value outside the whitelist
- **THEN** the dispatcher's payload validator or the adapter rejects with a stable code and the persona record is unchanged

#### Scenario: Clearing an unset field succeeds as a no-op
- **WHEN** the owner submits a null `text` for a whitelisted field the character never set
- **THEN** the result is a confirmed success and no persona key is added

#### Scenario: Invalid payloads reject with a stable code before the service
- **WHEN** the submitted `field` is non-whitelisted or the `text` is over-bound
- **THEN** the adapter returns a stable rejection code without invoking the service

#### Scenario: The adapter writes no state directly and bypasses no parser
- **WHEN** the adapter handles a `character.persona.update` submission
- **THEN** it does not assign `.db` directly and does not route through the text command parser
