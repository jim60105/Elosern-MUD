## MODIFIED Requirements

### Requirement: The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces
The WebClient SHALL render as a full-bleed stage that fills the viewport, with the scene backdrop as
the lowest layer, the portrait anchors above it, the HUD islands above those, the bottom band above
those, and the command line topmost among the persistent surfaces. HUD surfaces SHALL be placed by
named stage anchors — the top-left `place` and `vitals` anchors, the top-right `map` anchor, the portrait anchors
`actor-left` and `actor-right`, the bottom band's two regions `band-message` and `band-command`, the dialogue `choices` anchor, and
the `command-line` row — and SHALL NOT be placed inside a page-scrolling container that can push a
required surface out of view.

The top band SHALL be 48px tall at every supported viewport and SHALL carry only the brand, the top
navigation bar, the possession banner when present, the character switcher, and the connection
state; it SHALL carry no location label and no time label. The `place` anchor SHALL sit at the stage
box's top-left corner, below the top band, at a fixed height that does not depend on the label
lengths it holds, and the `vitals` anchor SHALL begin below it. The `map` anchor SHALL sit at the stage
box's top-right corner, below the top band; its content column (the minimap island, then the
objective line, then any other island this capability places there) SHALL be right-aligned to the
stage's right gutter and bounded above the bottom band.

The bottom band SHALL span the full stage width along the stage's bottom edge at one fixed height,
`clamp(260px, 27.8vh, 400px)` (300px at the 1920x1080 reference viewport), taken from a single
shared band-height token. The band's height SHALL NOT depend on its content, on the dock frame, on
the committed mode, or on any measurement: no frame, pane, line count, dialogue exchange, or mode
change SHALL grow or shrink it. The band SHALL be divided into the message region `band-message`,
covering the left two thirds of the band's width, and the command region `band-command`, covering
the remaining right third; in creation mode, where the message region is hidden, the command region
SHALL span the whole band, and in dialogue mode, where the command region is collapsed, the message
region SHALL span the whole band. The band SHALL carry the reference's band chrome (the upward gradient,
the hairline top border, and the upward shadow) on the band itself, not on the content inside it.
The stage box — the region between the top band's lower edge and the bottom band's upper edge — is
where the scene is seen, and at the 1920x1080 reference viewport it SHALL be at least 65% of the
viewport's height — at least 702px of 1080; the 48px top band and the 300px bottom band leave 731px. Every surface other than the band SHALL be positioned relative to the
band-height token so that none of them overlaps the band.

The portrait anchors SHALL stand on the band: each SHALL be bottom-aligned to the band's upper edge,
SHALL be `min(62vh, 680px)` tall but never taller than the stage box, SHALL be inset 6% of the stage
width from its own side, and SHALL never cover the band. The `actor-left` anchor SHALL carry the
player's stage actor — the current roster character's portrait, resolved exactly as the stage
portrait was before this requirement, with the truthful placeholder when no image exists — in
exploration, dialogue, and combat mode. The `actor-right` anchor SHALL carry the dialogue host's stage
actor while the committed mode is `dialogue` and the committed `dialogue` panel is available, SHALL carry
the foe line-up that "Foes stand opposite the player during combat" defines while the committed mode is
`combat` and at least one foe is active, or while a round that ended the fight still plays as "Combat
beats are choreographed on the stage at the motion level" defines, and SHALL carry no content in every
other state. The foe
line-up MAY extend leftward beyond the `actor-right` anchor's own box, within the bounds that
requirement sets. Every stage actor follows "Stage actors present the player and the dialogue host with
a speaking state". The portrait anchors are non-interactive art: they SHALL carry no
focusable element and SHALL NOT intercept pointer events, and they MAY sit behind the HUD islands, the
`choices` anchor, and the command-line row.

The `choices` anchor SHALL render only in dialogue mode. It SHALL be horizontally centred on the stage
box, at most `min(560px, 40%)` of the stage width wide, vertically centred in the stage box and bounded
by it, above the portrait anchors; when its content is taller than the stage box allows it SHALL
scroll internally, and it SHALL NOT grow into the top band or the bottom band.

