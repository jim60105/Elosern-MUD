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
