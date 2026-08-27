## MODIFIED Requirements

### Requirement: The character-status drawer degrades section by section and never substitutes a disguise
The character-status drawer SHALL present the committed `status` panel's resources and its complete
condition roster in every mode, because that panel is available in every mode; each condition SHALL
pair a non-colour severity glyph with its label and every numeric or derived-modifier value the
payload provides. It SHALL present the committed `character` panel's true traits, equipment, guild
standing, wallet and persona background, and SHALL mark each of those sections with the registry-owned
reason when the `character` panel is unavailable — as it is outside exploration mode — rather than
hiding the drawer or inventing a value.

Where a disguise is active the drawer SHALL render the displayed values beside the true trait rows
they describe, distinctly labelled, together with the statement that a disguise affects display,
registration and identification only and that combat always resolves against true values. A displayed
value SHALL NEVER replace a true trait row.

The intimate and adult state block the design draft shows in this drawer SHALL be absent: no arousal,
wetness, shame, exposure, climax-phase, per-part sensitivity or virginity element, and no placeholder
standing in for one, because no committed panel carries such a field.

Each of the drawer's sections (vitals, traits, conditions, guild counters, disguise, persona) SHALL carry
a labelled, small-caps section heading naming what it presents, using the same heading treatment the
HUD's other islands use. The vitals, traits, and guild-counter sections SHALL render each value as its
own bordered card tile in a two-column grid rather than a plain text row, with the tile's label at the
left and its `current`/`current / maximum` value in the shared numeral treatment at the right; no
value not already present in the committed payload (such as an effective-vs-base delta) SHALL be
invented to fill the tile. The condition roster SHALL render as a wrapped row of rounded pill badges,
one per condition, each carrying that condition's label, its visible severity word, its non-colour
severity glyph, and its duration/modifier text — the same content the roster shows today, none of it
dropped — coloured per severity using the same severity-to-colour mapping the capped status-island
condition chips use elsewhere in the HUD. These presentation rules apply identically
whether a section is fully populated or marked with a registry-owned unavailable reason.

The drawer's main sections SHALL render in the order 生命量 (vitals) → 屬性 (traits) → 計數・公會
(guild counters) → 狀態 (conditions) → 偽裝 (disguise), matching the design draft's `#dr-status`
section order. The `屬性` section SHALL render exactly the `character.traits` rows whose `key` is
`atk_phys`, `agility`, `defense`, or `magic_level`, in that order, and SHALL NOT render any `traits`
row whose value is already presented by the vitals section (`hp`, `mp`, `sp`) or the guild-counter
section (`guild_merit`), so each quantity the drawer presents appears in exactly one section.

#### Scenario: The drawer is useful in combat
- **WHEN** the committed mode is combat, so the `character` panel is unavailable
- **THEN** the drawer opens and renders the `status` resources and the complete condition roster, and marks the trait, equipment, guild, wallet and persona sections with the registry-owned reason

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

#### Scenario: Sections render in design order
- **WHEN** the character-status drawer renders with both `status` and `character` available
- **THEN** the vitals section renders before the traits section, the traits section renders before the guild-counter section, the guild-counter section renders before the condition roster, and the condition roster renders before the disguise section

#### Scenario: Traits never repeat a vitals or guild-counter value
- **WHEN** `character.traits` contains `hp`, `mp`, `sp`, `atk_phys`, `agility`, `defense`, `magic_level`, and `guild_merit` rows
- **THEN** the `屬性` section renders only the `atk_phys`, `agility`, `defense`, and `magic_level` rows, in that order, and renders no `hp`, `mp`, `sp`, or `guild_merit` row

#### Scenario: The abbreviated attribute and guild-rank labels match the design draft
- **WHEN** the `屬性` section renders the `magic_level` row, and the `計數・公會` section renders the guild rank row
- **THEN** the `magic_level` row's label reads `魔階` and the guild rank row's label reads `公會階級`, matching the design draft's `#dr-status` markup

### Requirement: The drawer layer renders the wallet exactly once
Across every drawer, the player's wallet SHALL be rendered in exactly one place — the character-status
drawer's character section — and SHALL be read from the committed panel that owns it. The shop, the
lore reference and the bag SHALL NOT render a balance of their own. A drawer that cannot read the
wallet from an available panel SHALL render no balance at all rather than a zero.

#### Scenario: One wallet across the whole drawer layer
- **WHEN** every drawer is opened in turn with the `services` and `character` panels available
- **THEN** exactly one wallet value is rendered across all of them, in the character-status drawer

#### Scenario: An unavailable panel renders no balance
- **WHEN** the panel that carries the wallet is unavailable
- **THEN** no drawer renders a balance, and none renders a zero in its place