At 1920x1080, 1440x900, and 1280x720 no interactive stage anchor (`place`, `vitals`, `map`,
`band-message`, `band-command`, `choices`, `command-line`) SHALL overlap another interactive anchor's content,
and the top band's own elements SHALL neither overlap one another nor extend into the HUD island
anchor region: a band element whose content is variable-width SHALL be bounded and truncated rather
than sized by its content. A transient popover opened from a top-band element MAY overlay the
island anchors while open, provided it does not change the band's own rendered box and closes on
Escape and on outside activation; a surface that permanently occupies vertical space SHALL NOT be
introduced into the band this way.

#### Scenario: The stage fills the viewport with layered surfaces
- **WHEN** the shell mounts at 1440x900
- **THEN** the scene backdrop fills the stage box, and the player portrait, the HUD islands, the bottom band, and the command line are layered above it in that order with no page-level scrollbar

#### Scenario: Required surfaces never scroll out of view
- **WHEN** the HUD islands hold more content than their anchor's height, or the dock frame or the narrative holds more content than its band region
- **THEN** the island stack or the band region itself is bounded and scrolls internally, and no required surface is pushed below the visible viewport

#### Scenario: Anchors do not overlap at the minimum viewport
- **WHEN** the shell renders at 1280x720 with every mode-visible surface present
- **THEN** no interactive stage anchor's rendered box intersects another interactive anchor's rendered box

#### Scenario: The top band's own elements do not collide
- **WHEN** the shell renders at 1280x720 with every top-band element present and a maximum-length character name committed
- **THEN** the band's elements render side by side without intersecting, the variable-width element is truncated within its bound, and no band element's box extends into the island anchor region

#### Scenario: A band popover overlays without displacing
- **WHEN** a transient popover is opened from a top-band element
- **THEN** the band's rendered box is unchanged, the popover renders above the island anchors, and Escape or outside activation closes it

#### Scenario: The bottom band keeps one height whatever it holds
- **WHEN** the shell renders at 1920x1080 and the player moves through the exploration scene overview, a target's verb popover, the waiting frame, an empty pane host, the deepest combat frame, and a dialogue exchange with four picks
- **THEN** the bottom band's rendered height is 300px (±1px) in every one of those states, the message region's and the command region's boxes are unchanged between the exploration and combat states, and in the dialogue state the message region spans the band's whole width at the same height

#### Scenario: The band splits two thirds and one third
- **WHEN** the shell renders in exploration mode at 1920x1080, 1440x900, and 1280x720
- **THEN** the message region spans the left two thirds of the band's width and the command region spans the remaining right third (each ±1px), both share the band's top and bottom edges, in creation mode the command region spans the whole band, and in dialogue mode the message region spans the whole band while the command region is not rendered

#### Scenario: The player portrait stands on the band
- **WHEN** the shell renders in exploration mode at 1920x1080 with a committed roster portrait for the current character
- **THEN** the `actor-left` anchor renders that portrait, its bottom edge coincides with the band's top edge, its height is `min(62vh, 680px)` (±1px), its left edge is 6% of the stage width from the stage's left edge, it holds no focusable element, and the `actor-right` anchor renders no content

#### Scenario: The portrait never outgrows the stage box
- **WHEN** the shell renders at 1280x720, where `min(62vh, 680px)` exceeds the stage box's height
- **THEN** the player portrait's height equals the stage box's height and its top edge is not above the top band's lower edge

#### Scenario: The stage box is at least 65% of the reference viewport
- **WHEN** the shell renders in exploration mode at 1920x1080
- **THEN** the top band is 48px tall, the bottom band is 300px tall (each ±1px), and the stage box between them is at least 702px tall (65% of 1080)

#### Scenario: The top band carries no location or time
- **WHEN** the shell renders in exploration mode with a committed location label and world time
- **THEN** the top band's rendered height is 48px, no element inside the top band states the location label or the world time, and the place anchor below the top band states both

