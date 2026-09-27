## ADDED Requirements

### Requirement: Drawer art and identity match the subject
A drawer SHALL show decorative portrait art only when it represents that drawer subject. Character status SHALL name the committed character and supplied rank/title without inventing missing values. Repeated art-state labels SHALL be consolidated into one readable status.

#### Scenario: Codex is not the player
- **WHEN** the world codex or quest log opens
- **THEN** the player portrait is not presented as relevant content and the content uses the available width

#### Scenario: Character fields are unavailable
- **WHEN** the character panel lacks a rank or title
- **THEN** the header omits the missing value rather than rendering a guessed value

### Requirement: Empty drawer guidance preserves unavailable reasons
An available empty drawer list SHALL show a consistent headline and guidance; an unavailable panel SHALL retain its authoritative reason and SHALL NOT be presented as merely empty.

#### Scenario: Empty becomes unavailable
- **WHEN** an empty quest panel is replaced by an unavailable panel
- **THEN** empty guidance is replaced by the registered reason with no invented quest/action

### Requirement: Lineage identity and inventory rarity use backed fields
Lineage rows with the same element/style name SHALL be distinguished using their supplied root-node display names and keep progress beside that identity. Inventory rarity framing SHALL use committed presentation metadata and retain a non-colour label; unknown items SHALL remain neutral.

#### Scenario: Same element has two lineages
- **WHEN** two chains share an element label but have distinct root-node display names
- **THEN** both root names are readable beside their own progress

#### Scenario: Unknown item has no rarity
- **WHEN** an inventory row has null presentation
- **THEN** no rarity or item-kind value is inferred from its key
