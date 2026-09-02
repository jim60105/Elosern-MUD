# persona-editing — Delta Spec

## ADDED Requirements

### Requirement: One deterministic service writes the four editable persona fields
A post-activation deterministic `world.rules` service function `update_persona_field(character, field, text)` SHALL be the sole writer of an active character's persona prose fields, with the module constant `PERSONA_EDITABLE_FIELDS` as the exact four-key whitelist (`background`, `personality`, `life_story`, `habit`). It SHALL trim the submitted text; a value that is null or empty after trimming SHALL remove that key (clearing a nonexistent field is a no-op success); a non-empty value longer than the shared 600-code-point persona bound SHALL be rejected deterministically without writing; the service SHALL create the import-card-shaped persona record when none exists, preserve every other persona key (including keys outside the whitelist and unknown keys) unchanged, and SHALL NOT alter traits, identity attributes, or the world clock. `update_background(character, text)` SHALL remain as a thin wrapper delegating to `update_persona_field(character, "background", text)` with the existing behaviour intact for current callers.

#### Scenario: Updating one prose field changes only that field
- **WHEN** an active character's owner submits a bounded update for any whitelisted field
- **THEN** that persona key equals the trimmed new text, every other persona key (including unknown keys and the other three prose fields) is unchanged, and no trait, identity, or clock state changes

#### Scenario: Clearing a field removes only its key
- **WHEN** the owner submits a null or whitespace-only value for a whitelisted field
- **THEN** that key is removed (or never created) and no other state changes

#### Scenario: Updating on a character without a persona record creates the card
- **WHEN** an active character has no persona record and the owner submits a bounded update
- **THEN** the service creates the import-card-shaped record with the six keys (empty containers for the non-prose keys) plus the updated key, and no other state changes

#### Scenario: An over-bound value is rejected without a write
- **WHEN** the owner submits text exceeding 600 code points after trimming
- **THEN** the service rejects it deterministically and the persona record is unchanged

#### Scenario: The background wrapper still writes only background
- **WHEN** an existing caller invokes `update_background` with new text
- **THEN** only the `background` key changes and the call is behaviourally identical to before the generalisation

### Requirement: The character.persona.update action edits one persona field
The production action registry SHALL register `character.persona.update` with a payload of exactly `field` (a member of the four-key whitelist) and `text` (a string of 1..600 code points after trimming, or null to clear). The adapter SHALL resolve the actor through the standard ownership rule (the session's own puppet, activated, exploration mode), call `update_persona_field` directly, return a confirmed success with a Traditional Chinese message and the affected `character` panel on the happy path, and return a stable rejection code for a non-whitelisted field or an over-bound text without invoking the service. Clearing a field the character never set SHALL be a confirmed no-op success. The adapter SHALL NOT assign `.db` directly and SHALL NOT route through the text command parser.

#### Scenario: A browser edit updates the panel
- **WHEN** an activated character's owner submits `character.persona.update` with `field` `life_story` and a bounded text
- **THEN** the persona record's `life_story` equals the trimmed text, the result is a confirmed success with a Traditional Chinese message, and the refreshed `character` panel renders the new value

#### Scenario: A non-whitelisted field is rejected
- **WHEN** a client submits `character.persona.update` with `field` `identity` or any value outside the whitelist
- **THEN** the dispatcher's payload validator or the adapter rejects with a stable code and the persona record is unchanged

#### Scenario: Clearing an unset field succeeds as a no-op
- **WHEN** the owner submits a null `text` for a whitelisted field the character never set
- **THEN** the result is a confirmed success and no persona key is added

### Requirement: The persona command family mirrors the action on Telnet
The `CharacterCmdSet` SHALL mount three commands in addition to the existing `設定背景`: `設定個性` (alias `個性`) for `personality`, `設定生平` (aliases `生平`, `背景故事`) for `life_story`, and `設定習慣` (alias `習慣`) for `habit`. Each SHALL replicate the existing `CmdBackground` three-part behaviour verbatim — no argument shows the current value and usage, an argument sets the field, whitespace-only clears it — and every write SHALL go through `update_persona_field`; command syntax, aliases, and availability contexts are part of the command documentation contract.

#### Scenario: Setting a field through its command
- **WHEN** an active character uses `設定生平` with bounded text
- **THEN** the persona record's `life_story` equals the trimmed text and the response confirms the change in Traditional Chinese

#### Scenario: Empty argument clears the field
- **WHEN** an active character uses `設定個性` with only whitespace as the argument
- **THEN** the `personality` key is removed and no other persona key changes

#### Scenario: Over-bound command input is refused
- **WHEN** an active character passes text exceeding the 600-code-point bound to any family command
- **THEN** the command reports the bound violation and writes nothing

### Requirement: The character drawer shows and edits the four persona sections
The browser character drawer SHALL render the persona area as four labelled sections (個性, 生平, 習慣, 背景) from the `character` panel's `persona` object, showing the localized unset placeholder for null values, and SHALL offer an inline edit affordance per section that submits exactly one `character.persona.update` action with the section's field key and the edited text (or null when cleared), then reflects the refreshed panel. The drawer SHALL NOT expose the `identity`, `appearance`, or `social_connection` persona keys.

#### Scenario: Four sections render with placeholders
- **WHEN** a character with only a `background` value opens the drawer
- **THEN** the 背景 section shows the text, the other three sections show the unset placeholder, and no structural persona key is rendered

#### Scenario: Editing a section submits one action
- **WHEN** the player edits the 習慣 section and submits
- **THEN** exactly one `character.persona.update` action carries `field` `habit` with the edited text and the refreshed drawer shows the new value without a page reload
