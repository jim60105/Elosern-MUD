## MODIFIED Requirements

### Requirement: The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces
Fixed CSS-pixel chrome dimensions in this requirement are reference dimensions at viewport heights up to 1080px. Above that height chrome dimensions scale once under the desktop proportional-scaling contract; viewport-relative band/prose/portrait dimensions are not multiplied again. The named acceptance-size non-overlap rules remain.
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
SHALL be `min(62vh, 680px)` tall but never taller than the stage box, SHALL be inset at least 6% of the
stage width from its own side, and SHALL never cover the band. Where 6% would place the figure's face
(the anchor's horizontal centre) under the island column on its side — the place card and vitals on
the left, the minimap card on the right — the inset SHALL grow just enough to clear that column; at
the 1920x1080 reference viewport both insets are exactly 6%. The `actor-left` anchor SHALL carry the
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

#### Scenario: The host's face clears the minimap at the smaller viewports
- **WHEN** the committed mode is dialogue with a committed `local_map` panel at 1440x900 and at 1280x720
- **THEN** the `actor-right` anchor's right inset is at least 6% of the stage width, its horizontal centre lies left of the minimap card's left edge, and no interactive stage anchor overlaps another

#### Scenario: The choice list sits over the stage between the portraits
- **WHEN** the dialogue choice list renders four picks and its three trailing rows at 1920x1080, 1440x900, and 1280x720 with the minimap island present and the command line expanded
- **THEN** the `choices` anchor and the list are horizontally centred on the stage box (±1px), lie entirely inside the stage box above the command-line row, intersect no `place`, `vitals`, `map`, band, or command-line anchor, and every row is reachable