#### Scenario: The dialogue host stands opposite the player
- **WHEN** the committed mode changes from exploration to dialogue at 1920x1080 with an available `dialogue` panel
- **THEN** the `actor-right` anchor renders the host's stage actor, its bottom edge coincides with the band's top edge, its right edge is 6% of the stage width from the stage's right edge, its height equals the player portrait's height, it holds no focusable element, and on the return to exploration `actor-right` renders no content again

#### Scenario: The choice list sits over the stage between the portraits
- **WHEN** the dialogue choice list renders four picks and its three trailing rows at 1920x1080 and at 1280x720 with the vitals island, the minimap, and the party island present
- **THEN** the `choices` anchor is horizontally centred on the stage box (±1px), lies entirely inside the stage box, intersects no `place`, `vitals`, `map`, band, or command-line anchor, and every row is reachable, scrolling inside the anchor at 1280x720 if needed

### Requirement: Surface visibility is gated by the committed game mode
The shell SHALL expose the committed mode on the stage root as `data-elosern-mode`, and surface
visibility SHALL be derived from that single attribute. A surface hidden for the current mode SHALL be
removed from rendering with `display:none` — never dimmed, never merely visually hidden — so it leaves
the accessibility tree and the tab order. The one exception is the band's command region in dialogue
mode, which animates out as "The command region collapses in dialogue mode and the message window spans
the band" defines: it leaves the accessibility tree, the tab order, and pointer hit-testing at the
commit, and is `visibility: hidden` once its slide ends. The second exception is the combat stage
hold: while a round whose publication already committed another mode still plays, as "Combat beats are
choreographed on the stage at the motion level" defines, the decorative combat veil and the foe line-up
MAY remain on the stage, outside the accessibility tree, the tab order, and pointer hit-testing, until
the round ends; every other surface follows the committed mode at the commit. The matrix SHALL be:

