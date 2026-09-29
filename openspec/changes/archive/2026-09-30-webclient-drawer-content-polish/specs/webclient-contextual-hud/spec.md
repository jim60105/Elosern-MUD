## ADDED Requirements

### Requirement: Drawer art and identity match the subject
A reference drawer SHALL show the current character's portrait column only when that character is the drawer's subject: the character-status, inventory, and party drawers. The skill book, shop, quest, and world-codex drawers SHALL render no art column and no stand-in illustration, so their content takes the whole workspace width. The art column SHALL be bounded to `min(360px, 28%)` of the workspace width on a plain ink ground with no scene illustration behind the portrait; the content body keeps `min-width: 0` and remains the only scrolling region. The portrait frame SHALL show exactly one visible state line: a shown image carries its alternative-text caption, and a placeholder carries only its own label — the entry's placeholder label, else `肖像生成中` for a pending entry, `肖像生成失敗` for a failed one, `肖像載入失敗` after a failed load, and otherwise `無肖像` — so it never claims a pending portrait the payload does not carry; the placeholder initial is the character's name initial. The character-status hero SHALL name the committed character and supplied title and rank without inventing missing values.

#### Scenario: Codex is not the player
- **WHEN** the world codex or quest log opens
- **THEN** the player portrait is not presented as relevant content and the content uses the available width

#### Scenario: Character fields are unavailable
- **WHEN** the character panel lacks a rank or title
- **THEN** the header omits the missing value rather than rendering a guessed value

#### Scenario: A character drawer bounds its portrait column
- **WHEN** the character-status, inventory, or party drawer opens at a desktop viewport
- **THEN** its art column is at most `min(360px, 28%)` of the workspace width and shows one state line

#### Scenario: A missing portrait is not called pending
- **WHEN** a character drawer's portrait entry is null or carries no pending status
- **THEN** the frame's single label reads `無肖像`, not `肖像生成中`

### Requirement: Empty drawer guidance preserves unavailable reasons
An available but empty drawer list — the quest book with no rows, the world codex with nothing discovered, the bag's item section with no rows, and the party with no companions — SHALL render the shared empty guidance: a decorative registry glyph, a short headline, and one line of guidance in a solid ink frame, adding no control of its own. The empty party guidance SHALL sit above the unchanged 空位 row, which keeps the only invite control. An unavailable panel SHALL retain its authoritative registry reason and SHALL NOT be presented as merely empty, and an absent section keeps its own absence line.

#### Scenario: Empty becomes unavailable
- **WHEN** an empty quest panel is replaced by an unavailable panel
- **THEN** empty guidance is replaced by the registered reason with no invented quest/action

#### Scenario: Every empty list shares one guidance form
- **WHEN** the quest book, the codex, the bag's items, or the party is available and empty
- **THEN** each renders the shared glyph, headline, and guidance card, and the empty party additionally keeps its 空位 row

### Requirement: Lineage identity and inventory rarity use backed fields
Lineage rows with the same element/style name SHALL be distinguished using their supplied root-node display names and keep progress beside that identity: a collapsed chain row is about 56px tall and places its progress meter, at most 320px wide, immediately after an identity column shared by every row, followed by its percentage or 已全數見頂; the root-node subtitle is the first node's supplied `display_name_zh`, omitted when absent or equal to the label, and no name is derived from a skill key. Inventory rarity framing SHALL use committed presentation metadata and retain a non-colour label: each rarity draws a distinct border pattern at a width where the pattern is visible (uncommon dotted and rare dashed at 2px, epic double and legendary ridge at 3px) with a faint tint, and common and unknown items SHALL remain neutral.

#### Scenario: Same element has two lineages
- **WHEN** two chains share an element label but have distinct root-node display names
- **THEN** both root names are readable beside their own progress

#### Scenario: Unknown item has no rarity
- **WHEN** an inventory row has null presentation
- **THEN** no rarity or item-kind value is inferred from its key

## MODIFIED Requirements

### Requirement: The character-status drawer degrades section by section and never substitutes a disguise
The character-status drawer SHALL present the committed `status` panel's resources and its complete condition roster in every mode, because that panel is available in every mode; each condition SHALL pair a non-colour severity glyph with its label and every numeric or derived-modifier value the payload provides. It SHALL present the committed `character` panel's true traits, guild standing, and persona background, and SHALL mark each of those sections with the registry-owned reason when the `character` panel is unavailable — as it is outside exploration mode — rather than hiding the drawer or inventing a value. Equipment and wallet presentation belong exclusively to the inventory drawer and SHALL NOT render in character status.

Where a disguise is active the drawer SHALL render the displayed values beside the true trait rows they describe, distinctly labelled, together with the statement that a disguise affects display, registration and identification only and that combat always resolves against true values. A displayed value SHALL NEVER replace a true trait row.

