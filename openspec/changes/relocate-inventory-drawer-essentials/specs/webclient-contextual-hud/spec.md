## MODIFIED Requirements

### Requirement: The bag renders the bounded inventory rows without inventing a total or a rarity
The bag drawer SHALL use the shared drawer chrome for the `背包 · 裝備` title, local `inventory` SVG icon, close control, and a wallet subtitle formatted as integer copper from the committed available `character` panel. It SHALL render that wallet in no other body location. Its available body SHALL begin with the read-only equipment doll built from the committed `character` panel's equipment rows, followed by the committed `services` panel's inventory rows — each row's display name, held count and whether it is equipped — and nothing else. The listing SHALL be bounded by the server's row ceiling; when it holds that many rows the drawer SHALL state the ceiling in words. The shipped row count SHALL NOT be presented as a count of the player's untruncated holdings, because the panel's inventory total is that same shipped count and carries no information about what was truncated.

The bag SHALL NOT render an item rarity, a per-item statistics line, a comparison tooltip, or a numeric item mechanic in this change. It SHALL NOT render a use, consume or equip control, because the panel advertises no such action. When the `services` panel commits its unavailable form, or when its inventory section is absent, the bag SHALL render only the registry-owned reason and SHALL fabricate no wallet, equipment slot, row or count. When services are available but the character panel is unavailable, the held-item listing remains available, the doll renders its registered unavailable state, and the drawer header renders no balance.

#### Scenario: The bag lists what the payload carries
- **WHEN** the committed `services` panel carries inventory rows and the committed character panel is available
- **THEN** each row renders its display name, its held count and an equipped marker where the row is equipped, the body begins with the true equipment doll, and no rarity, statistic or tooltip is rendered for it

#### Scenario: The inventory drawer owns the equipment and wallet context
- **WHEN** the inventory drawer opens with available services and character panels
- **THEN** its shared header shows the local bag symbol and thousands-grouped character wallet, its body contains the equipment doll, and the character-status drawer contains neither a wallet figure nor equipment doll

#### Scenario: The ceiling is stated, the total is not invented
- **WHEN** the inventory listing holds the server's maximum number of rows
- **THEN** the drawer states that the listing is bounded at that maximum, and it never renders a figure claiming to be the player's complete holdings

#### Scenario: No use or equip control appears
- **WHEN** the bag renders a held item, whether equipped or not
- **THEN** it offers no use, consume or equip control, matching the panel's action set

#### Scenario: An unavailable services panel fabricates nothing
- **WHEN** the `services` panel commits its unavailable form
- **THEN** the bag renders only the registry-owned reason message, with no rows, wallet, equipment slot or count

#### Scenario: Character unavailability does not fabricate a balance or equipment
- **WHEN** the services inventory is available and the character panel is unavailable
- **THEN** the bag renders its held rows, renders the equipment section's registered unavailable reason, and shows no wallet subtitle or zero balance

### Requirement: The character-status drawer degrades section by section and never substitutes a disguise
The character-status drawer SHALL present the committed `status` panel's resources and its complete condition roster in every mode, because that panel is available in every mode; each condition SHALL pair a non-colour severity glyph with its label and every numeric or derived-modifier value the payload provides. It SHALL present the committed `character` panel's true traits, guild standing, and persona background, and SHALL mark each of those sections with the registry-owned reason when the `character` panel is unavailable — as it is outside exploration mode — rather than hiding the drawer or inventing a value. Equipment and wallet presentation belong exclusively to the inventory drawer and SHALL NOT render in character status.

Where a disguise is active the drawer SHALL render the displayed values beside the true trait rows they describe, distinctly labelled, together with the statement that a disguise affects display, registration and identification only and that combat always resolves against true values. A displayed value SHALL NEVER replace a true trait row.

The intimate and adult state block the design draft shows in this drawer SHALL be absent: no arousal, wetness, shame, exposure, climax-phase, per-part sensitivity or virginity element, and no placeholder standing in for one, because no committed panel carries such a field.

Each of the drawer's sections (vitals, traits, conditions, guild counters, disguise, persona) SHALL carry a labelled, small-caps section heading naming what it presents, using the same heading treatment the HUD's other islands use. The vitals, traits, and guild-counter sections SHALL render each value as its own bordered card tile in a two-column grid rather than a plain text row, with the tile's label at the left and its `current`/`current / maximum` value in the shared numeral treatment at the right; no value not already present in the committed payload (such as an effective-vs-base delta) SHALL be invented to fill the tile. The condition roster SHALL render as a wrapped row of rounded pill badges, one per condition, each carrying that condition's label, its visible severity word, its non-colour severity glyph, and its duration/modifier text — the same content the roster shows today, none of it dropped — coloured per severity using the same severity-to-colour mapping the capped status-island condition chips use elsewhere in the HUD. These presentation rules apply identically whether a section is fully populated or marked with a registry-owned unavailable reason.

#### Scenario: The drawer is useful in combat
- **WHEN** the committed mode is combat, so the `character` panel is unavailable
- **THEN** the drawer opens and renders the `status` resources and the complete condition roster, and marks the trait, guild and persona sections with the registry-owned reason without a wallet or equipment placeholder

#### Scenario: Conditions are never colour-only
- **WHEN** the condition roster renders a committed condition
- **THEN** it pairs a non-colour severity glyph with the condition's label and every numeric or derived-modifier value the payload provides

#### Scenario: A disguise is a comparison, not a substitution
- **WHEN** the committed `character` panel carries an active disguise with displayed values
- **THEN** the drawer renders each displayed value beside the true trait row it describes with an explicit label, states that combat resolves against true values, and shows no true row replaced by a displayed one

#### Scenario: The intimate block is absent
- **WHEN** the character-status drawer renders in any mode
- **THEN** no arousal, wetness, shame, exposure, climax-phase, sensitivity or virginity element is present and no placeholder stands in for one

#### Scenario: Every section states what it is
- **WHEN** the character-status drawer renders any of its sections
- **THEN** each section carries a labelled small-caps heading naming it, matching the heading treatment used elsewhere in the HUD

#### Scenario: Vitals, traits, and guild counters render as card tiles
- **WHEN** the vitals, traits, or guild-counter sections render their rows
- **THEN** each row renders as its own bordered tile inside a two-column grid, showing only the label and the value already present in the committed payload, with no invented delta or base-vs-effective figure

#### Scenario: The condition roster renders as coloured pill badges
- **WHEN** the condition roster renders one or more committed conditions
- **THEN** each condition renders as a rounded pill carrying its label, its visible severity word, its severity glyph, and its duration/modifier text — with no content dropped relative to today's rendering — coloured by the same severity-to-colour mapping the capped status-island chips use, and the pills wrap onto additional lines rather than clipping or scrolling horizontally

### Requirement: The drawer layer renders the wallet exactly once
Across every drawer, the player's wallet SHALL be rendered in exactly one place — the inventory drawer's shared header — and SHALL be read from the committed available character panel that owns it. The shop, the lore reference, the inventory body, and the character-status drawer SHALL NOT render a balance of their own. A drawer that cannot read the wallet from an available character panel SHALL render no balance at all rather than a zero.

#### Scenario: One wallet across the whole drawer layer
- **WHEN** every drawer is opened in turn with the `services` and `character` panels available
- **THEN** exactly one wallet value is rendered across all of them, in the inventory drawer header

#### Scenario: An unavailable panel renders no balance
- **WHEN** the character panel that carries the wallet is unavailable
- **THEN** no drawer renders a balance, and none renders a zero in its place
