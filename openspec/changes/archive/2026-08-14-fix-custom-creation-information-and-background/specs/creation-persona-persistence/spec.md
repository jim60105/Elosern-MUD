## MODIFIED Requirements

### Requirement: Activation persists the persona block in the import-card shape
When the draft carries a persona block, `activate_player_character()` SHALL write
`entity.db.persona` as a dict with the import-card keys
(identity/personality/life_story/habit/appearance/social_connection), the block filling the three
prose fields and the remaining keys stored as empty containers, inside the same all-or-nothing
activation transaction; a persona write failure SHALL roll back activation, and a draft without a
persona block SHALL write nothing. When the draft carries a player-authored bounded background
field, the same activation transaction SHALL additionally store that text under the persona
record's `background` key (kept separate from the three prose fields), so a custom character's
background survives activation; a draft without a background SHALL omit the key. `world/rules/
character_creation.py` SHALL be the sole writer of creation-generated persona; `world/imports/
loader.py` remains the import-time writer and is unchanged.

#### Scenario: A concept draft persists its persona at activation
- **WHEN** a pending character activates with a draft carrying a persona block
- **THEN** `entity.db.persona` contains the six-key import-card dict with the block's three prose
  fields and empty containers for the rest, activation commits, and the character is an active
  persona owner

#### Scenario: A custom background is persisted inside the persona record
- **WHEN** a pending character activates with a custom draft carrying a non-empty bounded
  `background`
- **THEN** `entity.db.persona` contains the six import-card keys plus a `background` key holding the
  exact accepted text, activation commits, and the character is an active persona owner

#### Scenario: A persona write failure rolls back activation
- **WHEN** a write failure is injected into the persona-persistence step of the activation
  transaction
- **THEN** activation rolls back entirely, the character remains pending, and no canonical
  identity, trait, or persona state is written

#### Scenario: A draft without persona or background writes nothing
- **WHEN** a pending character activates with a draft that has no persona block and no background
- **THEN** `entity.db.persona` remains absent and activation behaves exactly as before

## ADDED Requirements

### Requirement: The owner can freely update the background after activation
A post-activation deterministic `world.rules` service SHALL be the sole writer of an active
character's persona `background` field. It SHALL accept a bounded text value (an empty value
explicitly clears the field by removing the key), validate the bound deterministically, create the
import-card-shaped persona record when none exists, preserve every existing persona key (including
unknown keys) while writing or clearing only `background`, and SHALL NOT alter traits, identity
attributes, the three prose fields, or the world clock.

#### Scenario: Updating the background changes only that field
- **WHEN** an active character's owner submits a bounded background update
- **THEN** `entity.db.persona["background"]` equals the new text, the six import-card keys (and any
  prose fields) are unchanged, and no trait, identity, or clock state changes

#### Scenario: Clearing the background removes the key
- **WHEN** an active character's owner submits an empty background update
- **THEN** the persona record's `background` key is removed (or never created) and no other state
  changes

#### Scenario: Updating on a character without a persona record creates the card
- **WHEN** an active character has no persona record and the owner submits a bounded background
- **THEN** the service creates the import-card-shaped record with the six keys (empty containers
  for the non-prose keys) and the `background` key, and no other state changes

### Requirement: The background survives the draft, concept, custom-save, and activation journey
The `background` SHALL be a first-class custom-draft field: `save_custom_draft` validates and
stores it, the draft normalizer accepts it with its bound and includes it in the draft fingerprint,
and the concept-apply service SHALL NOT overwrite it. Activation SHALL merge the background into the
persona record together with any concept persona block — the six import-card keys are written first,
then `background` when the draft carries one — inside the same all-or-nothing transaction.

#### Scenario: A background persists through every entry order
- **WHEN** a background is entered alone (no concept), then a concept is applied, then a custom
  save follows, and finally activation commits
- **THEN** `entity.db.persona["background"]` equals the entered text at every step and after
  activation, and the concept persona block is also present when the concept's race matches