| Surface | exploration | combat | dialogue | creation |
|---|---|---|---|---|
| place card (location, world time) | visible | visible | visible | hidden |
| message window (band message region) | visible | visible | visible (whole band width, paged, name plate) | hidden |
| dialogue choice list (`choices` anchor, centred over the stage) | not rendered | not rendered | once the current response's last page is fully shown, while no action is in flight | not rendered |
| vitals island (vitals/conditions) | by the vitals rule | visible | by the vitals rule | hidden |
| minimap island | visible | **hidden** | visible | hidden |
| party quickbar island | while the party is non-empty | while the party is non-empty | while the party is non-empty | hidden |
| objective line (under the minimap) | visible | hidden | hidden | hidden |
| player standing portrait (`actor-left`) | visible | visible | visible (dimmed while the host speaks) | hidden |
| dialogue host standing portrait (`actor-right`) | not rendered | not rendered | while the `dialogue` panel is available (dimmed while the player speaks) | not rendered |
| foe line-up (`actor-right`, at most three active foes) | only while a round that ended the fight still plays (held, inert) | while at least one foe is active | not rendered | not rendered |
| action dock (band command region) | visible | visible | **hidden** (command region collapsed: inert at commit, slides out, then `visibility: hidden`) | visible (creation form, full band width) |
| command-line toggle (⌨, message region's bottom-right) | visible | visible | visible | hidden |
| log control (日誌, beside the command-line toggle) | visible | visible | visible | hidden |
| command line (row on the message region's top edge) | while expanded | while expanded | while expanded | hidden |
| scene backdrop | visible (exploration stage) | visible (combat stage) | visible (unchanged art) | visible |

While the committed mode is `dialogue` the scene backdrop SHALL keep rendering its committed
exploration art truthfully — the dialogue's focus is carried by the stage actors, the name plate, and
the message window, and the choice list, not by mutating the backdrop. Per-surface requirements that name their own visible-mode
sets SHALL stay consistent with this matrix. A cell that names a data rule instead of `visible` means
the surface is shown in that mode only while its own requirement's rule holds for the committed state,
and is otherwise hidden the same way (`display:none`, or not rendered at all where that requirement
says so). The command line's `while expanded` cell is such a rule: its own requirement defines when the
row is expanded, and a collapsed row is hidden with `display:none` exactly like a mode-hidden surface.
Each playing mode has one focus home: the action dock in exploration, combat, and creation mode, and
the message window's focus target in dialogue mode, as "The command region collapses in dialogue mode
and the message window spans the band" defines. When a mode change, a committed revision that turns a
surface's data rule false, or a collapse of the command line hides the surface that currently holds
focus, the shell SHALL move focus to the focus home of the mode being entered or kept before the
surface is removed, using the existing focus-restore path. A mode change into creation SHALL also
collapse the command line, so leaving creation never reveals an expanded row.

#### Scenario: The minimap disappears in combat
- **WHEN** the committed mode changes from exploration to combat
- **THEN** the minimap island is absent from the DOM layout and from the tab order, and it is not merely dimmed, while the participant frame renders in the `map` anchor and the foe line-up renders in `actor-right`

#### Scenario: The minimap returns on leaving combat
- **WHEN** the committed mode changes from combat back to exploration, including by a round whose beats
  are still playing
- **THEN** the minimap island renders again with the committed `local_map` payload at the commit, and any
  held foe line-up or veil is inert and outside the accessibility tree

#### Scenario: Focus is rescued before its surface is hidden
- **WHEN** the focused element belongs to a surface that the incoming mode hides, including a scene-overview chip when the incoming mode is dialogue
- **THEN** focus is moved to the incoming mode's focus home before the surface is removed, and no focus is lost to the document body

#### Scenario: Creation mode presents only the creation surfaces
- **WHEN** the committed mode is creation
- **THEN** the place card, the message window, the command-line toggle, the log control, the `vitals` and `map` anchors with every island in them, the player standing portrait, and the command line are absent, and the action dock renders the creation form across the whole bottom band

#### Scenario: Dialogue mode keeps the cockpit visible
- **WHEN** the committed mode changes from exploration to dialogue with an available `dialogue` panel
- **THEN** the place card, message window, minimap, player standing portrait, command-line toggle, and log control all
  remain rendered, the dialogue host's standing portrait is rendered in `actor-right`, the command line keeps its expanded or collapsed state, the objective line is hidden with `display:none` because only exploration shows it, the vitals and party islands keep following the same data rules as in
  exploration, the action dock is out of the accessibility tree and the tab order together with the band's command region from the commit and is `visibility: hidden` once the region's slide ends, while the message window spans the whole band with the host's name plate, and the `#action-dock` element is not removed from the document

#### Scenario: Dialogue backdrop keeps its committed art
- **WHEN** the committed mode is dialogue
- **THEN** the scene backdrop renders the same committed exploration art as before the mode
  change, unmodified

#### Scenario: The objective line shows only in exploration
- **WHEN** a non-empty committed `objectives` panel stays committed while the mode changes from exploration to combat, then to dialogue, then back to exploration
- **THEN** the objective line renders in exploration, is hidden with `display:none` in combat and in dialogue, and renders again on the return to exploration

#### Scenario: The command line starts collapsed in every playing mode
- **WHEN** the shell mounts in exploration mode, and later the committed mode changes to combat and then to dialogue without the player opening the command line
- **THEN** in each mode the command-line toggle is rendered with `aria-expanded="false"`, the command-line row is hidden with `display:none`, and the input field is outside the tab order

#### Scenario: Entering creation collapses an expanded command line
- **WHEN** the command line is expanded with focus in its field and the committed mode changes to creation, and later back to exploration
- **THEN** focus moves to the action dock before the row is hidden, and on the return to exploration the command line is collapsed

### Requirement: Foes stand opposite the player during combat
While the committed mode is `combat`, the `actor-right` anchor SHALL carry a foe line-up: one stage actor
for each committed combat participant whose team is the opposing side and whose state is active, in the
presenter's order, at most three. Foes beyond the third SHALL NOT stand on the stage; the participant
frame lists them. Party members other than the player SHALL NOT stand on the stage; the player alone
stands in `actor-left`. When no foe is active the line-up SHALL render nothing.

The line-up SHALL stand on the band: every foe's stage actor SHALL be bottom-aligned to the band's upper
edge. The first foe SHALL stand at the `actor-right` anchor's position — its right edge inset 6% of the
stage width from the stage's right edge — and each later foe SHALL stand further toward the stage's
centre, overlapping the foe before it and drawn behind it. With one, two, or three foes shown, each
foe's height SHALL be 100%, 90%, or 80% of the player's stage actor's height. At 1920x1080, 1440x900,
and 1280x720 no foe's stage actor SHALL cross the stage's vertical centre line or intersect the player's
stage actor. Each foe's stage actor SHALL expose that participant's portrait reference as a data
attribute for tests and for the beat presentation. The line-up is decorative art: it SHALL carry no
focusable element, SHALL NOT intercept pointer events, and SHALL NOT state tokens, hit-point numerals, or
states, which remain the participant frame's. Each foe SHALL carry a slim decorative hit-point gauge,
hidden from assistive technology, whose fill shows that foe's current hit points (the displayed value
while a combat round plays) over its maximum, with a trailing bar like the vitals'.

While a combat round plays by itself, the line-up SHALL stand the foes that were active before the round,
in the presenter's order, and a foe SHALL leave it only when its own defeat beat plays; when the round
ends, by itself or because the player ended it, the line-up SHALL stand the committed active foes.

A live change of the committed mode into `combat` SHALL bring the line-up in from the right with a fade
over the actor duration of the client's motion level (350ms at `full`), and a live change out of `combat`
SHALL fade it out. Within combat, a foe that leaves the active set SHALL fade out, a foe that joins SHALL
enter the same way, and the remaining foes SHALL move to their new places. Every leaving copy SHALL be
out of reach as "A leaving element is out of reach while it animates out" requires. Mounting the client
in combat, a reload, and a reconnect SHALL play no entrance. At `reduced` the line-up SHALL only fade,
within 150ms, and at `off` every change SHALL render its final state in the commit's frame.

#### Scenario: One foe stands opposite the player
- **WHEN** a combat snapshot commits one active foe with a catalog portrait at 1920x1080
- **THEN** `actor-right` renders one foe stage actor with that image, its bottom edge on the band's top
  edge, its right edge 6% of the stage width from the stage's right edge, its height equal to the
  player's stage actor's height (±1px), and no focusable element

#### Scenario: Three foes overlap toward the centre
- **WHEN** a combat snapshot commits three active foes at 1920x1080, 1440x900, and 1280x720
- **THEN** three foe stage actors render in presenter order, each 80% of the player's height (±1px),
  each later one further left and behind the one before it, and none crosses the stage's centre line or
  intersects the player's stage actor

#### Scenario: Foes beyond three stay in the participant frame
- **WHEN** a combat snapshot commits five active foes
- **THEN** the line-up shows the first three in presenter order, and the participant frame lists all five
  foes with their tokens and hit points

#### Scenario: Only active foes stand on the stage
- **WHEN** a committed update that carries no playable round changes one of two foes to defeated, and
  later a playing round defeats the other foe
- **THEN** the first foe's stage actor fades out at the commit and is inert while it leaves, the other
  foe moves to the first place, the second foe stays on the stage until its defeat beat plays, and the
  participant frame still lists both defeated foes with their text markers

#### Scenario: A missing portrait shows the truthful placeholder
- **WHEN** an active foe's portrait reference is `null`, and another's names no catalog entry
- **THEN** both foes' stage actors show the display name's initial and the display name, and neither
  renders an image or a constructed URL

#### Scenario: Entering combat brings the foes in
- **WHEN** the effective level is `full` and a committed revision changes the mode from exploration to
  combat with two active foes
- **THEN** the line-up enters from the right with a 350ms fade, and after a later change back to
  exploration it fades out and is inert while it leaves

#### Scenario: A reload in combat plays no entrance
- **WHEN** the client reloads or reconnects while the committed mode is combat
- **THEN** the line-up renders in its final state with no running transition

#### Scenario: Reduced and off keep the foes still
- **WHEN** the effective level is `reduced`, and later `off`, and the mode enters and leaves combat
- **THEN** at `reduced` the line-up only fades within 150ms and never moves, and at `off` it is present
  or absent in the commit's frame

### Requirement: Vitals pair an icon, a label, and numerals with a trailing damage bar
Each of hp, mp, and sp SHALL render as one vital row carrying an icon, a Traditional Chinese label,
and the `current / maximum` numerals from `status.resources` — or, for hp while a combat round plays,
the displayed value that `webclient-combat-menu` "A combat round plays beat by beat" defines — above a track containing a trailing bar
and a fill. The numerals SHALL render at every value, so no vital state is conveyed by the coloured
fill alone. The sp fill SHALL carry a non-colour texture distinguishing it from the hp and mp fills.

The trailing bar SHALL exist to make damage taken visible: it SHALL lag the fill when the ratio falls
and SHALL be overtaken by the fill when the ratio rises. It SHALL be decorative — hidden from the
accessibility tree, carrying no accessible name, and conveying nothing the numerals do not already
carry on the same revision. It SHALL NOT render any value that was not a previously displayed ratio of
that same gauge, where a displayed ratio comes only from the committed `status` or from a committed
beat's `hp_after` during a round's playback, SHALL NOT be interpolated or extrapolated from narrative text or an action result,
and SHALL reset to the current ratio when the epoch changes, so no trail is drawn across a reconnect.
Its motion SHALL be token-gated so the reduced-motion block disables it. At the `full` motion level the
trailing bar SHALL start following a drop 300ms after the fill moves.

A vital at or below the client's display threshold SHALL be marked by both a recolour and an explicit
text marker, never by the recolour alone.

#### Scenario: Each vital is legible without colour
- **WHEN** the vitals island renders with the `status` panel committed
- **THEN** each of hp, mp, and sp shows an icon, a text label, and its `current / maximum` numerals, and the sp fill is distinguishable from hp and mp by texture rather than by hue

#### Scenario: Damage leaves a visible trailing bar
- **WHEN** a committed revision lowers a gauge's ratio
- **THEN** the fill moves to the new ratio and the trailing bar follows behind it, so the gap between them shows the amount lost, and the numerals show the new value immediately

#### Scenario: Healing shows no trailing bar
- **WHEN** a committed revision raises a gauge's ratio
- **THEN** the fill overtakes the trailing bar and no lagging gap is drawn

#### Scenario: The trailing bar follows a round's displayed hit points
- **WHEN** a playing combat round shows the player's hp stepping from 40 to 28 and then to 15 of 60
- **THEN** the numerals and the fill show each displayed value in turn, the trailing bar lags each drop
  from the previously displayed ratio, and once the round ends the numerals and fill show the committed
  value

#### Scenario: The trailing bar never shows an uncommitted value
- **WHEN** the trailing bar renders at any point
- **THEN** its width corresponds to a ratio that was previously displayed for that same gauge — a committed `status` value, or a committed `combat_beats` beat's `hp_after` during that round's playback — never a value from neither source, and it is absent from the accessibility tree

#### Scenario: A reconnect does not draw a trail across epochs
- **WHEN** a new epoch's snapshot commits after a reconnect
- **THEN** the trailing bar resets to the current ratio and no gap is drawn between the pre-reconnect and post-reconnect values

#### Scenario: A low vital is marked by text as well as colour
- **WHEN** a vital falls to or below the client's display threshold
- **THEN** the row carries both the low recolour and an explicit text marker, and the numerals continue to render

## ADDED Requirements

### Requirement: Combat beats are choreographed on the stage at the motion level
While a combat round plays by itself, as `webclient-combat-menu` "A combat round plays beat by beat"
defines, each beat SHALL play one stage gesture once its page is fully shown, on the stage actors that the
beat names and that stand on the stage (the player in `actor-left`, a foe in the foe line-up), taking every
duration and distance from the client's motion tokens:
- **The first beat of each action:** the acting stage actor steps 24px toward the stage's centre and back
  within 240ms.
- **`damage`:** the target's stage actor shakes 6px from side to side for 180ms with a brief flash, a
  decorative number naming the damage rises from it and fades over 600ms, and its displayed hit points
  move to the beat's `hp_after` as the gesture starts, in the vitals or the foe's gauge and in the
  participant frame, with the trailing bar following.
- **`target_defeated`:** a foe's stage actor fades and drops out of the line-up. The player's stage actor
  never leaves the stage.
- **`roll` and `other`:** no gesture.

The next beat's pause SHALL start when the gesture has played. A beat that names a participant with no
stage actor (a party member other than the player, or a foe beyond the third) SHALL play no gesture. The
gestures, the rising number, and the flash SHALL be decorative: absent from the accessibility tree,
never intercepting a pointer, and never the only carrier of any value, which the beat's page and the
numerals already state.

When the round's publication has already committed a mode other than `combat` (the round that ends the
fight), the combat veil SHALL stay at its combat opacity and the foe line-up SHALL stay on the stage,
inert, while the round plays by itself; when the round ends, by itself or because the player ended it,
the veil SHALL fade out and the line-up SHALL leave as a live change out of combat does. The mode
attribute, every mode-gated surface, the command region's content, focus, and the accessibility tree
SHALL follow the committed mode at the commit, and the committed flash and flip SHALL play at the commit
as "Mode changes transition at the motion level" defines.

