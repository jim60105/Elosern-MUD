## ADDED Requirements

### Requirement: Combat identity and status remain legible without changing authority
The combat presentation SHALL show each standing foe name with its decorative gauge, preserve every participant identity and numeric HP in the participant frame, and distinguish the acting or focused-target foe by a non-colour cue without making it interactive. The compact frame SHALL NOT obscure a standing foe head. A zero canonical round SHALL be described as preparation rather than incremented.

#### Scenario: Playback HP agrees
- **WHEN** a beat changes the displayed HP before final settlement
- **THEN** the participant numerator and foe gauge use the same display HP and settle to committed HP together

#### Scenario: First round is not fabricated
- **WHEN** session round is zero and then one
- **THEN** the ribbon shows preparation and then canonical round one, never adding one

#### Scenario: Portrait is missing
- **WHEN** a participant catalog entry is a placeholder
- **THEN** the thumbnail has one initial with accessible state, not clipped multiline microcopy; its visible session token remains

## MODIFIED Requirements

### Requirement: The combat participant frame presents the session's participants and their portraits
In combat the shell SHALL render a participant frame as a HUD island in the stage's top-right `map`
anchor, where the minimap is hidden in combat, and SHALL NOT place it in either portrait anchor, grouped into the
player's side and the opposing side using the committed participants' server-authored team values, in
the presenter's order. Each participant SHALL render its session token, its display name, its current
and maximum hit points as numerals — the current value being, while a combat round plays, the displayed
value that `webclient-combat-menu` "A combat round plays beat by beat" defines — and its state; a non-active state SHALL be conveyed by an explicit
text marker in addition to any colour. The frame SHALL NOT invent a field the participant descriptor
does not carry. The frame SHALL list every participant of both sides, including the foes the foe line-up
does not stand on the stage, and it SHALL remain the only surface that states participant tokens, hit
points, and states: the foe line-up in `actor-right` carries decorative portraits and decorative
hit-point gauges without numerals only. A display name longer than the frame's width SHALL end in an
ellipsis on screen while its full text stays in the DOM, and the frame's rows SHALL be compact enough
that a frame of six participants ends above the foe line-up's gauges at 1920x1080 and 1440x900; at all three acceptance sizes its visible content SHALL NOT cover a standing foe head.

Each participant's portrait SHALL be resolved only by looking its server-authored portrait reference
up in the committed art panel's portrait catalog: a resolvable entry SHALL render that entry, an
entry that resolves to a placeholder SHALL render a compact initial with its truthful availability state accessible outside the bitmap, and a null reference or an
unavailable art panel SHALL render no portrait at all. The client SHALL NOT construct a portrait
subject key or URL. While the participant frame is mounted, the frame and the stage actors SHALL be the
only presenters of the portrait catalog, so no separate portrait strip is rendered alongside them.

The participant frame SHALL be display-only: it SHALL NOT be a row container, SHALL NOT be part of
the dock's composite widget, and SHALL NOT be a second tab stop. Target selection happens in the
dock's target frame.

#### Scenario: Both sides render from the payload
- **WHEN** a combat session commits participants on both teams
- **THEN** the frame renders the player's side and the opposing side in presenter order, each participant showing its token, display name, current and maximum hit points, and state

#### Scenario: A non-active participant is marked in text
- **WHEN** a participant's state is fled, knocked out or defeated
- **THEN** the frame renders an explicit text marker for that state alongside any colour treatment

#### Scenario: A portrait comes only from the catalog
- **WHEN** a participant carries a portrait reference present in the committed portrait catalog
- **THEN** the frame renders that catalog entry, and when the reference is null or the art panel is unavailable it renders no portrait and constructs no URL

#### Scenario: The frame does not compete for focus
- **WHEN** the participant frame is mounted during combat
- **THEN** it is not reachable by sequential keyboard navigation, the dock's active row container remains the surface's only listbox, and no portrait strip is rendered outside the frame and the stage actors

#### Scenario: The frame sits in the map anchor, not on a portrait anchor
- **WHEN** a combat session commits participants at 1440x900 and 1280x720
- **THEN** the participant frame is a descendant of the `map` anchor, the `actor-right` anchor holds only the foe line-up's stage actors and gauges and no frame row, token, or hit-point numeral, and the frame's visible box intersects neither the bottom band nor the command line
