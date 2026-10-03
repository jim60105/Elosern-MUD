## RENAMED Requirements

- FROM: `### Requirement: Vitals pair an icon, a label, and numerals with a trailing damage bar`
- TO: `### Requirement: Vitals read as one numeral readout over three thin trailing-bar lines`

- FROM: `### Requirement: Condition chips carry a severity glyph, a payload duration, and a bounded overflow`
- TO: `### Requirement: Condition icons float without a window and disclose their detail in a tooltip`

## ADDED Requirements

### Requirement: The vitals dock stands at the stage's lower-left above the band
The stage SHALL render the vitals surfaces — the condition icon row and the vitals bars — as one bottom-anchored dock in the `vitals` anchor: a left-gutter column standing on the bottom band's upper edge, inset from the stage's left edge by the stage gutter, a quarter of the viewport's width wide (a viewport-relative width, not multiplied by the chrome factor), and at whatever compact height its content takes. The dock SHALL NOT be top-anchored and SHALL NOT claim the stage's upper-left corner: at the top of the left column the stage shows only the standing portrait line. The condition icon row SHALL be the dock's topmost content, directly above the bars. The dock SHALL be bounded above the band and SHALL scroll internally rather than grow past the band's edge. The dock MAY overlap the lowest strip of the `actor-left` standing portraits (the party line's feet); the portraits keep their full standing height and the dock paints above them. The dock SHALL NOT read as a rectangular box: its ground is the shared panel ink with the backdrop blur, feathered out towards its right and top edges so the scene reads through them, and it is mounted on a hairline brass spine down its left side capped by the band's lozenge ornament, with a hairline brass crown fading out along its top; it carries no full border and no square corners. Every island chrome the dock carries SHALL come from the shared design tokens. The command-line row docked on the same band edge SHALL begin past the dock's right edge, so the two never intersect. Until `companion-portrait-lineup` removes it, the interim party quickbar island stands in the `vitals` anchor between the dock and the band.

#### Scenario: The dock stands on the band's edge
- **WHEN** the shell renders in exploration mode with the vitals dock visible at 1920x1080
- **THEN** the `vitals` anchor's bottom edge coincides with the bottom band's top edge (the dock's own bottom edge does too whenever no interim party quickbar stands below it), the dock's left edge sits at the stage's left gutter and its width is a quarter of the viewport's width (±1.5px), its rendered height is the compact height of the icon row, the readout, and the three lines, and the stage's upper-left corner holds no vitals surface

#### Scenario: The dock covers only the portraits' lowest strip
- **WHEN** the dock is visible and the player's standing portrait renders at 1920x1080 and at 1280x720
- **THEN** the overlap of the two rendered boxes reaches no higher than the portrait's lowest quarter, the portrait's face and torso are fully visible, and neither box moves the other

#### Scenario: The dock stays bounded at the minimum viewport
- **WHEN** the shell renders at 1280x720 with the dock visible and conditions overflowing the row
- **THEN** the dock's box stays inside the left gutter between the top band and the band's top edge, its content scrolls within that bound, and it intersects no other interactive anchor's content

## MODIFIED Requirements

### Requirement: The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces
This requirement carries the `place-card-relocation` amendment; the vitals-anchor wording below moves the anchor from the stage box's top-left corner to the stage's lower-left dock, and the command-line row now begins past that dock.
Fixed CSS-pixel chrome dimensions in this requirement are reference dimensions at viewports up to 1080px tall or 1920px wide. Above both, chrome dimensions scale once under the desktop proportional-scaling contract; viewport-relative band/prose/portrait dimensions are not multiplied again. The named acceptance-size non-overlap rules remain.
The WebClient SHALL render as a full-bleed stage that fills the viewport, with the scene backdrop as
the lowest layer, the portrait anchors above it, the HUD islands above those, the bottom band above
those, and the command line topmost among the persistent surfaces. HUD surfaces SHALL be placed by
named stage anchors — the lower-left `vitals` anchor, the top-right `map` anchor, the portrait anchors
`actor-left` and `actor-right`, the bottom band's two regions `band-message` and `band-command`, the dialogue `choices` anchor, and
the `command-line` row — and SHALL NOT be placed inside a page-scrolling container that can push a
required surface out of view. The stage SHALL carry no separate `place` anchor: the place card is an
island of the `map` anchor.

The top band SHALL be 48px tall at every supported viewport and SHALL carry only the brand, the top
navigation bar, the possession banner when present, the character switcher, and the connection
state; it SHALL carry no location label and no time label. The `vitals` anchor is the stage's lower-left vitals dock that "The vitals dock stands at the stage's lower-left above the band"
defines: bottom-anchored on the band's upper edge in the left gutter, at a quarter of the viewport's width that does not depend on the
content it holds. The `map` anchor SHALL sit at the stage
box's top-right corner, below the top band; its content column (the place card, then the
minimap island, then the objective line, then any other island this capability places there) SHALL be right-aligned to the
stage's right gutter and bounded above the bottom band.

The bottom band SHALL span the full stage width along the stage's bottom edge at one fixed height,
`clamp(260px, 27.8vh, 400px)` with its two px bounds multiplied once by the desktop chrome factor (300px at the 1920x1080 reference viewport, 400px at 2560x1440), taken from a single
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
SHALL be `min(62vh, 680px)` tall but never taller than the stage box, SHALL be inset at least 6% of the
stage width from its own side, and SHALL never cover the band. Where 6% would place the figure's face
(the anchor's horizontal centre) under the island column on its side — the vitals dock's left
gutter on the left, the place card and the minimap card on the right — the inset SHALL grow just enough to clear that column; at
the 1920x1080 reference viewport both insets are exactly 6%, and the compact lower-left dock never
reaches the portrait's face height, so neither inset needs to grow for it. The `actor-left` anchor SHALL carry the
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
box, at most `min(560px, 40%)` of the stage width wide, above the portrait anchors, and its content
SHALL be vertically centred in, and bounded by, the part of the stage box between the top band and the
scene caption row that stands on the command-line row, so it never meets the scene caption or the
expanded command line; when its content is taller
than that span allows it SHALL scroll internally, and it SHALL NOT grow into the top band, the
command-line row, or the bottom band.

At 1920x1080, 1440x900, and 1280x720 no interactive stage anchor (`vitals`, `map`,
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
- **THEN** the top band's rendered height is 48px, no element inside the top band states the location label or the world time, and the place card in the `map` anchor below the top band states both

#### Scenario: The left column carries no place card
- **WHEN** the shell renders in exploration mode with a committed location and world time
- **THEN** no place card renders anywhere in the stage's left column, and the `vitals` anchor's box is not offset by any place card's height

#### Scenario: The dialogue host stands opposite the player
- **WHEN** the committed mode changes from exploration to dialogue at 1920x1080 with an available `dialogue` panel
- **THEN** the `actor-right` anchor renders the host's stage actor, its bottom edge coincides with the band's top edge, its right edge is 6% of the stage width from the stage's right edge, its height equals the player portrait's height, it holds no focusable element, and on the return to exploration `actor-right` renders no content again

#### Scenario: The host's face clears the minimap at the smaller viewports
- **WHEN** the committed mode is dialogue with a committed `local_map` panel at 1440x900 and at 1280x720
- **THEN** the `actor-right` anchor's right inset is at least 6% of the stage width, its horizontal centre lies left of the leftmost edge of the right-hand island column — the place card and the minimap card, which share that column's width — and no interactive stage anchor overlaps another

#### Scenario: The choice list sits over the stage between the portraits
- **WHEN** the dialogue choice list renders four picks and its three trailing rows at 1920x1080, 1440x900, and 1280x720 with the minimap island present and the command line expanded
- **THEN** the `choices` anchor and the list are horizontally centred on the stage box (±1px), lie entirely inside the stage box above the command-line row, intersect no `vitals`, `map`, band, or command-line anchor, and every row is reachable

### Requirement: Location, appearance, and vitals changes transition at the motion level
The stage SHALL animate the following committed changes, taking every duration and distance from the
client's motion tokens, so they follow the effective motion level of "The motion level is a client-local
preference that governs every client animation":
- **A new scene image** SHALL crossfade from the previous image to the new one over the scene duration
  (500ms at `full`). The new image SHALL start its fade only once it is decoded. Until then, the previous
  image SHALL stay visible with the dimmed treatment the backdrop already uses for a prior image, so the
  fade never passes through an empty frame and a previous scene is never presented undimmed as the
  current one. The new image SHALL fade in above the previous one, and the pair SHALL NOT dip through
  the stage behind them mid-fade. The scene label, the alternative text, and the placeholder SHALL
  update at commit.
- **A new location label** SHALL slide the place card's heading in from the left and fade it in, while
  the previous heading fades out. A change of the world time alone SHALL NOT animate.
- **A new current map node** SHALL pan the minimap: the drawing SHALL start where the previous current
  node stood on screen and ease to its committed placement, and the current-node marker SHALL travel
  the step from the node the player left to the new current node, so a move reads even when the drawing
  itself does not shift. When the previous current node is absent from the new placement, the minimap
  SHALL show the new placement at once. The full-map surface SHALL NOT pan.
- **A new response** SHALL clear the message window as "The message window presents the current
  response one page at a time in the band's message region" allows: the previous page fades out over
  the clear duration (150ms at `full` and at `reduced`) while the new page starts at once and surfaces
  beneath it within the same duration, so the two pages never read through each other.
- **A new portrait source** on a stage actor (a new image URL, or a switch between an image and a
  placeholder) SHALL crossfade over the portrait duration (400ms at `full`), and a change of the speaking
  state SHALL ease the dim.
- **The vitals dock** — the condition icon row and the vitals bars as one surface — SHALL fade in while
  rising 12px into its bottom-anchored resting position (entering from 12px below it, so it reads as
  rising out of the band's edge), and SHALL fade out while sinking 12px back toward the band when it
  hides.

At `reduced`, each of these SHALL play as an opacity fade of at most 150ms with no slide, no pan, and no
marker travel, and the dim SHALL change instantly. At `off`, each SHALL render its final state in the commit's frame. No
transition SHALL delay a committed value or the player's input beyond its own duration, as "Presentation
timing never gates committed state or input" requires.

#### Scenario: A new scene crossfades once decoded
- **WHEN** the effective level is `full`, the backdrop shows a done scene, and a committed revision names
  a different done scene URL
- **THEN** the scene label and alternative text read the new values in the commit's frame, the previous
  image stays visible and dimmed until the new image is decoded, and then both images are present while
  the previous one fades out over 500ms, after which only the new image remains

#### Scenario: The place card slides in the new location
- **WHEN** the effective level is `full` and a move commits a new location label, and later only the
  world time changes
- **THEN** the new heading enters from the left with a fade while the old heading fades out, and the
  time-only change swaps the time line with no transition

#### Scenario: The minimap pans to the new node
- **WHEN** the effective level is `full` and a move commits a current node adjacent to the previous one
- **THEN** the minimap's drawing starts offset so the previous current node sits where it stood, and it
  eases to the committed placement over the base duration while the current-node marker travels from
  the node the player left, and the nodes' visibility states, accessible names, and click targets
  already describe the new placement

#### Scenario: The message window clears between responses
- **WHEN** the effective level is `full`, page 1 of a response is on screen, and the player acts
- **THEN** the new response's first page starts typing at once beneath an inert layer holding the
  previous page, which fades out over 150ms and is then removed

#### Scenario: An appearance change crossfades the player's portrait
- **WHEN** the effective level is `full` and the roster's current character portrait changes URL
- **THEN** the player's stage actor shows both portraits while the previous one fades out over 400ms, and
  then only the new one

#### Scenario: The vitals island fades and slides in and out
- **WHEN** the effective level is `full` and a committed revision lowers `hp` from full outside combat,
  and a later revision restores it
- **THEN** the dock fades in while rising 12px from 12px below its resting position, and on
  restore it fades out while sinking 12px toward the band and ends hidden with `display:none`

#### Scenario: Reduced plays short fades with no travel
- **WHEN** the effective level is `reduced` and a move commits a new scene, location, and current node
- **THEN** the backdrop and the place card fade within 150ms with no slide, the minimap shows the new
  placement at once, and the message window's clear fades within 150ms

#### Scenario: Off renders every final state at once
- **WHEN** the effective level is `off` and a move commits a new scene, location, current node, portrait,
  and vitals state
- **THEN** in the commit's frame the backdrop holds only the new image once decoded, and the place card,
  the minimap, the message window, the stage actor, and the vitals dock each hold only their final
  state

### Requirement: The HUD island stack renders as bounded floating islands, not column cards
This requirement carries the `place-card-relocation` amendment; the party quickbar keeps its interim
island inside the dock until `companion-portrait-lineup` removes it.
The surfaces placed in the stage's island anchors SHALL render as floating HUD
islands: a translucent panel fill, a backdrop blur, a hairline border, the shared corner radius, and
the shared drop shadow, each island a separate box separated by the anchor's gap — never a single
boxed column card and never an opaque `<aside>` stacked in a layout column. The `vitals` anchor is the
stage's lower-left vitals dock that "The vitals dock stands at the stage's lower-left above the band"
defines: it carries the condition icon row and the vitals bars as one dock, and SHALL carry
no character head card, no portrait catalog strip, and no top-anchored island; the party quickbar keeps
its compact island in the anchor below the dock until `companion-portrait-lineup` removes it. The dock
itself replaces the boxed island chrome with the feathered instrument plate that "The vitals dock stands at the stage's lower-left above the band" defines. The `map` anchor SHALL carry, in this order, the
place card, the
minimap island, the objective line, the combat participant frame while it is mounted, and the title
ballot menu while it is mounted, each present only while its own requirement renders it; no reference
panel and no portrait anchor content SHALL be placed in either island anchor. Each stack's rendered height SHALL fit within its anchor at both 1440x900 and 1280x720 with
every island populated, so no required island depends on scrolling the anchor to be seen. Every
island's chrome SHALL be expressed through the shared design tokens, so a token change or the
reduced-motion block reaches all of them at once.

#### Scenario: The left anchor renders separate islands
- **WHEN** the shell renders in exploration mode with a vital below its maximum and a committed `harmful` condition
- **THEN** the condition icon row and the vitals bars render as the lower-left dock's two surfaces in that order, the dock carries the feathered, blurred panel ink on its brass spine, and no head card, place card, portrait catalog strip, or top-anchored vitals island is rendered; the interim party quickbar, when a party is committed, stands below the dock

#### Scenario: The populated stack fits its anchor at the minimum viewport
- **WHEN** the shell renders at 1280x720 with every island populated and the condition overflow disclosed
- **THEN** each anchor's content fits inside its anchor, the place card's rendered box does not intersect the minimap island below it, and neither the dock nor the map stack intersects the bottom band, the command line, or the other island anchor's content

#### Scenario: Island chrome comes from the shared tokens
- **WHEN** an island renders
- **THEN** its fill, border, radius, shadow, and transitions resolve from the shared design tokens rather than from per-component literals

#### Scenario: The map anchor stacks its islands in order
- **WHEN** the shell renders in exploration mode with a committed `local_map` panel, a non-empty `objectives` panel, and title-ballot candidates, and later in combat mode
- **THEN** exploration renders the place card, the minimap island, the objective line, and the title ballot menu in that order in the `map` anchor, and combat renders the place card above the participant frame there with no minimap and no objective line

### Requirement: The vitals island is shown only in combat or while a vital or a condition needs attention
The HUD SHALL show the vitals dock — the condition icon row together with the vitals bars — only while at least one of these holds for the committed state: the committed mode is `combat`; the derived low-HP presentation state is true; any `status.resources` vital (hp, mp, sp) carries a numeric `current` below its numeric `maximum`; or `status.conditions` carries at least one entry whose `severity` is `warning`, `harmful`, or `critical`. A condition whose `severity` is `beneficial` or `informational` — including a passive `skill_owned` combat-modifier row — SHALL NOT by itself make the dock visible, and neither SHALL an entry with a missing or unknown `severity`. While the dock is visible its condition icons SHALL render every committed condition, whatever its severity. Otherwise the dock SHALL be hidden: from the moment the committed revision turns the rule false it SHALL leave the accessibility tree, the tab order, and pointer hit-testing, and once its exit transition has finished it SHALL be `display:none` and contribute no visible box. The dock SHALL enter and leave with a fade and a 12px slide at the client's motion level (`webclient-contextual-hud` "Location, appearance, and vitals changes transition at the motion level"); at `off` it is shown and hidden in the same frame as the commit. The rule SHALL be derived client-side from the committed `status` panel and the committed mode alone: no server field, request, or timer is involved, and a vital that is absent from the payload or carries a non-numeric field SHALL NOT count as below its maximum. Dialogue mode SHALL follow the same rule as exploration; creation mode hides the dock through the visibility matrix; an unavailable `status` panel renders no vitals dock at all.

While hidden, the dock SHALL keep its trailing-bar memory, so the first committed revision that lowers a vital from full shows the dock with the trailing bar lagging from the previously committed ratio exactly as an always-visible dock would. When a committed revision turns the rule false while focus is inside the dock, focus SHALL move to the action dock before the dock is hidden, through the same focus-restore path a mode change uses.

#### Scenario: Full health outside combat hides the island
- **WHEN** the committed mode is exploration, every committed vital's `current` equals its `maximum`, and `status.conditions` is empty
- **THEN** the vitals dock is absent from the accessibility tree and the tab order, and once any exit transition has finished it is hidden with `display:none` and no bars, numerals, icons, or low-HP marker are visible

#### Scenario: A vital below its maximum shows the island
- **WHEN** a committed revision in exploration mode carries `mp` at 40 of 60 with no condition
- **THEN** the vitals dock renders with every vital's icon, label, and on-track `current / maximum` numerals

#### Scenario: A condition shows the island at full health
- **WHEN** a committed revision in exploration mode carries full vitals and one condition whose `severity` is `harmful`
- **THEN** the dock renders its bars and the condition icon

#### Scenario: A beneficial-only condition keeps the island hidden at full health
- **WHEN** a committed revision in exploration mode carries full vitals and only conditions whose `severity` is `beneficial`, such as a passive `skill_owned` combat-modifier row
- **THEN** the dock stays hidden with `display:none` and none of its condition icons is visible or focusable, and no enter transition plays

#### Scenario: Visible island renders every condition chip
- **WHEN** the dock is visible because a vital is below its maximum and the committed conditions carry one `beneficial` and one `informational` entry
- **THEN** the icon row renders both condition icons

#### Scenario: Combat always shows the island
- **WHEN** the committed mode is combat with every vital full and no condition
- **THEN** the vitals dock renders

#### Scenario: The first hit from full health keeps its trailing bar
- **WHEN** the dock is hidden at full health and the next committed revision in the same epoch lowers `hp`
- **THEN** the dock renders, the hp fill shows the new ratio, and the trailing bar starts from the previously committed full ratio

#### Scenario: Focus is rescued before the island hides
- **WHEN** focus is on a `harmful` condition icon outside combat with every vital full, and a committed revision clears that condition, leaving only `beneficial` conditions
- **THEN** focus moves to the action dock before the dock is hidden, and no focus is lost to the document body

### Requirement: Vitals read as one numeral readout over three thin trailing-bar lines
Each of hp, mp, and sp SHALL render as one thin trailing-bar line, the three laid almost edge to edge — parted by a hairline seam, in hp, mp, sp order from the top — under one numeral readout row that states, in the same order, each gauge's icon and its `current / maximum` numerals — or, for hp while a combat round plays, the displayed value that `webclient-combat-menu` "A combat round plays beat by beat" defines. The icons SHALL be three distinct shapes in their gauge's hue, so the readings are told apart without colour; each gauge's Traditional Chinese label (生命, 魔力, 耐力) SHALL be its reading's accessible name and SHALL NOT be rendered as visible text. The 危險 low marker SHALL render with the hp reading. The current value SHALL lead in the brightest paper ink at tabular figures and the maximum SHALL recede a step, every value in a contrast that keeps it legible over the dock, so no vital state is conveyed by the coloured fill alone. The lines SHALL NOT read as square boxes: each SHALL taper to a point at its far end, and each line SHALL run a little shorter than the one above it, so the set fans out rather than ending on one hard edge. The readout and the three lines together SHALL occupy well under half the previous vitals island's row block. The sp fill SHALL carry a non-colour texture distinguishing it from the hp and mp fills.

The trailing bar SHALL exist to make damage taken visible: it SHALL lag the fill when the ratio falls and SHALL be overtaken by the fill when the ratio rises. It SHALL be decorative — hidden from the accessibility tree, carrying no accessible name, and conveying nothing the numerals do not already carry on the same revision. It SHALL NOT render any value that was not a previously displayed ratio of that same gauge, where a displayed ratio comes only from the committed `status` or from a committed beat's `hp_after` during a round's playback, SHALL NOT be interpolated or extrapolated from narrative text or an action result, and SHALL reset to the current ratio when the epoch changes, so no trail is drawn across a reconnect. Its motion SHALL be token-gated so the reduced-motion block disables it. At the `full` motion level the trailing bar SHALL start following a drop 300ms after the fill moves.

A vital at or below the client's display threshold SHALL be marked by both a recolour and an explicit text marker, never by the recolour alone.

#### Scenario: Each vital is legible without colour
- **WHEN** the vitals dock renders with the `status` panel committed
- **THEN** the readout states hp, mp, and sp in that order, each as a distinct icon shape with its `current / maximum` numerals and its gauge label as the reading's accessible name, no gauge label is visible text, the three lines below carry no text, and the sp fill is distinguishable from hp and mp by texture rather than by hue

#### Scenario: Damage leaves a visible trailing bar
- **WHEN** a committed revision lowers a gauge's ratio
- **THEN** the fill moves to the new ratio and the trailing bar follows behind it, so the gap between them shows the amount lost, and the numerals show the new value immediately

#### Scenario: Healing shows no trailing bar
- **WHEN** a committed revision raises a gauge's ratio
- **THEN** the fill overtakes the trailing bar and no lagging gap is drawn

#### Scenario: The trailing bar follows a round's displayed hit points
- **WHEN** a playing combat round shows the player's hp stepping from 40 to 28 and then to 15 of 60
- **THEN** the numerals and the fill show each displayed value in turn, the trailing bar lags each drop from the previously displayed ratio, and once the round ends the numerals and fill show the committed value

#### Scenario: The trailing bar never shows an uncommitted value
- **WHEN** the trailing bar renders at any point
- **THEN** its width corresponds to a ratio that was previously displayed for that same gauge — a committed `status` value, or a committed `combat_beats` beat's `hp_after` during that round's playback — never a value from neither source, and it is absent from the accessibility tree

#### Scenario: A reconnect does not draw a trail across epochs
- **WHEN** a new epoch's snapshot commits after a reconnect
- **THEN** the trailing bar resets to the current ratio and no gap is drawn between the pre-reconnect and post-reconnect values

#### Scenario: A low vital is marked by text as well as colour
- **WHEN** a vital falls to or below the client's display threshold
- **THEN** the hp reading carries both the low recolour and the explicit 危險 text marker, and the numerals continue to render

#### Scenario: The three lines read as one instrument
- **WHEN** the vitals dock renders three gauges
- **THEN** the three lines are parted by a 1px seam, each tapers to a point at its far end and runs shorter than the one above it, and the readout plus the three lines render in a height no greater than half of the previous island's three header-plus-track rows

### Requirement: Condition icons float without a window and disclose their detail in a tooltip
The active conditions SHALL NOT render as a chipped island with a background window, header, or border. Each entry in `status.conditions` SHALL instead render as a standalone small icon in a row directly above the vitals readout, carrying only its per-severity shape glyph — the five severities each mapping to a distinct glyph so no two are separated by colour alone, with the beneficial and harmful directions readable from the glyph itself. The row SHALL carry no panel fill, no backdrop blur, and no `狀態` label.

The condition's readable name — its label, or its code only when no label is supplied — its remaining duration, and every derived modifier SHALL NOT be shown on the icon; they SHALL appear in a tooltip opened when the icon is hovered or when keyboard focus reaches it, and closed on pointer leave, blur, or Escape. The tooltip SHALL state the full label, the duration when the payload supplies one, and every derived modifier the payload provides, each modifier named in the game's stat vocabulary (for example 攻擊, 敏捷, 防禦, 準度, 每回合行動, 魔力消耗) rather than by its raw adjustment key, with its value verbatim — no sign, unit or digit added or dropped — and a key outside that vocabulary SHALL be named by the neutral 其他修正 and keep its value. The icon SHALL also carry this content as its accessible name, so the information is reachable by assistive technology without the pointer. The duration the tooltip states is the payload's `remaining_seconds` value as committed; the client SHALL run no countdown and SHALL NOT re-render the tooltip between commits.

Icons SHALL be bounded to the row's width, and the remainder SHALL stay reachable in one action through a trailing `+N` icon stating how many are hidden, which discloses the hidden conditions as the same tooltip content for each. An empty condition list SHALL render no icon row at all — no placeholder, no `無條件` text — consistent with the contextual-hiding rule that an absent surface is not a dimmed or emptied surface.

#### Scenario: A chip carries its label, duration, and modifiers
- **WHEN** a beneficial and a harmful condition are committed
- **THEN** the row above the vitals readout renders exactly two glyphs of distinct shapes with no panel chrome, no condition names, and no duration text visible, and each icon's accessible name states its label, remaining duration, and every modifier's readable name with its verbatim value

#### Scenario: Two severities are distinguishable without colour
- **WHEN** a warning condition and a harmful condition are committed together
- **THEN** their icons carry different glyph shapes and remain distinguishable with colour removed

#### Scenario: Hovering a condition icon discloses its detail
- **WHEN** the pointer rests on a condition icon whose payload carries a label, a remaining duration, and a derived modifier
- **THEN** a tooltip appears stating the full label, the duration, and the modifier's readable name with its verbatim value, and it closes when the pointer leaves or Escape is pressed

#### Scenario: Keyboard focus reaches the same tooltip
- **WHEN** keyboard focus reaches a condition icon
- **THEN** the same tooltip opens, and Escape closes it without stealing the shell's drawer or dock Escape when no tooltip is open

#### Scenario: A condition without a duration renders no badge
- **WHEN** a committed condition carries no `remaining_seconds`
- **THEN** its tooltip renders no duration text and no substitute value

#### Scenario: The duration does not tick between revisions
- **WHEN** a tooltip showing a duration is displayed and no new revision commits
- **THEN** the tooltip continues to show the payload's value unchanged, and the client runs no countdown

#### Scenario: Overflowing conditions stay reachable
- **WHEN** more conditions are committed than the row shows
- **THEN** a trailing `+N` icon states the hidden count and discloses every hidden condition's full tooltip content in one action, and no committed condition becomes unreachable at any count the payload permits

#### Scenario: No conditions renders no island
- **WHEN** the committed condition list is empty
- **THEN** no condition icon or row is rendered anywhere in the HUD

#### Scenario: Long names stay bounded and complete
- **WHEN** conditions with long labels are committed
- **THEN** no icon is sized by its label, and every icon's tooltip states its full label and localized modifiers without truncation

#### Scenario: Unknown modifier keys keep their values
- **WHEN** a condition carries a known and an unknown modifier key
- **THEN** the tooltip names the known key in the stat vocabulary, names the unknown key 其他修正, and keeps both original values verbatim with their signs and units
