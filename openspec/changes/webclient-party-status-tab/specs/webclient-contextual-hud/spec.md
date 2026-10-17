# Spec Delta

## REMOVED Requirements

### Requirement: The character-status drawer degrades section by section and never substitutes a disguise
**Reason**: `CharacterStatusDrawer` is deleted; the party window's 狀態 tab presents the viewed member's status from the `character` panel, which is available in every mode.
**Migration**: See `webclient-party-window` requirements "The status tab shows true values with a trait waterfall" and "The status tab shows conditions and an honest disguise".

## MODIFIED Requirements

### Requirement: Drawer art and identity match the subject
The party window and the shop window SHALL show members through the member rail portraits and SHALL render no portrait art column; a remaining reference drawer SHALL show the current character's portrait column only when that character is its subject. The skill book, shop, quest, and world-codex drawers SHALL render no art column and no stand-in illustration, so their content takes the whole workspace width. The character-status hero SHALL name the committed character and supplied title and rank without inventing missing values.

#### Scenario: The art column is bounded over plain ink
- **WHEN** a subject drawer renders its art column
- **THEN** it is bounded to `min(360px, 28%)` of the workspace width on a plain ink ground with no scene illustration behind the portrait, and the content body keeps `min-width: 0` and remains the only scrolling region

#### Scenario: The portrait frame shows exactly one state line
- **WHEN** a portrait frame renders an image or a placeholder
- **THEN** a shown image carries its alternative-text caption, and a placeholder carries only its own label — the entry's placeholder label, else `肖像生成中` for a pending entry, `肖像生成失敗` for a failed one, `肖像載入失敗` after a failed load, and otherwise `無肖像` — so it never claims a pending portrait the payload does not carry; the placeholder initial is the character's name initial

#### Scenario: Codex is not the player
- **WHEN** the world codex or quest log opens
- **THEN** the player portrait is not presented as relevant content and the content uses the available width

#### Scenario: Character fields are unavailable
- **WHEN** the character panel lacks a rank or title
- **THEN** the header omits the missing value rather than rendering a guessed value

#### Scenario: A character drawer bounds its portrait column
- **WHEN** the party window opens at a desktop viewport
- **THEN** it renders no art column, each rail portrait shows one state line, and any remaining subject drawer keeps its column at most `min(360px, 28%)` of the workspace width

#### Scenario: A missing portrait is not called pending
- **WHEN** a character drawer's portrait entry is null or carries no pending status
- **THEN** the frame's single label reads `無肖像`, not `肖像生成中`
