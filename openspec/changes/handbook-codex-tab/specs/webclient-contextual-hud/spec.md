## MODIFIED Requirements

### Requirement: Drawer art and identity match the subject
The party window and the shop window SHALL show members through the member rail portraits and SHALL render no portrait art column; a remaining reference drawer SHALL show the current character's portrait column only when that character is its subject. The skill book, shop and quest drawers SHALL render no art column and no stand-in illustration; the codex detail hero SHALL show only the entry's own art or category emblem. The status tab hero SHALL name only supplied values.

#### Scenario: The art column is bounded over plain ink
- **WHEN** a subject drawer renders its art column
- **THEN** it is bounded to `min(360px, 28%)` of the workspace width on a plain ink ground with no scene illustration behind the portrait, and the content body keeps `min-width: 0` and remains the only scrolling region

#### Scenario: The portrait frame shows exactly one state line
- **WHEN** a portrait frame renders an image or a placeholder
- **THEN** a shown image carries its alternative-text caption, and a placeholder carries only its own label — the entry's placeholder label, else `肖像生成中` for a pending entry, `肖像生成失敗` for a failed one, `肖像載入失敗` after a failed load, and otherwise `無肖像` — so it never claims a pending portrait the payload does not carry; the placeholder initial is the character's name initial

#### Scenario: Codex is not the player
- **WHEN** the world codex or quest log opens
- **THEN** the player portrait is not presented as relevant content and the content uses the available width

#### Scenario: The codex hero shows only the entry
- **WHEN** a codex entry is selected in the handbook codex tab
- **THEN** its hero renders that entry's art descriptor, or its category emblem when the entry has none, and never the player's portrait or a scene of the current room

#### Scenario: Character fields are unavailable
- **WHEN** the character panel lacks a rank or title
- **THEN** the header omits the missing value rather than rendering a guessed value

#### Scenario: A character drawer bounds its portrait column
- **WHEN** the party window opens at a desktop viewport
- **THEN** it renders no art column, each rail portrait shows one state line, and any remaining subject drawer keeps its column at most `min(360px, 28%)` of the workspace width

#### Scenario: A missing portrait is not called pending
- **WHEN** a character drawer's portrait entry is null or carries no pending status
- **THEN** the frame's single label reads `無肖像`, not `肖像生成中`

### Requirement: Empty drawer guidance preserves unavailable reasons
An available but empty list — the quest book with no rows, the world codex detail with nothing discovered (beside its placeholder wall), the party window bag tab with no rows, and the party window member rail with no companions — SHALL render the shared empty guidance: a decorative registry glyph, a short headline, and one line of guidance in a solid ink frame, adding no control of its own.

#### Scenario: The party keeps its invite row
- **WHEN** the party has no companions
- **THEN** the member tab shows the empty guidance and the rail keeps the commander entry and the 空位 entry, which keeps the only invite descriptor

#### Scenario: Unavailable is never merely empty
- **WHEN** a panel is unavailable, or a section is absent
- **THEN** an unavailable panel retains its authoritative registry reason and is not presented as merely empty, and an absent section keeps its own absence line

#### Scenario: Empty becomes unavailable
- **WHEN** an empty quest panel is replaced by an unavailable panel
- **THEN** empty guidance is replaced by the registered reason with no invented quest/action

#### Scenario: Every empty list shares one guidance form
- **WHEN** the quest book, the codex, the bag tab, or the party is available and empty
- **THEN** each renders the shared glyph, headline, and guidance card, and the empty party additionally keeps its 空位 entry
