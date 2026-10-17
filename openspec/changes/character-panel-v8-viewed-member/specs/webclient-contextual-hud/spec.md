# Spec Delta

## MODIFIED Requirements

### Requirement: The character-status drawer degrades section by section and never substitutes a disguise
The character-status drawer SHALL present the committed `status` panel's resources and its complete condition roster in every mode, because that panel is available in every mode. It SHALL present the committed `character` panel's true traits and guild standing and the committed `party_member` panel's persona prose and intimate state for the viewed member, and SHALL mark each of those sections with the registry-owned reason when its panel is unavailable rather than hiding the drawer or inventing a value.

#### Scenario: Equipment and wallet belong to the inventory drawer
- **WHEN** the character-status drawer renders
- **THEN** equipment and wallet presentation, which belong exclusively to the inventory drawer, do not render in character status

#### Scenario: Conditions pair a glyph with every backed value
- **WHEN** the condition roster renders a committed condition
- **THEN** the condition pairs a non-colour severity glyph with its label and every numeric or derived-modifier value the payload provides

#### Scenario: A disguise compares, never substitutes
- **WHEN** a disguise is active
- **THEN** the drawer renders the displayed values beside the true trait rows they describe, distinctly labelled, together with the statement that a disguise affects display, registration and identification only and that combat always resolves against true values; a displayed value never replaces a true trait row

#### Scenario: The 親密狀態 disclosure is preserved in place
- **WHEN** the committed `party_member` panel's intimate section is present, and when it is `null` or the panel is unavailable
- **THEN** the drawer renders the collapsed-by-default 親密狀態 disclosure widget — added by the archived intimate-status change — immediately after the 偽裝 (disguise) section and before the 背景 (persona) section, and no change removes it, reorders it, or alters its disclosure widget, content, or collapsed default; like the persona area it spans the full row of the section grid; with `intimate` null or the panel unavailable the section is absent from the DOM, exactly as the merged main spec requires; this change removes only the equipment and wallet sections

#### Scenario: Every section names itself in the shared treatment
- **WHEN** any of the drawer's sections renders (vitals, traits, conditions, guild counters, disguise, intimate status, persona)
- **THEN** each carries a labelled, small-caps section heading naming what it presents, using the same heading treatment the HUD's other islands use

#### Scenario: Value rows render as bordered card tiles
- **WHEN** the vitals, traits, or guild-counter sections render their values
- **THEN** each value is its own bordered card tile in an auto-fill grid of equal-width tracks rather than a plain text row, each tile only as tall as its own content, with the tile's label at the left and its `current`/`current / maximum` value in the shared numeral treatment at the right; a tile carrying more than two breakdown chips spans its grid's full row so its chips wrap in one wide line; and no value not already present in the committed payload (such as an effective-vs-base delta) is invented to fill the tile

#### Scenario: Sections size themselves independently
- **WHEN** the section grid renders
- **THEN** the sections are content-sized cards in an auto-fit grid of equal-width tracks in their DOM order, with the persona area, the intimate disclosure, and a panel-wide unavailable reason spanning the full row, so no section's height depends on another's

#### Scenario: The hero names only supplied values
- **WHEN** the drawer body opens
- **THEN** it opens with a hero naming the committed character — the `status` panel's actor name, its composed full title (`status` actor `full_title`), and the `character` panel's guild rank, each rendered only when the payload supplies a non-blank value and omitted — never guessed — otherwise; the name and title therefore stay in every mode, and the rank is absent while the `character` panel is unavailable

#### Scenario: The hero carries the openers, the header carries the title
- **WHEN** the hero renders
- **THEN** it carries the drawer's existing secondary openers (技能書, and 同伴 ‧ 隊伍 while the party panel is available) in one wrapping action row, with their existing behavior, and the body does not repeat the drawer title the shared header already renders

#### Scenario: The roster renders as coloured pills with nothing dropped
- **WHEN** the condition roster renders
- **THEN** it renders as a wrapped row of rounded pill badges, one per condition, each carrying that condition's label, its visible severity word, its non-colour severity glyph, and its duration/modifier text — the same content the roster shows today, none of it dropped — coloured per severity using the same severity-to-colour mapping the capped status-island condition chips use elsewhere in the HUD; these presentation rules apply identically whether a section is fully populated or marked with a registry-owned unavailable reason

#### Scenario: The drawer is useful in combat
- **WHEN** the committed mode is combat
- **THEN** the drawer opens and renders the `status` resources, the complete condition roster, and the trait, guild and persona sections from the `character` and `party_member` panels, which stay available in combat, without a wallet or equipment placeholder

#### Scenario: Conditions are never colour-only
- **WHEN** the condition roster renders a committed condition
- **THEN** it pairs a non-colour severity glyph with the condition's label and every numeric or derived-modifier value the payload provides

#### Scenario: A disguise is a comparison, not a substitution
- **WHEN** the committed `character` panel carries an active disguise with displayed values
- **THEN** the drawer renders each displayed value beside the true trait row it describes with an explicit label, states that combat resolves against true values, and shows no true row replaced by a displayed one

#### Scenario: The intimate section is preserved in place
- **WHEN** the character-status drawer renders with the `party_member` panel available and its intimate section present
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
- **THEN** the hero shows that name, that title and `公會階級 <rank>` above one row holding the 技能書 and 同伴 ‧ 隊伍 openers, and the drawer title appears only in the shared header
