## ADDED Requirements

### Requirement: Combat identity and status remain legible without changing authority
The combat presentation SHALL show each standing foe name with its decorative gauge, preserve every participant identity and numeric HP with a decorative HP hairline in the participant frame, and distinguish the acting or focused-target foe by a non-colour cue without making it interactive. The compact frame SHALL NOT obscure a standing foe head. A zero canonical round SHALL be described as preparation rather than incremented.

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
points, and states: the foe line-up in `actor-right` carries decorative portraits, names, non-colour
acting/target cues and hit-point gauges without numerals. A display name longer than the frame's width SHALL end in an
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

### Requirement: Foes stand opposite the player during combat
While the committed mode is `combat`, the `actor-right` anchor SHALL carry a foe line-up: one stage actor
for each committed combat participant whose team is the opposing side and whose state is active, in the
presenter's order, at most three. Foes beyond the third SHALL NOT stand on the stage; the participant
frame lists them, and no "+N" count is drawn. Party members other than the player SHALL NOT stand on the
stage; the player alone stands in `actor-left`. When no foe is active the line-up SHALL render nothing.

The line-up SHALL be a depth-staged row that grows leftward. The first foe SHALL stand in front, nearest
the stage's right edge, and each later foe SHALL stand behind the one before it: further toward the
stage's centre, overlapping that foe and drawn behind it, smaller, and standing a little higher (up-stage)
than it. With one, two, or three foes shown, the foes' heights SHALL be, front to back, 100%; 90% and 78%;
or 80%, 70%, and 61% of the player's stage actor's height, and every later foe SHALL show 46% of its width
past the foe in front of it. The front foe SHALL stand on the band's upper edge, and each foe behind SHALL
stand 3.5% of the portrait anchor's height higher than the one in front of it. The row's right inset SHALL
be the portrait anchor's right inset, grown just enough that the front foe's horizontal centre (its face)
lies at least 24px left of the participant frame's column, which spans the `map` anchor's width in combat.
At 1920x1080, 1440x900, and 1280x720 no foe's stage actor SHALL cross the stage's vertical centre line or
intersect the player's stage actor.

Each foe's stage actor SHALL expose that participant's portrait reference as a data attribute for tests
and for the beat presentation. Each foe SHALL show its display name above its decorative hit-point gauge
and distinguish acting or focused-target presentation with a non-colour cue. Names SHALL ellipsize within
their plate while retaining full DOM text. Each gauge SHALL be a slim track centred
under the figure on the scene caption's baseline, above the command-line row, filled to that foe's current
hit points (the displayed value while a combat round plays) over its maximum, with a trailing bar that follows a drop after the vitals' trail delay so
the damage shows as a gap. The line-up is decorative art: it SHALL be hidden from assistive technology,
SHALL carry no focusable element, SHALL NOT intercept pointer events, and SHALL NOT state tokens, hit-point
numerals, or participant states, which remain the participant frame's.

While a combat round plays by itself, the line-up SHALL stand the foes that were active before the round,
in the presenter's order, and a foe SHALL leave it only when its own defeat beat plays; when the round
ends, by itself or because the player ended it, the line-up SHALL stand the committed active foes.

A live change of the committed mode into `combat` SHALL bring the line-up in: after half the flash's
duration it SHALL fade in over the actor duration of the client's motion level (350ms at `full`) while
each foe slides in from the right, the front foe furthest. A live change out of `combat` SHALL fade it out
while the foes drift a step to the right. Within combat, a foe that leaves the active set SHALL fade out
where it stands, a foe that joins SHALL slide and fade in, and the remaining foes SHALL glide to their new
places and sizes. Every leaving copy SHALL be out of reach as "A leaving element is out of reach while it
animates out" requires. Mounting the client in combat, a reload, and a reconnect SHALL play no entrance.
At `reduced` the line-up SHALL only fade, within 150ms, and nothing in it SHALL move or glide; at `off`
every change SHALL render its final state in the commit's frame. No change SHALL scroll the stage or any
element that contains it.

#### Scenario: One foe stands opposite the player
- **WHEN** a combat snapshot commits one active foe with a catalog portrait at 1920x1080
- **THEN** `actor-right` renders one foe stage actor with that image, its bottom edge on the band's top
  edge, its height equal to the player's stage actor's height (±1px), its horizontal centre at least 24px
  left of the participant frame's left edge, a gauge and name under it, and no focusable element

#### Scenario: Three foes stand in depth toward the centre
- **WHEN** a combat snapshot commits three active foes at 1920x1080, 1440x900, and 1280x720
- **THEN** three foe stage actors render in presenter order at 80%, 70%, and 61% of the player's height
  (±1px), each later one further left, higher, and behind the one before it, and none crosses the stage's
  centre line or intersects the player's stage actor

#### Scenario: Foes beyond three stay in the participant frame
- **WHEN** a combat snapshot commits five active foes
- **THEN** the line-up shows the first three in presenter order, and the participant frame lists all five
  foes with their tokens and hit points

#### Scenario: The gauge follows the committed hit points
- **WHEN** a committed update lowers an active foe's `hp_current`
- **THEN** that foe's gauge fill shrinks to the new ratio, its trailing bar follows after the trail delay,
  and neither the gauge nor the line-up states an HP numeral

#### Scenario: Only active foes stand on the stage
- **WHEN** a committed update that carries no playable round changes the first of two foes to defeated,
  and later a playing round defeats the other foe
- **THEN** the first foe's stage actor fades out at the commit and is inert while it leaves, the other
  foe glides to the front place, the second foe stays on the stage until its defeat beat plays, and the
  participant frame still lists both defeated foes with their text markers

#### Scenario: A missing portrait shows the truthful placeholder
- **WHEN** an active foe's portrait reference is `null`, and another's names no catalog entry
- **THEN** both foes' stage actors show the display name's initial and the display name, and neither
  renders an image or a constructed URL

#### Scenario: Entering combat brings the foes in
- **WHEN** the effective level is `full` and a committed revision changes the mode from exploration to
  combat with two active foes
- **THEN** the line-up fades in over 350ms while its foes slide in from the right, and after a later change
  back to exploration it fades out and is inert while it leaves, and at no frame does any stage ancestor
  scroll horizontally

#### Scenario: A reload in combat plays no entrance
- **WHEN** the client reloads or reconnects while the committed mode is combat
- **THEN** the line-up renders in its final state with no running transition

#### Scenario: Reduced and off keep the foes still
- **WHEN** the effective level is `reduced`, and later `off`, and the mode enters and leaves combat
- **THEN** at `reduced` the line-up only fades within 150ms and never moves, and at `off` it is present
  or absent in the commit's frame
