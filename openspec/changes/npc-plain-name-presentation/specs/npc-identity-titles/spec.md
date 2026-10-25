# Spec Delta

## ADDED Requirements

### Requirement: Every NPC identity surface uses the plain authored name
NPC text, exploration, dialogue, party, inspection, skill targeting and management identity surfaces SHALL render the plain authored name without reading or composing an independent title. Historical title attributes SHALL remain inert; player title presentation SHALL remain unchanged.

#### Scenario: All identity surfaces ignore historical titles
- **WHEN** a real NPC carries title sentinel data or a raising title accessor
- **THEN** room/look/dialogue/party/editor/GM surfaces retain plain names without accessing it

#### Scenario: No identity replacement
- **WHEN** an NPC title is removed from a display
- **THEN** the old title is not merged into name, description or a replacement role field

## MODIFIED Requirements

### Requirement: The NPC dialogue context carries the title as read-only data
NPC dialogue context SHALL carry name, description and location without an independent title field. Player title context SHALL remain unchanged.

#### Scenario: NPC context omits independent title
- **WHEN** an NPC with historical title attributes builds dialogue context
- **THEN** the context neither reads nor includes that title

#### Scenario: Player context preserves title
- **WHEN** a player with an equipped title builds its existing context
- **THEN** its current title information is unchanged

#### Scenario: A titled NPC exposes its title to the dialogue context
- **WHEN** an NPC with historical title data builds context
- **THEN** the title is neither read nor emitted; ordinary name/description/location remain

#### Scenario: An untitled NPC exposes an empty title and an unchanged prompt
- **WHEN** an NPC without title data builds context
- **THEN** the same title-free context is emitted without creating an attribute

### Requirement: Command and search targeting matches the plain NPC key only

Player command and object-search targeting SHALL continue to resolve NPCs by their plain `key`. The title SHALL NOT be written into the key, registered as an alias, or added to any search index, so a player never has to type a title to address an NPC.

#### Scenario: The plain name still resolves a titled NPC

- **WHEN** a player targets a titled NPC by its plain name through an ordinary object search
- **THEN** the NPC resolves exactly as it did before the title existed

#### Scenario: The composed full identity is not a search key

- **WHEN** a player searches for the composed 「姓名　稱號」 string
- **THEN** the search does not resolve the NPC through that composed string

#### Scenario: Composed member aliases are removed
- **WHEN** a member is targeted with an old name-plus-title token rather than its current key/dbref
- **THEN** no composed-name alias matches and existing ambiguity rules still apply

## REMOVED Requirements

### Requirement: A single deterministic composer renders the NPC full identity
**Reason**: Independent NPC titles and composed-name presentation are removed.
**Migration**: Render the plain authored NPC key with existing surface bounds; player titles stay unchanged.

### Requirement: Full identity appears only on opt-in text display surfaces
**Reason**: Independent NPC titles and composed-name presentation are removed.
**Migration**: Render the plain authored NPC key with existing surface bounds; player titles stay unchanged.

### Requirement: The webclient exploration panel renders the NPC full identity on entity and interact rows
**Reason**: Independent NPC titles and composed-name presentation are removed.
**Migration**: Render the plain authored NPC key with existing surface bounds; player titles stay unchanged.

### Requirement: Compact presentation rows keep the plain NPC name
**Reason**: Independent NPC titles and composed-name presentation are removed.
**Migration**: Render the plain authored NPC key with existing surface bounds; player titles stay unchanged.