The character-status drawer SHALL preserve the 親密狀態 disclosure section added by the archived intimate-status change: when the committed `character` panel's `intimate` field is present the drawer renders its collapsed-by-default disclosure widget immediately after the 偽裝 (disguise) section and before the 背景 (persona) section, and no change SHALL remove it, reorder it, or alter its disclosure widget, content, or collapsed default; like the persona area it spans the full row of the section grid. When `intimate` is `null` or the `character` panel is unavailable, the section is absent from the DOM, exactly as the merged main spec requires. This change removes only the equipment and wallet sections.

Each of the drawer's sections (vitals, traits, conditions, guild counters, disguise, intimate status, persona) SHALL carry a labelled, small-caps section heading naming what it presents, using the same heading treatment the HUD's other islands use. The vitals, traits, and guild-counter sections SHALL render each value as its own bordered card tile in an auto-fill grid of equal-width tracks rather than a plain text row, each tile only as tall as its own content, with the tile's label at the left and its `current`/`current / maximum` value in the shared numeral treatment at the right; a tile carrying more than two breakdown chips SHALL span its grid's full row so its chips wrap in one wide line; no value not already present in the committed payload (such as an effective-vs-base delta) SHALL be invented to fill the tile. The sections themselves SHALL be content-sized cards in an auto-fit grid of equal-width tracks in their DOM order, with the persona area, the intimate disclosure, and a panel-wide unavailable reason spanning the full row, so no section's height depends on another's.

The drawer body SHALL open with a hero naming the committed character: the `status` panel's actor name, its composed full title (`status` actor `full_title`), and the `character` panel's guild rank, each rendered only when the payload supplies a non-blank value and omitted — never guessed — otherwise; the name and title therefore stay in every mode, and the rank is absent while the `character` panel is unavailable. The hero SHALL carry the drawer's existing secondary openers (技能書, and 同伴 · 隊伍 while the party panel is available) in one wrapping action row, with their existing behavior. The body SHALL NOT repeat the drawer title the shared header already renders. The condition roster SHALL render as a wrapped row of rounded pill badges, one per condition, each carrying that condition's label, its visible severity word, its non-colour severity glyph, and its duration/modifier text — the same content the roster shows today, none of it dropped — coloured per severity using the same severity-to-colour mapping the capped status-island condition chips use elsewhere in the HUD. These presentation rules apply identically whether a section is fully populated or marked with a registry-owned unavailable reason.

#### Scenario: The drawer is useful in combat
- **WHEN** the committed mode is combat, so the `character` panel is unavailable
- **THEN** the drawer opens and renders the `status` resources and the complete condition roster, and marks the trait, guild and persona sections with the registry-owned reason without a wallet or equipment placeholder

#### Scenario: Conditions are never colour-only
- **WHEN** the condition roster renders a committed condition
- **THEN** it pairs a non-colour severity glyph with the condition's label and every numeric or derived-modifier value the payload provides

#### Scenario: A disguise is a comparison, not a substitution
- **WHEN** the committed `character` panel carries an active disguise with displayed values
- **THEN** the drawer renders each displayed value beside the true trait row it describes with an explicit label, states that combat resolves against true values, and shows no true row replaced by a displayed one

#### Scenario: The intimate section is preserved in place
- **WHEN** the character-status drawer renders with the `character` panel available and its `intimate` field present
- **THEN** the drawer renders the 親密狀態 disclosure collapsed by default immediately after the 偽裝 section and before the 背景 section, and this change leaves it unchanged

#### Scenario: Every section states what it is
- **WHEN** the character-status drawer renders any of its sections
- **THEN** each section carries a labelled small-caps heading naming it, matching the heading treatment used elsewhere in the HUD

#### Scenario: Vitals, traits, and guild counters render as card tiles
- **WHEN** the vitals, traits, or guild-counter sections render their rows
- **THEN** each row renders as its own bordered tile inside an auto-fill grid of equal-width tracks, only as tall as its content, showing only the label and the value already present in the committed payload, with no invented delta or base-vs-effective figure

#### Scenario: The condition roster renders as coloured pill badges
- **WHEN** the condition roster renders one or more committed conditions
- **THEN** each condition renders as a rounded pill carrying its label, its visible severity word, its severity glyph, and its duration/modifier text — with no content dropped relative to today's rendering — coloured by the same severity-to-colour mapping the capped status-island chips use, and the pills wrap onto additional lines rather than clipping or scrolling horizontally

#### Scenario: The hero names the committed character
- **WHEN** the character-status drawer opens with a `status` panel carrying an actor name and full title and an available `character` panel carrying a guild rank
- **THEN** the hero shows that name, that title and `公會階級 <rank>` above one row holding the 技能書 and 同伴 · 隊伍 openers, and the drawer title appears only in the shared header