At `reduced`, no step, shake, flash, rise, or drop SHALL move or brighten anything; a defeated foe SHALL
only fade, within 150ms, and the pauses SHALL be kept. At `off`, no round plays by itself, so no gesture
and no stage hold SHALL occur.

#### Scenario: The actor steps and the target reacts
- **WHEN** the effective level is `full` and a playing round shows the player's roll beat and then its
  damage beat on a foe on the stage
- **THEN** the player's stage actor plays one 240ms step toward the centre on the roll beat, and on the
  damage beat the foe's stage actor plays one 180ms shake with a flash, a number naming the damage rises
  from it over 600ms, and the foe's gauge and frame numerals move to the beat's `hp_after`

#### Scenario: The trailing bar follows 300ms later
- **WHEN** the effective level is `full` and a damage beat lowers the player's displayed hit points
- **THEN** the vitals fill moves at once and the trailing bar starts following 300ms later

#### Scenario: A defeated foe drops out on its own beat
- **WHEN** the effective level is `full` and a playing round's defeat beat names a foe on the stage
- **THEN** that foe stays on the stage until the defeat beat plays, then fades and drops out and is inert
  while it leaves

#### Scenario: The round that ends the fight plays in front of the combat stage
- **WHEN** the effective level is `reduced` and an accepted attack defeats the last foe, committing mode
  `exploration`
- **THEN** in the commit's frame the stage's mode attribute is `exploration` and the minimap is visible,
  while the combat veil keeps its combat opacity and the foe line-up stays on the stage, inert, until the
  round's beats have played, after which the veil fades out and the line-up leaves

#### Scenario: Ending the round releases the stage
- **WHEN** a round that ended the fight is playing and the player clicks the message window
- **THEN** the veil starts fading out and the foe line-up leaves at once

#### Scenario: Reduced keeps the rhythm without motion
- **WHEN** the effective level is `reduced` and a round with a roll, a damage, and a defeat beat plays
- **THEN** no stage actor translates, shakes, or brightens, no number rises, the defeated foe only fades
  within 150ms, and each beat still follows the 400ms pause

#### Scenario: Off plays no gesture and holds nothing
- **WHEN** the effective level is `off` and an accepted attack defeats the last foe
- **THEN** no gesture plays, the combat veil and the foe line-up are gone in the commit's frame, and the
  round's beats are read as text pages
