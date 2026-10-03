# webclient-contextual-hud Specification

## Purpose
The full-bleed cinematic stage with its anchored HUD surfaces (scene backdrop, message window,
HUD islands, action dock, command line), the committed-mode visibility matrix, the truthful scene
backdrop, the paged message window, drawer/overlay stage recessing, and the action-dock
re-chrome contract: the fixed bottom band's command region, the combat root's vertical command list with its truthful skills count,
the router-derived breadcrumb, the per-kind row vocabulary, the display-only combat participant
frame, the bounded skill master-detail, and the two-step destructive confirmation.

## Requirements

### Requirement: The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces
This requirement carries the `place-card-relocation` and `vitals-bar-redesign` amendments; the party-line wording below replaces the solo-portrait wording of the `actor-left` anchor.
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
defines: bottom-anchored on the band's upper edge in the left gutter, at the left column's fixed width that does not depend on the
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
(the anchor's horizontal centre) under the island column on its side — the vitals stack on
the left, the place card and the minimap card on the right — the inset SHALL grow just enough to clear that column; at
the 1920x1080 reference viewport both insets are exactly 6%, and the compact lower-left dock never
reaches the portrait's face height, so neither inset needs to grow for it. The `actor-left` anchor SHALL carry the
controlled character's stage actor — the current roster character's portrait, or the possessed
companion's while the possession banner is available — with the committed party's companion stage
actors lined up behind it as "Companion standing portraits line up behind the controlled character in
the actor-left anchor" defines, each with the truthful placeholder when no image exists, in
exploration, dialogue, and combat mode. The `actor-right` anchor SHALL carry the dialogue host's stage
actor while the committed mode is `dialogue`, the committed `dialogue` panel is available, and its host identity does not already join to a committed party or controlled lineup figure, SHALL carry
the foe line-up that "Foes stand opposite the player during combat" defines while the committed mode is
`combat` and at least one foe is active, or while a round that ended the fight still plays as "Combat
beats are choreographed on the stage at the motion level" defines, and SHALL carry no content in every
other state. The foe
line-up MAY extend leftward beyond the `actor-right` anchor's own box, within the bounds that
requirement sets, and SHALL NOT cross the stage's horizontal centre, which the companion line-up's
figures also never cross. Every stage actor follows "Stage actors present the player and the dialogue host with
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
- **THEN** the `actor-left` anchor renders that portrait frontmost, its bottom edge coincides with the band's top edge, its height is `min(62vh, 680px)` (±1px), its left edge is 6% of the stage width from the stage's left edge, it holds no focusable element, and the `actor-right` anchor renders no content

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
- **WHEN** the committed mode changes from exploration to dialogue at 1920x1080 with an available `dialogue` panel whose host is not already in the party lineup
- **THEN** the `actor-right` anchor renders the host's stage actor, its bottom edge coincides with the band's top edge, its right edge is 6% of the stage width from the stage's right edge, its height equals the player portrait's height, it holds no focusable element, and on the return to exploration `actor-right` renders no content again

#### Scenario: The host's face clears the minimap at the smaller viewports
- **WHEN** the committed mode is dialogue with a committed `local_map` panel at 1440x900 and at 1280x720
- **THEN** the `actor-right` anchor's right inset is at least 6% of the stage width, its horizontal centre lies left of the leftmost edge of the right-hand island column — the place card and the minimap card, which share that column's width — and no interactive stage anchor overlaps another

#### Scenario: The choice list sits over the stage between the portraits
- **WHEN** the dialogue choice list renders four picks and its three trailing rows at 1920x1080, 1440x900, and 1280x720 with the minimap island present and the command line expanded
- **THEN** the `choices` anchor and the list are horizontally centred on the stage box (±1px), lie entirely inside the stage box above the command-line row, intersect no `vitals`, `map`, band, or command-line anchor, and every row is reachable

### Requirement: Surface visibility is gated by the committed game mode
This requirement carries the amendments from `place-card-relocation` (place card in the `map` anchor), `vitals-bar-redesign` (the vitals dock at the lower left), and `companion-portrait-lineup` (the party quickbar row removed, the portrait row naming the companion line). Dialogue mode now hides the cockpit and navigation surfaces: the place card, the minimap island, and the vitals dock are hidden while the committed mode is `dialogue`.
The shell SHALL expose the committed mode on the stage root as `data-elosern-mode`, and surface
visibility SHALL be derived from that single attribute. A surface hidden for the current mode SHALL be
removed from rendering with `display:none` — never dimmed, never merely visually hidden — so it leaves
the accessibility tree and the tab order. The one exception is the band's command region in dialogue
mode, which animates out as "The command region collapses in dialogue mode and the message window spans
the band" defines: it leaves the accessibility tree, the tab order, and pointer hit-testing at the
commit, and is `visibility: hidden` once its slide ends. The second exception is the combat stage
hold: while a round whose publication already committed another mode still plays, as "Combat beats are
choreographed on the stage at the motion level" defines, the decorative combat veil and the foe line-up
MAY remain on the stage, outside the accessibility tree, the tab order, and pointer hit-testing, and the
scene backdrop SHALL keep presenting the combat stage (its combat gradient and, where a bundled sample
wash accompanies a degraded scene, the combat sample), until the round ends; every other surface
follows the committed mode at the commit. Dialogue's `vitals` and `map` anchors MAY retain exit paint
over the existing reveal duration while inert, outside the accessibility tree and pointer hit-testing
from commit, and SHALL settle at `display:none`. Mount, reconnect, motion-off, and browsers without
discrete display transitions SHALL hide them immediately. The matrix SHALL be:

| Surface | exploration | combat | dialogue | creation |
|---|---|---|---|---|
| place card (location, world time; `map` anchor, above the minimap) | visible | visible | **hidden** | hidden |
| message window (band message region) | visible | visible | visible (whole band width, paged, name plate) | hidden |
| dialogue choice list (`choices` anchor, centred over the stage) | not rendered | not rendered | once the current response's last page is fully shown, while no action is in flight | not rendered |
| vitals dock (condition icons + vitals bars; `vitals` anchor, lower-left) | by the vitals rule | visible | **hidden** | hidden |
| minimap island | visible | **hidden** | **hidden** | hidden |
| objective line (under the minimap) | visible | hidden | hidden | hidden |
| controlled character and companion standing portraits (`actor-left`) | visible | visible | visible (listeners dimmed while the host speaks; the party line stays) | hidden |
| dialogue host standing portrait (`actor-right`) | not rendered | not rendered | while the `dialogue` panel is available (dimmed while the player speaks) | not rendered |
| foe line-up (`actor-right`, at most three active foes) | only while a round that ended the fight still plays (held, inert) | while at least one foe is active | not rendered | not rendered |
| action dock (band command region) | visible | visible | **hidden** (command region collapsed: inert at commit, slides out, then `visibility: hidden`) | visible (creation form, full band width) |
| command-line toggle (⌨, message region's bottom-right) | visible | visible | visible | hidden |
| log control (日誌, beside the command-line toggle) | visible | visible | visible | hidden |
| command line (row on the message region's top edge) | while expanded | while expanded | while expanded | hidden |
| scene backdrop | visible (exploration stage; the combat stage while a round that ended the fight still plays) | visible (combat stage) | visible (unchanged art) | visible |

While the committed mode is `dialogue` the scene backdrop SHALL keep rendering its committed
exploration art truthfully — the dialogue's focus is carried by the stage actors, the name plate, and
the message window, and the choice list, not by mutating the backdrop. Per-surface requirements that name their own visible-mode
sets SHALL stay consistent with this matrix. A cell that names a data rule instead of `visible` means
the surface is shown in that mode only while its own requirement's rule holds for the committed state,
and is otherwise hidden the same way (`display:none`, or not rendered at all where that requirement
says so). The command line's `while expanded` cell is such a rule: its own requirement defines when the
row is expanded, and a collapsed row is hidden with `display:none` exactly like a mode-hidden surface.
The place card's visibility SHALL follow this matrix exactly: it is shown in exploration and combat,
hidden in dialogue and creation; hiding the `map` anchor in dialogue hides the place card with the
minimap, and the card's own visibility rule SHALL NOT claim dialogue after this change.
The vitals dock SHALL be hidden in dialogue mode through the mode gate regardless of its data rule:
a committed revision while dialogue holds — a vital dropping below its maximum, a new condition —
SHALL NOT reveal the dock, and the dock's reveal transition SHALL NOT play until the mode leaves
dialogue. The dialogue's attention surface is the message window and the name plate; the dock returns
through its normal reveal when the mode commits back to exploration or combat. The low-HP stage
vignette is not mode-gated and keeps rendering in dialogue, so a critical HP state is still conveyed
through the stage frame.
Each playing mode has one focus home: the action dock in exploration, combat, and creation mode, and
the message window's focus target in dialogue mode, as "The command region collapses in dialogue mode
and the message window spans the band" defines. When a mode change, a committed revision that turns a
surface's data rule false, or a collapse of the command line hides the surface that currently holds
focus, the shell SHALL move focus to the focus home of the mode being entered or kept before the
surface is removed, using the existing focus-restore path. A mode change into creation SHALL also
collapse the command line, so leaving creation never reveals an expanded row.

#### Scenario: The minimap disappears in combat
- **WHEN** the committed mode changes from exploration to combat
- **THEN** the minimap island is absent from the DOM layout and from the tab order, and it is not merely dimmed, while the participant frame renders in the `map` anchor below the still-visible place card and the foe line-up renders in `actor-right`

#### Scenario: The place card stays visible through combat
- **WHEN** the committed mode changes from exploration to combat with a committed location and world time
- **THEN** the place card remains rendered above the participant frame, and returns to standing above the minimap island when the mode returns to exploration

#### Scenario: The minimap returns on leaving combat
- **WHEN** the committed mode changes from combat back to exploration, including by a round whose beats
  are still playing
- **THEN** the minimap island renders again with the committed `local_map` payload at the commit, and any
  held foe line-up or veil is inert and outside the accessibility tree

#### Scenario: A held round keeps the combat backdrop
- **WHEN** the committed art panel carries no usable scene image, a round that ends the fight by a flee
  commits mode `exploration` while its beats still play, and later the round ends
- **THEN** during the hold the scene backdrop keeps the combat gradient and the combat sample wash
  behind the held foe line-up and veil, and only when the hold ends does it return to the exploration
  stage, crossfading over the scene duration at `full` and switching in one frame at `off`

#### Scenario: Focus is rescued before its surface is hidden
- **WHEN** the focused element belongs to a surface that the incoming mode hides, including a scene-overview chip when the incoming mode is dialogue
- **THEN** focus is moved to the incoming mode's focus home before the surface is removed, and no focus is lost to the document body

#### Scenario: Creation mode presents only the creation surfaces
- **WHEN** the committed mode is creation
- **THEN** the place card, the message window, the command-line toggle, the log control, the `vitals` and `map` anchors with every island in them, the player and companion standing portraits, and the command line are absent, and the action dock renders the creation form across the whole bottom band

#### Scenario: Dialogue mode keeps the cockpit visible
- **WHEN** the committed mode changes from exploration to dialogue with an available `dialogue` panel
- **THEN** the message window spans the whole band with the host's name plate, the dialogue host's standing portrait is rendered in `actor-right`, the player's front figure and the companion standing portraits remain rendered in `actor-left` dimmed as listeners, the command-line toggle and the log control remain rendered, the command line keeps its expanded or collapsed state, the action dock is out of the accessibility tree and the tab order together with the band's command region from the commit and is `visibility: hidden` once the region's slide ends, and the `#action-dock` element is not removed from the document

#### Scenario: Dialogue mode hides the cockpit and navigation islands
- **WHEN** the committed mode changes from exploration to dialogue with a committed location, a committed `local_map` panel, and a vital below its maximum
- **THEN** the place card, the minimap island, the objective line, and the vitals dock are absent from the accessibility tree and the tab order, and once each surface's exit transition has finished it is `display:none`

#### Scenario: A vital change during dialogue does not reveal the dock
- **WHEN** the committed mode is dialogue with the dock hidden and a committed revision lowers `hp` below its maximum
- **THEN** the vitals dock stays `display:none`, no reveal transition plays, and the numerals are not visible anywhere on the stage

#### Scenario: Returning from dialogue restores the hidden surfaces
- **WHEN** the committed mode changes from dialogue back to exploration with a vital below its maximum
- **THEN** the place card and the minimap island render again at the commit, and the vitals dock enters through its reveal transition because the vitals rule holds

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

### Requirement: The scene backdrop renders the art payload truthfully behind the stage
The stage backdrop SHALL render the committed `art` panel's scene: the same-origin image with
cover-style cropping when the scene status is `done`; the previously rendered image visibly dimmed and
labelled `目前場景圖片生成中` when the scene is pending and a prior image exists; and the mode's
gradient stage otherwise — for a missing, failed, or invalid asset, for a pending scene with no prior
image, and when the `art` panel is unavailable. A bundled decorative sample MAY accompany this
fallback only with a visible caption distinguishing it from an actual scene image, while retaining
the authoritative missing/pending/unavailable label; the sample caption and that label SHALL share one
status badge, so the stage shows at most one status badge at a time, and the badge SHALL NOT show a
raw placeholder kind code or an error-styled (dashed seal-red) frame. Samples SHALL NOT enter the art catalog or
change its status, and SHALL disappear when an actual or labelled prior scene renders.
Decorative portrait samples SHALL likewise be labelled separately from the current subject;
an available committed player-roster portrait takes precedence, and a load failure returns to
an explicitly labelled sample instead of attributing that sample to the player.
While the combat hold of "Surface visibility is gated by the committed game mode" is playing, the
backdrop MAY keep presenting the combat gradient stage (and the combat sample wash where a degraded
scene carries one), yet it SHALL NOT hold the pre-terminal scene's identity: a newer committed scene
image, pending state, or truthful degradation follows the rules above beneath the held decoration at
its commit, and the scene caption row names the newly committed scene, never the held combat one.
The backdrop SHALL NOT present an invented image as authoritative and
SHALL NOT present a stale image as current. The scene label, its alternative text, and any truthful
placeholder label SHALL be rendered as text outside the bitmap, so no required information exists only
inside an image. The gradient stage SHALL differ per mode (exploration, dialogue, combat) and SHALL
carry an inset vignette. The backdrop's image SHALL be cover-cropped to the stage box (from the top
band's lower edge to the bottom band's upper edge), so no part of the scene the crop keeps is hidden
behind the bottom band.

The backdrop's own floating caption elements (the status badge, the `目前場景圖片生成中`
pending notice, the scene label and alternative-text captions, and the full-view control) SHALL be
positioned so that none of them overlaps the bottom band, the action dock's, or the command line's
rendered content, at 1920x1080, 1440x900, and 1280x720 — extending the sibling stage requirement's
general anchor non-overlap invariant to these backdrop-internal captions, which sit outside the named
stage anchors but are absolutely positioned within the same full-bleed stage.
The scene caption row SHALL render only while an actual scene image is on the stage — a `done` scene
image, or the dimmed prior image of a pending scene — and SHALL NOT render for a missing, failed,
invalid, or unavailable scene, whose truthful label the status badge already states. Within the row the
alternative text SHALL be omitted when it is identical to the scene label, and the full-view control
SHALL be an icon button whose accessible name is `開啟場景全圖`.
The scene label, the alternative text, the pending notice, and the full-view control SHALL render as
one caption row on the stage box's lower edge, standing just above the command-line row docked on the
band's top edge, and centred in the open stage between the `actor-left` and `actor-right` anchor boxes —
or, while the foe line-up stands in combat, between the `actor-left` anchor box and the line-up's
leftmost foe, until a leaving line-up has faded — so no portrait anchor (which paints above the
backdrop), no foe, and no other HUD surface covers any part of it in any mode. The alternative text SHALL
give way before the scene label when the row is too narrow for both. The row SHALL stay one line tall: a label or alternative text longer than the row SHALL end
in an ellipsis on screen while its full text stays in the DOM, and the dialogue choice list SHALL stop
above the row.

#### Scenario: A done scene paints the stage
- **WHEN** the committed art panel carries a `done` scene with a same-origin URL
- **THEN** the backdrop renders that image cover-cropped to the stage box behind every HUD surface, and the scene label and alternative text render as text outside the bitmap

#### Scenario: A missing scene degrades to the mode gradient
- **WHEN** the committed art panel carries a missing, failed, or invalid scene
- **THEN** the backdrop renders the current mode's gradient stage with the truthful placeholder label as text, and no image element carries a URL

#### Scenario: A degraded scene shows one status badge and no caption row
- **WHEN** the `art` panel is unavailable, or the scene is missing, and the bundled sample wash renders
- **THEN** exactly one status badge renders, stating both the sample caption and the truthful
  placeholder label, without a raw kind code, and no scene caption row, scene label, alternative text,
  or full-view control renders

#### Scenario: An alternative text equal to the label is not repeated
- **WHEN** a `done` scene's alternative text is identical to its label
- **THEN** the caption row renders the label once and no alternative-text element

#### Scenario: An unavailable art panel is indistinguishable from an ungenerated scene
- **WHEN** the `art` panel commits its unavailable form
- **THEN** the backdrop renders the mode gradient stage exactly as for a missing asset, with no broken image frame and no gameplay surface blocked

#### Scenario: A pending scene keeps its prior image labelled
- **WHEN** the scene is pending and a prior scene image is already rendered
- **THEN** the backdrop keeps that image visibly dimmed with the explicit `目前場景圖片生成中` label, and never presents it as the current scene

#### Scenario: The combat stage is visually distinct
- **WHEN** the committed mode is combat and no scene image is available
- **THEN** the backdrop renders the combat gradient stage, visually distinct from the exploration stage

#### Scenario: The truthful-placeholder caption never intrudes on the action dock
- **WHEN** the `art` panel is unavailable or the scene is missing/failed, so the status badge
  renders
- **THEN** the status badge's rendered bounding box intersects neither the bottom band's nor the
  command line's rendered bounding box at 1920x1080, 1440x900, or 1280x720

#### Scenario: The scene label, alt text, and full-view control clear the dock at both viewports
- **WHEN** the scene label, alternative-text caption, pending notice, or full-view control render above
  the band
- **THEN** each one's rendered bounding box stays above the bottom band's top edge and above the
  command-line row, at 1920x1080, 1440x900, and 1280x720

#### Scenario: The scene caption stands on the stage floor between the portraits
- **WHEN** the scene label, alternative text, and full-view control render with the command line expanded
  at 1920x1080, 1440x900, and 1280x720
- **THEN** their caption row's bottom edge lies at most 16px above the command-line row's top edge, the
  row is horizontally centred between the `actor-left` and `actor-right` anchor boxes (±1.5px), and each
  part lies between those boxes with no other surface painted over it

#### Scenario: The scene caption clears the foe line-up
- **WHEN** a combat snapshot commits one, two, and three active foes with the command line expanded at
  1920x1080, 1440x900, and 1280x720
- **THEN** the caption row lies between the `actor-left` anchor box and the leftmost foe's box, horizontally
  centred between them (±1.5px), with no foe painted over any of its parts

### Requirement: The message window presents the current response one page at a time in the band's message region
The narrative SHALL render as a message window that fills the bottom band's message region — the left
two thirds of the band, or the whole band in dialogue mode, at the band's fixed height — drawn with the
reference's caption panel
treatment: charcoal panel fill, a hairline border, shared radius and restrained shadow. The window
SHALL never grow into the stage and SHALL never change size with its content. In every mode, dialogue
included, the window SHALL present exactly one page of the current response at a time, paged as
`webclient-input-narrative` defines and revealed as its typing requirement defines — or, while the
current response carries a combat round the client presents, as that round's beat pages followed by the
response's remaining lines, as `webclient-combat-menu` "A combat round plays beat by beat" defines — and
SHALL NOT present earlier responses: they remain readable in the full-log surface. The one exception is the clear
transition: when a new response replaces the previous one, the previous page MAY remain only as an
opaque layer over the new page that fades out within the clear duration of the client's motion level
(at most 150ms, and none at `off`), carries no focusable element, and is outside the accessibility
tree and pointer hit-testing from the moment the new response starts. Page text SHALL be set in the
serif reading face at 28px at the 1920x1080 reference size and the default prose scale, SHALL scale
with the viewport height and with the client's prose scale, and SHALL hold at most 42 CJK characters
per line in every mode, including the whole-band width of dialogue mode.

The window's lower edge SHALL keep a control strip in which no page text renders. The strip SHALL
hold a page marker and, at its right end, a labelled `日誌` control beside the command-line toggle.
The page marker SHALL render only while the page on screen is fully shown, and SHALL be absent while
the page is typing and while a combat round plays by itself. When rendered, it SHALL read `▼` while the current response has further pages and
`■` on its last page. It SHALL be decorative (hidden from assistive technology), and it SHALL blink
only through the client's motion tokens, so reduced motion stops the blink. An oversize page SHALL
scroll inside the window's text area; it SHALL never be truncated and SHALL never grow the window.

The `日誌` control SHALL open the full-log surface in one action. Scrolling up over a page that has
nothing left to scroll up SHALL also open it. The full-log surface's content, markup renderer, focus
trap, Escape close, focus restore to the opening control, and opening at its latest line are
unchanged. The window SHALL render no unread indicator and no jump-to-latest control, and no head row
other than the dialogue name plate. In creation mode the window, its marker, and the `日誌` control are
hidden with the message region.

While the committed mode is `dialogue` and the committed `dialogue` panel is available, the window SHALL
carry a name plate above its text area, naming the host with the panel's `display_name` plus
` ‧ 羈絆 <stage>` only when `bond_stage` is non-null; the window's text area below the plate SHALL
present the current response's pages — the session line as the narrative delivered it, paged and typed
like any response, with no separate reply box, no rows, no avatar, and no text removed or rewritten
from the narrative lines. The window SHALL carry no choice, free-dialogue, or exit row: those are the
dialogue choice list's. While mode is `dialogue` but the panel is unavailable (the transient window
between a clear seam and its commit), the window SHALL render no name plate. The window SHALL make known
to the shell, from its own reader state and never from narrative prose, whether the current response's
last page is on screen, fully shown, with no pending action mark — the moment the dialogue choice list
waits for.

#### Scenario: The window keeps the message region's box
- **WHEN** the current response holds more text than one page and new lines keep arriving
- **THEN** the window keeps the message region's box — the band's height and two thirds of its
  width, or the whole band in dialogue mode — and never expands into the stage

#### Scenario: One page of the current response is shown
- **WHEN** the log holds three responses and the latest one fills two pages
- **THEN** the window shows only the first page of the latest response, and once the clear transition
  has finished no line of the two earlier responses is rendered in the window

#### Scenario: The page measure is bounded at the reference size
- **WHEN** the stage renders at 1920x1080 with the default prose scale and a long prose response, in exploration mode and in dialogue mode with the panel transiently unavailable
- **THEN** the page text's computed font size is 28px (±0.5px) and no rendered text line holds more
  than 42 CJK characters in either mode

#### Scenario: The marker names more pages and the last page
- **WHEN** the current response has two pages, page 1 types to its end, and the player advances
  once and page 2 types to its end
- **THEN** no marker renders while either page is typing, the marker reads `▼` once page 1 is fully
  shown and `■` once page 2 is fully shown, and it is absent from the accessibility tree

#### Scenario: The log control opens the complete log in one action
- **WHEN** the player activates the `日誌` control and then presses Escape
- **THEN** the full-log surface opens at its latest line showing every retained line, including
  input lines and every page of earlier responses, rendered through the same markup renderer, and
  Escape closes it with focus returned to the `日誌` control

#### Scenario: Scrolling up opens the complete log
- **WHEN** the player scrolls up with the wheel over a page that is not scrollable
- **THEN** the full-log surface opens

#### Scenario: An oversize page scrolls inside the window
- **WHEN** the current response's page is a box-drawing map taller than the text area
- **THEN** the map scrolls inside the text area, every row is reachable, and the window's box is
  unchanged

#### Scenario: No unread indicator is rendered
- **WHEN** the window renders in exploration, combat, or dialogue mode while lines arrive
- **THEN** no unread count, unread live region, or jump-to-latest control exists in the window

#### Scenario: The dialogue line is paged under the name plate
- **WHEN** mode `dialogue` commits with host `灰婆婆`, `bond_stage` `親睦`, and a greeting long enough for two pages at 1920x1080
- **THEN** the window spans the whole band, shows the name plate `灰婆婆 ‧ 羈絆 親睦`, types page 1 with no marker until it is fully shown, shows `▼`, advances on Enter on the page surface to page 2, and shows `■` once page 2 is fully shown, with no choice row inside the window at any point

#### Scenario: An unbonded host's plate names only the host
- **WHEN** mode `dialogue` commits with `bond_stage` `null`
- **THEN** the name plate reads the host's `display_name` alone and carries no `羈絆` text

#### Scenario: A transiently unavailable panel shows no plate
- **WHEN** mode is `dialogue` but the committed panel is the unavailable form
- **THEN** no name plate renders and the window shows the current response's pages with their page marker

### Requirement: An open drawer or overlay dims the stage behind it
When a drawer or a full-screen overlay is open, the shell SHALL mark the stage so the surfaces behind
the open surface are visually recessed, and SHALL clear that mark only when no drawer and no overlay
remain open. The recession SHALL be visual only: it SHALL NOT be used in place of hiding a
mode-gated surface, and it SHALL be disabled under `prefers-reduced-motion` for its transition while
the recessed state itself still applies.

#### Scenario: Opening a drawer recesses the stage
- **WHEN** a drawer or overlay opens
- **THEN** the stage behind it is visually recessed and the mark is present on the stage root

#### Scenario: The mark clears only when everything is closed
- **WHEN** two surfaces are open and one closes
- **THEN** the stage stays recessed until the last open surface closes

### Requirement: The HUD island stack renders as bounded floating islands, not column cards
This requirement carries the `place-card-relocation` and `vitals-bar-redesign` amendments; the party quickbar is removed with this change.
The surfaces placed in the stage's island anchors SHALL render as floating HUD
islands: a translucent panel fill, a backdrop blur, a hairline border, the shared corner radius, and
the shared drop shadow, each island a separate box separated by the anchor's gap — never a single
boxed column card and never an opaque `<aside>` stacked in a layout column. The `vitals` anchor, at the
stage box's lower left, is the vitals dock that "The vitals dock stands at the stage's lower-left above the band"
defines: it carries the condition icon row and the vitals bars as one dock, and SHALL carry
neither a character head card nor a portrait catalog strip nor a party quickbar. The `map` anchor SHALL carry, in this order, the
place card, the
minimap island, the objective line, the combat participant frame while it is mounted, and the title
ballot menu while it is mounted, each present only while its own requirement renders it; no reference
panel and no portrait anchor content SHALL be placed in either island anchor. The stack's rendered height SHALL fit within its anchor at both 1440x900 and 1280x720 with
every island populated, so no required island depends on scrolling the anchor to be seen. Every
island's chrome SHALL be expressed through the shared design tokens, so a token change or the
reduced-motion block reaches all of them at once.

#### Scenario: The left anchor renders separate islands
- **WHEN** the shell renders in exploration mode with a vital below its maximum, a committed `harmful` condition, and a non-empty party
- **THEN** the condition icon row and the vitals bars render as the lower-left dock's two surfaces in that order, the dock carries the translucent blurred panel chrome, no head card, place card, portrait catalog strip, or party quickbar is rendered, and the party appears only as standing portraits in the `actor-left` anchor

#### Scenario: The populated stack fits its anchor at the minimum viewport
- **WHEN** the shell renders at 1280x720 with every island populated and the condition overflow disclosed
- **THEN** each island anchor's stack fits inside its anchor, the place card's rendered box does not intersect the minimap island below it, and neither stack intersects the bottom band, the command line, or the other island anchor's content

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

### Requirement: The low-HP presentation state is derived client-side and drives the stage hook
The client SHALL derive a low-HP presentation state from the committed `status.resources.hp` ratio
alone, against a single display-only threshold, and SHALL expose it on the stage root through the
shell's existing low-HP hook so the stage renders its red vignette and the hp fill renders its pulse.

The threshold SHALL be a presentation constant: no server field, trait, or condition expresses "low
health", and the client SHALL NOT request one, invent one on the wire, or treat the derived state as
canonical. The state SHALL NOT be load-bearing — the numerals and the low text marker SHALL convey the
same information at every value, so a viewer who perceives neither the vignette nor the pulse loses
nothing. When the `status` panel is unavailable the state SHALL be false rather than true by default.
The pulse and the vignette transition SHALL be token-gated so the reduced-motion block disables the
motion while the marker and the numerals still apply.

#### Scenario: Crossing the threshold lights the stage
- **WHEN** a committed revision takes the hp ratio to or below the display threshold
- **THEN** the stage root carries the low-HP state, the stage renders its red vignette, and the hp fill renders its pulse

#### Scenario: Recovering clears the stage state
- **WHEN** a later committed revision takes the hp ratio back above the threshold
- **THEN** the low-HP state clears and the stage returns to its ordinary vignette

#### Scenario: An unavailable status panel is not low HP
- **WHEN** the `status` panel commits its unavailable form
- **THEN** the low-HP state is false, no red vignette is rendered, and no hp value is fabricated

#### Scenario: Reduced motion keeps the information and drops the motion
- **WHEN** `prefers-reduced-motion` is set and the hp ratio is below the threshold
- **THEN** the pulse animation is disabled while the low text marker, the numerals, and the recoloured row still render

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

### Requirement: The minimap island states only its own drawing convention
The minimap SHALL render as a bounded HUD island in the stage's `map` anchor, directly
below the place card and above the objective line, carrying the committed `local_map` payload's title. The island SHALL share the anchor's content-column width with the place card above it, so the two read as one column. Where the resolved layout variant is the
coordinate lattice — which exactly the coordinate-bearing layers (`grid`, `wilderness`) select — the
island SHALL state the renderer's own axis convention as orientation marks in its header following the
redesign draft's header treatment (the letterspaced title style and the `北↑ 東→` marks the draft's
lattice header draws); on the radial graph variant it SHALL omit those marks rather than assert an axis
the presentation does not draw (a radial graph draws no axis). Those marks and the axis cross the
lattice draws are ONE claim stated twice — once in words, once as geometry — so the two SHALL travel
together: a map surface SHALL draw the axis cross only where that same surface states the axis
convention in words, and the island's marks are what license the axis its lattice draws. The island
SHALL therefore draw the axis cross through the `current` node on the coordinate lattice and SHALL draw
none on the radial graph, and a surface that states no orientation marks — the full-map surface as it
stands — SHALL draw no axis at all. The lattice's coordinate dot field and its knowledge-edge vignette
are decoration that states nothing in words and SHALL NOT be read as a position, a bearing, a distance,
or a terrain claim: the dot field pictures the coordinate cell step the lattice already claims, and the
vignette pictures the limit of what the payload knows. On a coordinate-bearing layer the island SHALL additionally state the
`current` node's own coordinates as a two-integer figure — the payload `x` and `y` exactly as
committed, with no unit, delta, or derived quantity — as the entire content of its readout line, so
the island's position statement is the drawing convention plus the current cell's world coordinates
and nothing else. The readout SHALL NOT restate the current node's place name, its visibility state,
or a movement destination: the place name belongs to the stage's place card, which stands directly
above this island in the same column, and a
minimap shows the current position by definition. The readout SHALL NOT be driven by hover or by
selection, and the island SHALL keep no hovered-node or selected-node state; a node's own name stays
available as its on-canvas accessible name and, for a remembered node, as visible text on the surface
its layout variant presents it on — the name drawn beside the island's edge direction marker on the
coordinate lattice, and its entry in the full-map surface's remembered list on the radial graph, where
the island draws no visible remembered-node list at all — with the untruncated name always available
to assistive technology on the island, so no remembered place is readable by sight alone. Apart from that single figure the island SHALL NOT render a bearing angle, a compass
angle, a distance, or any other coordinate figure: coordinate readouts for non-current nodes,
differences between node coordinates, and every spatial figure on the graph variant remain forbidden,
because on coordinate-bearing layers node coordinates are validated world coordinates whose only
permitted visual uses are relative-direction geometry and the current-node figure, and on every other
layer they are renderer-local layout values that carry no spatial meaning at all. The one direction
statement the island MAY make in words is the octant name an edge direction marker already draws — one
of `北`, `東北`, `東`, `東南`, `南`, `西南`, `西`, `西北` — and only on the island's assistive-technology
text alternative for those markers, where it names the bearing the drawing already asserts to a reader
who cannot see it; a numeric angle, a degree figure, and a distance remain forbidden everywhere.

The island SHALL NOT present any map layout control — no segmented switch, button, menu item, or other
affordance selecting between the coordinate lattice and the radial graph — on the island or on the
full-map surface: the layout is resolved once from the committed payload's `layer` in the render model
and both surfaces consume that one value, so there is nothing for a control to change. No layout choice
SHALL be persisted in a client-local preference or any storage, and nothing about layout selection SHALL
travel to the server, because no selection exists to persist.

The island SHALL present no control for a surface the application does not mount: a full-map
affordance SHALL exist only once the full-map surface it opens is reachable. The island SHALL present
exactly ONE full-map affordance, and it SHALL carry no visible button chrome — no labelled control,
icon button, or other visible trigger occupies the island's header or any other part of the island,
because the island itself is the affordance. That affordance SHALL be a real `<button>` element
spanning the island's whole box, transparent and layered beneath the island's visual content so the
button element contains no focusable descendant, carrying 展開全地圖 as its accessible name and opening
the full-map surface through the platform's own Enter/Space button behaviour rather than a key handler
on a non-button element. Its focus-visible indication SHALL delineate the whole island rather than a
small region of it. Clicking anywhere on the island's non-interactive body SHALL still open the
full-map surface as a pointer convenience, provided the click did not originate in an interactive
descendant, and every activation path SHALL open the surface exactly once. The island root SHALL NOT
gain a button role or tab-stop of its own — the full-bleed button, not the root, is the keyboard path
— and `role="button"` on the island root is forbidden outright: a `role="button"` element must contain
no focusable descendant and must not flatten a composite surface into one accessible name, and the
island is a composite surface whose content the root would swallow. The full-bleed button SHALL remain
the island's only tab stop whatever its content becomes: a remembered place's presentation SHALL NOT
be a tab stop, on either layout variant, and SHALL be readable without being focusable. The minimap's
existing per-node movement submission SHALL be unchanged.

#### Scenario: The island states the axis convention on a coordinate-bearing layer
- **WHEN** the committed payload's layer places nodes on coordinates and the resolved variant is the lattice
- **THEN** the island renders the renderer's axis orientation marks in its draft-styled header
  alongside the map title, and its readout line states the current node's two payload coordinates as
  its entire content — no place name, no visibility-state word, no destination

#### Scenario: The stated convention and the drawn axis travel together
- **WHEN** a coordinate-bearing payload renders on the island, then a coordinate-free payload renders on
  the island, then the same coordinate-bearing payload renders on the full-map surface, which states no
  orientation marks
- **THEN** the island draws the axis cross exactly where it states `北↑ 東→` and nowhere else — drawn on
  the lattice, absent on the graph, and absent on the full-map surface — so no surface ever draws an axis
  it does not name or names an axis it does not draw
- **AND** the island's coordinate dot field and knowledge-edge vignette add no word, figure, or angle to
  the island: no bearing, no distance, and no coordinate figure beyond the current node's own pair appears
  anywhere because of them

#### Scenario: The readout ignores hover and selection
- **WHEN** the player hovers and then activates a non-current node on a coordinate-bearing layer
- **THEN** the readout line still states only the current node's coordinate figure, no coordinate
  figure appears for the hovered or activated node, and the island holds no hovered-node or
  selected-node state

#### Scenario: A coordinate-free layer omits the legend
- **WHEN** the committed payload's layer is coordinate-free
- **THEN** the island renders no orientation marks and no coordinate figure rather than asserting a
  direction or position the payload does not support

#### Scenario: The layout follows the payload without any control
- **WHEN** a coordinate-bearing payload and then a coordinate-free payload are committed, with no player
  interaction beyond movement
- **THEN** the island and the full-map surface render the lattice for the first payload and the radial
  graph for the second, the map chrome exposes no layout-control element in either state, and no
  preference or storage write occurs

#### Scenario: No compass angle or distance is rendered
- **WHEN** the minimap island renders on any layer
- **THEN** no compass angle, bearing angle, or distance appears anywhere in the island, and the only
  coordinate figure that can appear is the current node's own payload pair on a coordinate-bearing layer

#### Scenario: No control opens an unmounted surface
- **WHEN** the full-map surface is not mounted in the application
- **THEN** the island presents no full-map control, and the per-node movement submission continues to work unchanged

#### Scenario: Island body click opens the map without a second tab stop
- **WHEN** the player clicks the island's non-interactive body while the full-map surface is mounted
- **THEN** the full-map surface opens exactly once, the island root carries no button role and no
  additional tab stop, and the island's full-bleed transparent button remains the keyboard path with
  its focus restore unchanged

#### Scenario: The island's single affordance wears no visible chrome
- **WHEN** an available payload renders on the island while the full-map surface is mounted
- **THEN** exactly one full-map affordance exists, it is a `<button>` spanning the island's whole box
  with 展開全地圖 as its accessible name, no labelled or icon full-map control is rendered in the
  island's header or anywhere else in the island, and the island root carries no `role="button"`

#### Scenario: A keyboard user reaches the full map from the island
- **WHEN** a keyboard user tabs into the island and presses Enter, and repeats the run with Space
- **THEN** each press opens the full-map surface exactly once through the button element's own
  behaviour, the focus-visible indication while it is focused delineates the whole island, and closing
  the surface restores focus to that same still-present element

#### Scenario: Clicking an interactive descendant does not open the map
- **WHEN** the player activates an actionable lattice node, an edge direction marker, or the
  full-map affordance itself
- **THEN** only that control's own behavior runs — the node submits its move and no additional
  map-open is emitted, the affordance opens the map exactly once, and the marker, which carries no
  behaviour and no tab stop, lets the click fall through to the island body so the map opens exactly
  once from there

#### Scenario: A remembered place is readable on the island without a tab stop
- **WHEN** the island renders a coordinate-bearing payload carrying remembered gateways and, in turn,
  a coordinate-free payload carrying remembered rooms
- **THEN** the first draws each place's name beside its edge direction marker, the second draws no
  remembered place's name as visible text on the island and the full-map surface it opens lists each
  place's name as visible text, both islands expose every such place's untruncated name to assistive
  technology — with the marker's octant direction word on the lattice variant and no direction on the
  graph variant — and in neither case does the island offer a second tab stop beyond its full-map
  affordance

#### Scenario: The island sits under the place card at the column's width
- **WHEN** the shell renders in exploration mode with a committed `local_map` panel
- **THEN** the minimap island's top edge lies directly below the place card's bottom edge across the
  anchor's gap, and the two islands' left and right edges coincide

### Requirement: The combat dock root renders as a vertical command window with a truthful skills count
In combat mode the root SHALL render one vertical icon-and-label command list with a neutral inline Skills count equal to the committed descriptor count, omitted at zero. It SHALL preserve the existing resolver item order, identities, availability and confirmation routes. The active root SHALL be the only listbox/tab stop and expose its focused row by active descendant. Up/Down SHALL traverse and wrap in rendered order; Left/Right SHALL be no-ops at root. At deeper levels the root list SHALL be replaced by the current frame, with the existing breadcrumb/back path and only one active row container. No other mode SHALL render this combat root. Glyphs SHALL retain the existing concept mapping.

#### Scenario: The combat root renders as a vertical list and owns the listbox
- **WHEN** the dock is at the combat root frame
- **THEN** each root item renders as a vertical list row with a glyph and its label, the list carries the listbox role with a single tab stop and an active-descendant reference, and each row carries its preserved row identity attribute

#### Scenario: A combat root glyph matches the reference design's icon for the same concept
- **WHEN** the combat root renders the 攻擊/技能/道具/防禦/逃跑/投降 rows
- **THEN** each row's glyph is the same pictogram `docs/design/elosern-redesign/index.html` draws for that concept's tab

#### Scenario: The skills count equals the committed skill count
- **WHEN** the committed combat panel lists three skill descriptors across its categories, and later a panel with none
- **THEN** the 技能 row shows the neutral inline count `3`, then no count at all, and no other combat row shows a count or alert badge

#### Scenario: Combat root focus geometry matches the rendered order
- **WHEN** the player presses the arrow keys on the combat root frame
- **THEN** focus moves through the rows in their rendered order with the vertical arrow keys and wraps at the ends, and the horizontal arrow keys move focus nowhere

#### Scenario: An open deeper combat frame replaces the root list
- **WHEN** a deeper combat frame is open
- **THEN** the root list is replaced by the current frame, the deeper frame's row container is the surface's only listbox and only tab stop, and no root row is reachable by sequential keyboard navigation

#### Scenario: Exploration renders no combat root list
- **WHEN** the dock renders in exploration or dialogue mode at any depth
- **THEN** no combat root list is rendered, and no 移動, 查看, 互動, or 建議 root row exists anywhere in the dock

#### Scenario: Recovery root is bounded
- **WHEN** the resolver supplies only the recovery Forfeit path
- **THEN** one root row renders and still requires its existing explicit confirmation

### Requirement: The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance
The action dock SHALL carry one shortcut-legend strip at the bottom of its content column, below the
scrolling region, in exploration and combat mode (never in creation mode, and never visibly in
dialogue mode, where the strip is hidden with the collapsed command region), matching
`docs/design/elosern-redesign/index.html`'s dock hint in wording and structure: the text
`數字鍵 1–9 ‧ ` followed by an `<kbd>` element naming `Enter`
and the verb `執行`, the separator `‧`, and an `<kbd>` element naming `Esc` and the verb `返回`.
The legend renders
with the reference's `<kbd>` treatment (monospace face, `--ink-780` ground, 2px bottom border).
The legend SHALL render exactly once as visible content and SHALL be the only element carrying the
legend's test hook; no root command list or pane SHALL carry a second copy. The dock SHALL NOT carry a dialogue-mode
legend variant.

The legend SHALL NOT name a key, gesture, or affordance this client does not implement or that no
longer behaves as named, and it SHALL NOT advertise implemented affordances the reference's legend
does not name. When a named affordance's behaviour changes (for example, a control that used to
open a surface and now only moves focus into an always-present one), the legend's wording SHALL be
updated in the same change that alters the behaviour.

The digits the legend names SHALL be bound: while the dock owns keyboard focus (the key target is
not editable), pressing
`1`–`9` moves the current dock frame's focus onto its first nine entries (1-indexed, rendered order —
for the scene overview, its first nine chips in reading order: exits, then people, then objects, then
the footer; a frame's `back` row takes the slot of its rendered position) and activates the entry through the
same confirm path `Enter` uses — a disabled entry shows its explanation and submits nothing, an
in-flight entry stays locked, and a held repeat is suppressed.
The slots address the frame's rendered entries, disabled ones included. In dialogue mode neither the
dock's entries nor the keyboard router claim any digit: the digits `1`–`N` belong to the dialogue choice
list while it holds focus, which handles them itself as "Dialogue choices appear centred over the stage
after the line is fully read" defines.
A digit whose entry does not exist (a frame with fewer rendered entries, dialogue mode, or
the pre-session empty stack) is not claimed and falls
through to the text / command-history path.

#### Scenario: The legend renders once
- **WHEN** the dock renders in exploration or combat mode, at the overview, in a child frame, or at the combat root, and later the mode changes to dialogue
- **THEN** exactly one element carries the shortcut-legend text and test hook, it is the dock's
  legend strip, no root command list or pane renders a duplicate copy, and in dialogue mode the strip is hidden
  with the command region and no other element shows a legend

#### Scenario: The legend matches the reference wording and kbd structure
- **WHEN** the dock renders its legend strip in exploration or combat mode
- **THEN** the legend reads `數字鍵 1–9 ‧ Enter 執行 ‧ Esc 返回` with `Enter` and `Esc` rendered as
  styled `<kbd>` elements and no other key named

#### Scenario: A digit picks its row
- **WHEN** the scene overview holds three exit chips, two person chips, and one object chip, and the
  player presses `5`, and later `6`, from a non-editable focus
- **THEN** the `5` press focuses the second person chip and opens its popover exactly as `Enter`
  would, once, and after Escape the `6` press focuses the object chip and submits its `explore.look`
  once

#### Scenario: A digit beyond the frame's rows is unclaimed
- **WHEN** the current dock frame has fewer rendered entries than the pressed digit and the command
  field is not focused
- **THEN** the digit is not claimed, the frame's focus is unchanged, and nothing submits

#### Scenario: Digits address the caption's picks while the dialogue variant presents
- **WHEN** the dialogue choice list shows four picks with focus on the list, the command region is
  collapsed, and the player presses `4` and `5`
- **THEN** the `4` press activates pick four through the same dispatch entry, the `5` press is handled
  by neither the list nor the keyboard router and falls through, and the hidden dock's focus and frame
  are unchanged

### Requirement: A breadcrumb derived from the router names the player's position at depth

The dock SHALL render a breadcrumb line whenever the router's menu stack is deeper than its root
frame, and SHALL hide it entirely at the root frame. The one exception is a target's verb popover
(the scene overview's person-target frame): the popover's own heading already names the target, so
while that frame is current the breadcrumb SHALL NOT render and the target SHALL be stated exactly
once; the popover's `back` row, Escape, and a pointer press outside the popover card remain its back
paths. Every other submenu keeps the breadcrumb. The breadcrumb SHALL name the parent frame and
the current frame, with the current frame visually distinguished, and SHALL carry a back control.
Activating the back control SHALL perform exactly the same operation the Escape key performs — it
SHALL pop exactly one menu level and SHALL NOT dispatch any action.

The breadcrumb's contents and its visibility SHALL be derived from the keyboard router's own frame
stack and depth, published through the committed view in the same pass as the frame's rows. The
client SHALL NOT maintain a second navigation state — no local pane selection, no locally accumulated
crumb stack — so the breadcrumb can never disagree with what Escape will do. A frame's breadcrumb
label SHALL come from the frame itself; for a frame scoped to one target, that label SHALL be the
target's server-authored display name. Every frame's `back` item SHALL render as a row of that frame, so
a focused `back` item carries the same focused treatment as any other row (a background fill and
border change together); the breadcrumb's back control SHALL carry no focus state of its own that
mirrors the router's focus. Activating the back row with Enter or the pointer, or activating the
breadcrumb's back control, SHALL pop exactly one level, restore the parent frame's previously
focused entry, and dispatch no action.

#### Scenario: The breadcrumb appears only below the root
- **WHEN** the dock is at its root frame
- **THEN** no breadcrumb is rendered
- **WHEN** the player opens a submenu
- **THEN** the breadcrumb appears naming the parent frame and the current frame

#### Scenario: The back control is the Escape path
- **WHEN** the player activates the breadcrumb's back control at any depth
- **THEN** exactly one menu level closes, the parent frame's rows render with the previously focused row marked, and no `ui_action` is emitted

#### Scenario: A focused `back` row keeps a visible focus carrier
- **WHEN** keyboard focus moves onto the suggestions frame's `back` item
- **THEN** that `back` item is rendered as a row carrying the focused state (fill and border change together, not color alone), the breadcrumb's back control carries no focused state, and Enter on the row or a click on the breadcrumb control pops exactly one level back to the parent frame
- **WHEN** keyboard focus moves onto a verb popover's `back` item
- **THEN** that `back` item carries the same focused row treatment, and Enter or a click on the row pops exactly one level back to the scene overview

#### Scenario: The breadcrumb tracks a target frame's own name
- **WHEN** the player opens a frame scoped to one target other than the verb popover
- **THEN** the breadcrumb's current segment is that target's server-authored display name
- **WHEN** the player opens an interact target's verb popover from the scene overview
- **THEN** the popover's heading is that target's server-authored display name, no breadcrumb is rendered, and the target's name appears once in the command region

#### Scenario: The breadcrumb cannot drift from the router
- **WHEN** a panel replacement pops or replaces the current frame
- **THEN** the breadcrumb's depth and labels match the router's frame stack in the same render, with no interval in which they describe a frame the router has already left

### Requirement: Dock panes render a per-kind vocabulary from backed fields only

The dock's row region SHALL render the current frame in a form chosen for what that frame contains,
using one shared row renderer for every form so the focused marker, the disabled marker and its
`（無法使用）` suffix, the accessible disabled association, and the row identity attribute are defined
in exactly one place. The forms SHALL be: exit, person, object, and footer chips for the scene
overview; the verb popover's rows under a target head; the waiting cards; suggestion cards for the
suggestions frame; and the combat forms specified elsewhere in this capability. No exploration frame
SHALL render an exit-outlet grid or a navigation-row list: exits are chips of the scene overview, and
a host's conversation topics are the dialogue surface's choices, never a dock frame.

An exit chip SHALL render the exit's direction as a leading glyph, and, while the chip is enabled, its
primary text SHALL be the destination's display name — never a repetition of the direction word or the
exit's own label once a glyph already carries that meaning. The glyph SHALL be resolved from a fixed
client-side table of canonical direction words; an exit label outside that table SHALL render verbatim
as the chip's primary text (there being no glyph to carry it) rather than being mapped to a guessed
direction. The destination's display name SHALL be resolved by matching the exit's server-authored
destination node against the committed local-map nodes; when that node is not present in the committed
lattice, an enabled canonical-direction chip SHALL fall back to its own exit label as its primary text
rather than rendering blank — but SHALL NOT render both the destination name and the exit's own label
at once. A disabled exit chip SHALL always render its own exit label as its primary text, never the
destination name, followed by the shared disabled marker. An exit chip's focused state SHALL be
conveyed by its background and border fill together and SHALL NOT additionally render a focus-only
glyph beside its persistent direction glyph. A disabled exit chip's server-authored explanation SHALL
remain reachable by assistive technology directly from the chip and SHALL be shown in the overview's
reason strip while the chip is focused. The submitted move payload SHALL be unchanged.

A chip or row SHALL render only fields the committed payload carries: its server-authored name and,
where its form has one, an optional sub-line composed of such fields. No chip or row SHALL
render a statistics line, a portrait, or any other element for which the payload has no field; where
the design draft shows such an element it SHALL be absent rather than emptied or mocked. Icons and
glyphs SHALL be decorative, SHALL be hidden from assistive technology, SHALL always accompany a real
text label, and SHALL be selected only from stable server-authored keys or the direction table — never
from free text such as a display name.

A target's verb popover SHALL render a head naming the target it is scoped to, taken from the frame's
own server-authored display name, above that target's rows.

Every row and chip in every form SHALL keep the existing disabled contract: a disabled entry SHALL
remain focusable by arrow keys and by pointer, SHALL keep its accessible disabled state and its
server-authored explanation, and SHALL submit nothing.

#### Scenario: A move row names where it goes
- **WHEN** the scene overview renders an enabled exit chip whose label is a canonical direction and whose destination node is present in the committed local map
- **THEN** the chip renders that direction's glyph together with the destination node's display name as its primary text, with no separate rendering of the exit's own direction-word label, and activating it submits the unchanged move payload

#### Scenario: A non-canonical exit keeps its own name
- **WHEN** an exit chip's label is a named door or a dynamic wilderness exit rather than a canonical direction
- **THEN** the chip renders that label verbatim as its primary text and no direction is guessed for it

#### Scenario: An unknown destination falls back to the exit's own label
- **WHEN** an enabled canonical-direction exit chip's destination node is absent from the committed local map
- **THEN** the chip renders its glyph together with the exit's own label as a fallback primary text, and no destination name is invented

#### Scenario: A disabled exit never loses its disabled marker to a known destination
- **WHEN** a canonical-direction exit chip is disabled and its destination node is present in the committed local map
- **THEN** the chip renders its own exit label followed by the shared disabled marker as its primary text, not the destination's display name, and its server-authored explanation remains reachable by assistive technology from the chip itself

#### Scenario: A focused move row is not double-marked
- **WHEN** an exit chip carrying a direction glyph is focused
- **THEN** the chip's background and border change together to mark focus, and no additional focus-only glyph renders alongside its existing direction glyph

#### Scenario: The move frame has no companion panel
- **WHEN** the scene overview renders with any chip focused
- **THEN** no detail aside or other side panel renders beside the overview, the overview occupies the pane's full available width, and no exit-outlet grid exists anywhere in the dock

#### Scenario: A row renders only backed fields
- **WHEN** the scene overview renders a look-only chip for a present entity
- **THEN** the chip shows the entity's display name only, and shows no statistics line and no portrait, because the exploration payload carries no such field

#### Scenario: A target-affordance frame names its target
- **WHEN** the player opens an interact target's verb popover
- **THEN** the popover renders a head naming that target above the target's server-authored rows

#### Scenario: A disabled row in any pane stays readable
- **WHEN** a disabled row or chip is focused in any form, by arrow key or by pointer
- **THEN** it keeps focus, exposes its accessible disabled state and its server-authored explanation, and no action is submitted

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
entry that resolves to a placeholder SHALL render a compact initial with its truthful availability state accessible outside the bitmap; an entry whose image URL fails to load SHALL render a compact initial with a localized load-failure state accessible outside the bitmap; and a null reference or an
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

#### Scenario: A catalog portrait fails to load
- **WHEN** a catalog entry has an image URL that fails to load
- **THEN** the frame replaces the bitmap with the participant's initial and an accessible `肖像載入失敗` state, without changing its token or numeric HP

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
lies at least 24px left of the participant frame's column, within the `map` anchor in combat.
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

### Requirement: Combat identity and status remain legible without changing authority
The combat presentation SHALL show each standing foe name with its decorative gauge, preserve every participant identity and numeric HP with a decorative HP hairline in the participant frame, and distinguish the acting or focused-target foe by a non-colour cue without making it interactive. The compact frame SHALL NOT obscure a standing foe head. A zero canonical round SHALL be described as preparation rather than incremented.

#### Scenario: Playback HP agrees
- **WHEN** a beat changes display HP for a participant whose portrait reference names a displayed value
- **THEN** its participant numerator and hairline, and its foe gauge when it stands on stage, use that value and settle to committed HP together; a null or unmapped reference keeps committed HP on both participant and stage surfaces

#### Scenario: First round is not fabricated
- **WHEN** session round is zero and then one
- **THEN** the ribbon shows preparation and then canonical round one, never adding one

#### Scenario: Portrait is missing
- **WHEN** a participant catalog entry is a placeholder
- **THEN** the thumbnail has one initial with accessible state, not clipped multiline microcopy; its visible session token remains

### Requirement: Combat skills are chosen through a bounded master-detail
In combat, opening Skills SHALL present the committed skill categories as a bounded frame of category
entries, each carrying its server-authored label and the count of its own skill descriptors. Opening a
category SHALL present that category's sub-groups as a frame when the category carries more than one
sub-group, and SHALL open the skill frame directly when it carries exactly one — so no menu level ever
offers a single choice. The skill frame SHALL list that group's descriptors in the server's order,
each row carrying the skill's label and its resource cost, beside a detail region naming the focused
skill, its description, its cost, its target requirement and, when it is unavailable, its
server-authored reason.

Category, group and skill ordering SHALL be exactly the committed panel's order at every level. The
frames SHALL NOT reorder, filter or merge the server's grouping, and SHALL NOT render any badge or
field the skill descriptor does not carry. The subsequent power-scale step and target step SHALL be
unchanged in behaviour and payload: the scale frame SHALL render each advertised scale with its
server-computed cost in ascending order, and the target frame SHALL render the valid participants as
selectable tokens distinguishing the player's side from the opposing side, preserving the existing
multi-select marker. Every submitted cast payload SHALL be byte-identical to the payload the same
choices produce today.

The focused row SHALL be scrolled into view within the bounded row region on every frame render and
every focus change, so arrow navigation never leaves the focused row off-screen.

#### Scenario: Skills opens categories, not one flat list
- **WHEN** the player opens Skills in combat
- **THEN** the dock renders one row per committed skill category, each with its label and its own descriptor count, in the panel's order

#### Scenario: A single-group category skips a pointless level
- **WHEN** the player opens a category whose committed payload carries exactly one sub-group
- **THEN** the skill frame opens directly, and Escape from it returns to the category frame

#### Scenario: A multi-group category presents its groups
- **WHEN** the player opens a category whose committed payload carries more than one sub-group
- **THEN** the dock renders one row per sub-group in the panel's order, and opening one lists that group's skills

#### Scenario: The detail region names the focused skill
- **WHEN** a skill row is focused, including a disabled one
- **THEN** the detail region names that skill, its description, its cost and its target requirement, and for a disabled skill its server-authored reason, while the row stays focusable and submits nothing

#### Scenario: The cast payload is unchanged
- **WHEN** the player reaches a target through the category and group frames and confirms
- **THEN** the emitted cast payload is byte-identical to the payload the same skill, scale and target produce before this change

#### Scenario: The focused row is never off-screen
- **WHEN** the player arrows through a skill list longer than the bounded row region
- **THEN** the row region scrolls so the focused row is visible after every focus change

### Requirement: Destructive combat confirmation renders as an explicit two-step panel
The Forfeit entry SHALL open a confirmation frame rather than submitting, and that frame SHALL render
as an explicit warning panel stating what forfeiting does, with a cancel row and a confirm row. Only
the confirm row SHALL submit, and it SHALL carry the current session identifier exactly as it does
today. Escape or the breadcrumb's back control SHALL leave the confirmation without submitting and
without ending the session.

#### Scenario: Opening Forfeit submits nothing
- **WHEN** the player opens the Forfeit entry
- **THEN** a warning panel renders with a cancel row and a confirm row, and no mutation is sent

#### Scenario: Leaving the confirmation is safe
- **WHEN** the player presses Escape or activates the breadcrumb's back control on the confirmation frame
- **THEN** exactly one level closes, no mutation is sent, and the combat session is unchanged

#### Scenario: Confirming carries the session identifier
- **WHEN** the player activates the confirm row
- **THEN** exactly one forfeit action is emitted carrying the current session identifier

### Requirement: Reference surfaces render in a bounded workspace drawer with one modal contract
The client's reference surfaces SHALL render in a wide workspace 12px below the top navigation's
bottom edge, 16px inside each side of the viewport, and one command-line row height plus 12px above the
viewport bottom, so the workspace covers the stage, the bottom band, and the command-line row whether or
not that row is expanded, and only the band's lowest control strip stays exposed beneath it. A fine
border and a fully opaque charcoal ink panel SHALL distinguish the workspace from the stage. The existing
modal drawer lifecycle and shared motion tokens SHALL be retained over a dimmed scrim covering the whole
viewport behind the drawer. Between its header and optional footer, a decorative art column MAY
accompany the scrolling content body; only the content body scrolls. The head SHALL be the shared
reference-surface header: the title in the serif heading face at the shared workspace scale with slight
tracking, and the subtitle as the small muted line beside it. Every reference drawer SHALL declare one
leading head icon (a decorative, `aria-hidden` glyph from the shared glyph registry rendered before its
title). The drawer's close control SHALL carry an accessible name (e.g. an `aria-label`) but MAY be
rendered icon-only, with no visible text node — "labelled" in this requirement means an accessible name,
not necessarily visible text.

At most one drawer SHALL be open at any time; opening a second SHALL close the first. While a drawer
is open it SHALL trap keyboard focus, so no surface behind it is reachable by sequential navigation.
It SHALL close on Escape, on activation of its labelled close control, and on activation of the scrim,
and every one of those paths SHALL restore focus to the control that opened it. An open drawer SHALL
register itself as an open surface so the stage recession this capability already requires applies
without a second mechanism.

The skill-book drawer specifically SHALL carry, whenever the `character` panel is available, a
subtitle stating its owner's active and passive skill counts (`主動 {n} ‧ 被動 {m}`, computed from that
same payload `SkillBook` renders) in the drawer head; when the panel is unavailable the subtitle is
empty, matching the drawer's existing degrade-without-inventing-data contract. The skill-book drawer
SHALL carry a footer stating the client's own cast-command syntax
(`施放入口：cast <技法>[@威力]=<代號>`) as static client-local presentation copy — not a value the OOB
protocol carries, so its presence does not depend on any panel's availability — whenever the drawer
presents the skill book itself; while the declared-practice sub-screen replaces the book body, that
footer is absent and the head title reads 修煉, because the cast syntax belongs to the book view the
sub-screen replaced.

#### Scenario: A drawer opens over the stage with a scrim
- **WHEN** the player opens a reference drawer
- **THEN** the workspace is bounded below the navigation and above the band's lowest control strip, covering the command-line row, as an opaque panel over a dimmed scrim, its content body is the only scrolling region, and the stage behind it carries the recession mark

#### Scenario: The head carries the reference display type scale
- **WHEN** a reference drawer renders its head
- **THEN** the title renders in the serif heading face with slight tracking and the subtitle renders as the small muted line beside it

#### Scenario: Only one drawer is open at a time
- **WHEN** a drawer is open and the player opens a different one
- **THEN** the first drawer closes as the second opens, and exactly one drawer and one scrim are present

#### Scenario: Focus is trapped and returned
- **WHEN** a drawer is open and the player cycles focus forward past its last control and backward past its first
- **THEN** focus stays inside the drawer in both directions, and on closing by Escape, by the close control, or by the scrim, focus returns to the control that opened it

#### Scenario: Closing the last drawer clears the recession
- **WHEN** the open drawer closes and no overlay remains open
- **THEN** the scrim is removed and the stage's recession mark is cleared

#### Scenario: Reduced motion keeps the state and drops the transition
- **WHEN** `prefers-reduced-motion` is set and a drawer opens
- **THEN** the drawer is open and correctly placed with no slide transition played

#### Scenario: The close control is icon-only but keeps its accessible name
- **WHEN** a reference drawer's close control renders
- **THEN** it carries no visible text node, renders a decorative close glyph, and exposes the same accessible name (e.g. `aria-label="關閉"`) an assistive technology would have read from the previous visible text

#### Scenario: The skill-book drawer states its skill counts and cast syntax
- **WHEN** the skill-book drawer opens with the `character` panel available
- **THEN** its head carries a leading skill glyph and a `主動 {n} ‧ 被動 {m}` subtitle matching the panel's active/passive row counts, its title renders exactly once (not duplicated inside the body), and its footer states the client's `/cast` syntax as static copy

### Requirement: Reference drawers present no router frame and never host a dock row region
No reference drawer SHALL present a keyboard router frame. Opening any reference drawer — including the 背包 ‧ 裝備 drawer from the top navigation's 背包 entry, the 商店 drawer from a merchant's `navigate` affordance row, and the 任務 drawer from the top navigation's 任務 entry or from a guild clerk's `navigate` affordance row — SHALL push no frame, switch no sub-dock, and record no drawer-hosted service surface; an opener that is itself a top-navigation entry MAY first return the dock to its root frame exactly as every top-navigation entry does, and the drawer open SHALL add nothing to the stack after that. The client SHALL NOT maintain a second frame stack, a second focus model, or a second set of menu keys for a drawer. No reference drawer body SHALL render the dock's row renderer (`dock-menu`) or detail pane (`dock-detail`) in any state. Closing a reference drawer — by Escape, its close control, or the scrim — SHALL leave the router alone, popping no menu level, and SHALL restore focus to the control that opened it. Committed rows inside a reference drawer SHALL remain reachable by keyboard without a hosted router frame.

A drawer SHALL be openable only while its backing payload is present. When the committed mode changes so that a drawer's payload is no longer available, when the presentation epoch resets, or when the transport is lost, every open drawer SHALL close and every local selection, quantity and confirmation state inside it SHALL be discarded.

#### Scenario: Opening the quest drawer from the guild clerk pushes no frame
- **WHEN** the player activates the guild clerk's `navigate` affordance row inside an open target frame
- **THEN** the 任務 drawer opens with the quest book and the guild counter, the router's current frame is still that target frame, no frame was pushed, no sub-dock switch occurred, and the breadcrumb is unchanged

#### Scenario: Opening the bag or the shop pushes no frame
- **WHEN** the player activates the top navigation's 背包 entry at the exploration root, or a merchant's shop `navigate` affordance row inside an open target frame
- **THEN** the matching drawer opens, the router's current frame is the frame that was current before the open, no frame was pushed, no sub-dock switch occurred, and the breadcrumb is unchanged

#### Scenario: Keyboard reachability does not depend on a hosted list
- **WHEN** a keyboard-only player moves through the open bag drawer, or moves into a shop stock row, types a quantity within its advertised bounds, and activates its buy control
- **THEN** every committed inventory row is reachable through the focusable item tiles with the shared inspector, the shop row becomes the selected row carrying the quantity hooks and exactly one `shop.buy` is emitted with that row's `item_key` and quantity, and no parallel navigation list of those rows exists to traverse

#### Scenario: Opening the quest drawer from the top navigation pushes no frame
- **WHEN** the player activates the top navigation's 任務 entry at any dock depth
- **THEN** the dock returns to its root frame as for every top-navigation entry, the 任務 drawer opens, and the router's depth is 1 with no frame pushed by the open

#### Scenario: No drawer renders the dock's row renderer
- **WHEN** any reference drawer is open, including the quest drawer while a guild counter control or a quest-book row holds focus
- **THEN** no `dock-menu` row region and no `dock-detail` pane exists inside the drawer, and the dock itself renders exactly the router's current frame

#### Scenario: Closing a drawer pops nothing and returns focus
- **WHEN** the open 任務 drawer closes by Escape, by its close control, or by the scrim
- **THEN** the router's frame stack is exactly what it was right after the open, no action is dispatched, and focus returns to the control that opened it

#### Scenario: A mode change closes the drawers it invalidates
- **WHEN** the committed mode changes from exploration to combat while a services-backed drawer is open
- **THEN** that drawer closes, its local selection, quantity and confirmation state is discarded, and no stale service surface remains reachable

### Requirement: The bag renders the bounded inventory rows without inventing a total or a rarity
The bag workspace SHALL use shared chrome for the `背包 ‧ 裝備` title, local inventory SVG icon, close control, and wallet subtitle formatted as integer copper from the committed available character panel. The wallet SHALL additionally render exactly once in the body as the single row of a `金錢` section. The available body SHALL present an `裝備` section carrying the read-only equipment doll, an `物品` section whose heading carries the shipped listing size above the bounded responsive grid, a `金錢` section carrying the same committed wallet, and a reserved non-interactive detail column driven by the existing hover/focus selection. The listing SHALL remain bounded by the server row ceiling and state that ceiling in words when reached; no shipped count SHALL claim to be the player's untruncated holdings.

Each registered row's non-null `presentation` SHALL select one local inline SVG by `icon_key`, an item-kind label, rarity label, bounded summary, and non-colour-only rarity treatment. Its tile SHALL show committed held count and a non-colour equipped marker. A null presentation SHALL render only the neutral unknown-item SVG and visible unknown marker; the browser SHALL NOT derive type, icon, rarity, summary, or mechanics from item key or display name. The grid SHALL use native keyboard-focusable buttons and one non-focusable inspector shared by pointer hover and keyboard focus; both inspection paths SHALL expose identical committed name, kind, rarity, count, equipped state, and summary, and the focused tile SHALL reference the stable inspector through `aria-describedby`.

Each tile SHALL follow only its committed nullable action descriptor. Inspect-only and unknown tiles SHALL dispatch nothing. Disabled tiles SHALL remain keyboard reachable, expose `aria-disabled`, and show the committed reason on activation without dispatch. Enabled usable items SHALL open a labelled, focus-trapped inventory-use confirmation; enabled equipment SHALL dispatch its toggle immediately. Selection and dialog state SHALL remain client-local and reset on panel replacement, drawer close, mode/epoch change, or transport loss. The bag SHALL NOT render or infer numeric item statistics, recovery amounts, conditions, effects, consumable flags, slots, set bonuses, comparisons, sorting, filtering, search, drag, or drop behavior, and SHALL render no static sort/filter/search pill.

The drawer SHALL remain available from its combat affordance when services v3 inventory is available. When services commits its unavailable form or inventory is absent, the bag SHALL render only the registered reason and fabricate no wallet, equipment, row, count, action, or dialog. When services inventory is available but character is unavailable, the grid SHALL remain available, the doll SHALL render its registered unavailable state, and no wallet subtitle, wallet body value, or zero balance SHALL be invented. All inspector, confirmation, and warning transitions SHALL use existing motion tokens so reduced motion makes them effectively instant.

#### Scenario: A registered actionable row preserves truthful inspection
- **WHEN** a committed registered inventory row carries presentation and an enabled action descriptor
- **THEN** its tile renders committed visual identity and inspector data, and deliberate activation follows the descriptor without deriving mechanics locally

#### Scenario: An unknown row has a neutral truthful fallback
- **WHEN** a committed inventory row has `presentation` null and `action` null
- **THEN** its tile shows the neutral unknown state and real quantity with no inferred metadata or mutation

#### Scenario: Keyboard inspection and activation match pointer behavior
- **WHEN** keyboard and pointer users inspect and activate the same tile
- **THEN** both receive identical committed inspector data and action behavior, and the focused tile references the inspector through `aria-describedby`

#### Scenario: Eligible item use opens confirmation
- **WHEN** the player activates an enabled usable-item tile
- **THEN** the labelled confirmation dialog opens without dispatch and confirm is the only path that submits use

#### Scenario: Equipment activates directly
- **WHEN** the player activates an enabled equipment tile
- **THEN** one equipment-toggle intent is emitted without opening a confirmation

#### Scenario: Disabled item presents its reason
- **WHEN** the player activates a full-HP potion or an unequipped accessory at the five-slot cap
- **THEN** the committed reason is presented and no request is dispatched

#### Scenario: Combat bag keeps personal items reachable
- **WHEN** mode changes to active combat and services v3 commits canonical inventory
- **THEN** the combat root's client-local `背包` row opens the frameless bag without dispatch or a router frame, and personal item tiles remain reachable while guild and shop surfaces are absent

#### Scenario: The bag body retains its authoritative sections in a wide workspace
- **WHEN** the bag is available with inventory, character equipment, and wallet
- **THEN** it renders equipment, items, and money from their existing sources, with a reserved
  non-interactive item-detail column, and invents no inventory total or additional holdings

#### Scenario: Wallet renders only in the bag head and money row
- **WHEN** the bag renders with available character and inventory panels
- **THEN** the same integer copper wallet appears in the head subtitle and the single `金錢` row and nowhere else in the drawer

#### Scenario: Ceiling is stated without inventing a total
- **WHEN** the shipped inventory reaches its maximum row count
- **THEN** the bag states the listing ceiling and never labels that count as complete holdings

#### Scenario: Unavailable services fabricates nothing
- **WHEN** the services panel commits its unavailable form
- **THEN** the bag renders only the registered reason with no rows, wallet, equipment, count, heading, action, or dialog

#### Scenario: Character unavailability preserves inventory without fabricating equipment
- **WHEN** services inventory is available but the character panel is unavailable
- **THEN** the bag renders held tiles, the equipment registered unavailable reason, and no wallet subtitle, wallet value, or zero balance

#### Scenario: Reduced motion preserves action information
- **WHEN** reduced motion is active and focus, inspector, confirmation, or warning state changes
- **THEN** transitions are effectively instant while labels, reasons, focus, and committed item information remain available

### Requirement: The equipment doll renders only server-authored slots and drops nothing
The equipment presentation SHALL be built from the committed `character` panel's equipment rows, each of which carries a slot, an item key and a display name and nothing more. The section SHALL be introduced by the bag's small tracked section heading `裝備` carrying the right-aligned tag `真值 ‧ 偽裝不影響`, and SHALL NOT be introduced by a standalone `裝備人偶` title. The doll SHALL lay out as the redesign's equipment row: a compact two-column square slot grid beside a 裝備描述 column that lists the committed rows grouped under their slot labels. The doll SHALL render the server's three singleton slots and one accessory summary as four named positions in the square grid. The main-hand, armor, and accessory-summary positions SHALL each render a fixed local SVG selected by its server-authored slot role; the off-hand position SHALL be the iconless position. The doll SHALL NOT select an item icon from an item key or display name. A singleton slot with no row SHALL render a visible named empty state with a dashed outline. An occupied singleton slot SHALL render its visible slot label in the grid and its committed display name in the 裝備描述 column; when the committed rows carry more than one row for a recognised singleton slot, the square position consumes only the first row and every further row for that slot SHALL render as a labelled overflow row, so no committed row is lost. The accessory summary SHALL render its visible label and committed item count, while every repeatable accessory row SHALL render in the 裝備描述 column's accessory group. Any slot key outside the recognised set SHALL render as a labelled fallback row rather than being discarded, so no row the payload sends is lost. When the committed rows carry no equipment at all the doll SHALL render only its visible empty statement.

The doll SHALL NOT render an item statistic, attack or defence value, rarity, item icon, summary, or comparison against another item: the equipment rows carry none of those. Equipment SHALL be presented as true values that a disguise does not affect, and the section tag SHALL state exactly that.

#### Scenario: The equipment section is titled 裝備 with the true-value tag
- **WHEN** the bag renders its equipment section
- **THEN** the section heading reads `裝備` with the tag `真值 ‧ 偽裝不影響` in the bag's shared section-heading style, and the string `裝備人偶` appears nowhere in the drawer

#### Scenario: An empty slot is shown as empty
- **WHEN** the committed equipment rows carry no row for a singleton slot
- **THEN** that slot renders its visible name with a dashed explicit empty state, and no item is invented for it

#### Scenario: An occupied singleton slot is identified without guessing its item type
- **WHEN** the committed equipment rows carry one primary-hand item
- **THEN** the square grid renders only that position's fixed slot SVG and visible slot name, the 裝備描述 column renders its committed display name under the `主手` label, and nothing is inferred about the item's icon, rarity, statistic, or comparison

#### Scenario: An occupied off-hand position renders without an item icon
- **WHEN** the committed equipment rows carry a `weapon_off` item
- **THEN** the off-hand position stays the iconless position of the binding design, rendering its visible slot label in the grid and its committed display name in the 裝備描述 column with no item icon

#### Scenario: The description column lists only committed rows
- **WHEN** the committed equipment rows carry equipment
- **THEN** the 裝備描述 column shows one labelled entry per primary row (slot label plus committed display name) — the first committed row of each recognised singleton slot and, in the accessory group, every accessory row — grouped by slot label, while duplicate and unrecognised-slot rows are rendered only by the doll's labelled fallback sections so each committed row appears exactly once, and with no committed row the column shows only the visible empty statement

#### Scenario: Duplicate singleton rows are rendered, not discarded
- **WHEN** the committed equipment rows carry more than one row for a recognised singleton slot
- **THEN** the square position shows the first row for that slot and every additional row renders as a labelled overflow row, so the duplicate committed row is never dropped

#### Scenario: Repeated accessories all render
- **WHEN** the committed equipment rows carry more than one accessory row
- **THEN** the accessory summary states the committed count and every accessory row renders in the description column's accessory group, and none is dropped for want of a fixed position

#### Scenario: An unrecognised slot is rendered, not discarded
- **WHEN** an equipment row carries a slot key outside the recognised set
- **THEN** the row renders with its slot key as its label and its display name, and the doll drops no row

#### Scenario: No statistics are invented for an equipped item
- **WHEN** an equipped item renders in the doll
- **THEN** it shows its display name and its slot only, with no attack, defence, rarity, item icon, summary, or comparison value

### Requirement: The character-status drawer degrades section by section and never substitutes a disguise
The character-status drawer SHALL present the committed `status` panel's resources and its complete condition roster in every mode, because that panel is available in every mode; each condition SHALL pair a non-colour severity glyph with its label and every numeric or derived-modifier value the payload provides. It SHALL present the committed `character` panel's true traits, guild standing, and persona background, and SHALL mark each of those sections with the registry-owned reason when the `character` panel is unavailable — as it is outside exploration mode — rather than hiding the drawer or inventing a value. Equipment and wallet presentation belong exclusively to the inventory drawer and SHALL NOT render in character status.

Where a disguise is active the drawer SHALL render the displayed values beside the true trait rows they describe, distinctly labelled, together with the statement that a disguise affects display, registration and identification only and that combat always resolves against true values. A displayed value SHALL NEVER replace a true trait row.

The character-status drawer SHALL preserve the 親密狀態 disclosure section added by the archived intimate-status change: when the committed `character` panel's `intimate` field is present the drawer renders its collapsed-by-default disclosure widget immediately after the 偽裝 (disguise) section and before the 背景 (persona) section, and no change SHALL remove it, reorder it, or alter its disclosure widget, content, or collapsed default; like the persona area it spans the full row of the section grid. When `intimate` is `null` or the `character` panel is unavailable, the section is absent from the DOM, exactly as the merged main spec requires. This change removes only the equipment and wallet sections.

Each of the drawer's sections (vitals, traits, conditions, guild counters, disguise, intimate status, persona) SHALL carry a labelled, small-caps section heading naming what it presents, using the same heading treatment the HUD's other islands use. The vitals, traits, and guild-counter sections SHALL render each value as its own bordered card tile in an auto-fill grid of equal-width tracks rather than a plain text row, each tile only as tall as its own content, with the tile's label at the left and its `current`/`current / maximum` value in the shared numeral treatment at the right; a tile carrying more than two breakdown chips SHALL span its grid's full row so its chips wrap in one wide line; no value not already present in the committed payload (such as an effective-vs-base delta) SHALL be invented to fill the tile. The sections themselves SHALL be content-sized cards in an auto-fit grid of equal-width tracks in their DOM order, with the persona area, the intimate disclosure, and a panel-wide unavailable reason spanning the full row, so no section's height depends on another's.

The drawer body SHALL open with a hero naming the committed character: the `status` panel's actor name, its composed full title (`status` actor `full_title`), and the `character` panel's guild rank, each rendered only when the payload supplies a non-blank value and omitted — never guessed — otherwise; the name and title therefore stay in every mode, and the rank is absent while the `character` panel is unavailable. The hero SHALL carry the drawer's existing secondary openers (技能書, and 同伴 ‧ 隊伍 while the party panel is available) in one wrapping action row, with their existing behavior. The body SHALL NOT repeat the drawer title the shared header already renders. The condition roster SHALL render as a wrapped row of rounded pill badges, one per condition, each carrying that condition's label, its visible severity word, its non-colour severity glyph, and its duration/modifier text — the same content the roster shows today, none of it dropped — coloured per severity using the same severity-to-colour mapping the capped status-island condition chips use elsewhere in the HUD. These presentation rules apply identically whether a section is fully populated or marked with a registry-owned unavailable reason.

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
- **THEN** the hero shows that name, that title and `公會階級 <rank>` above one row holding the 技能書 and 同伴 ‧ 隊伍 openers, and the drawer title appears only in the shared header

### Requirement: The drawer layer renders the wallet exactly once
Across every drawer, the player's wallet SHALL be rendered exactly once per opening of the inventory drawer — once in its shared header subtitle and once as the single row of its `金錢` body section, both read from the committed available panel that owns the value — and nowhere else in the drawer layer. The shop, the lore reference, the character-status drawer, and every other body element of the inventory drawer SHALL NOT render a balance of their own. A drawer whose available character panel does not carry a committed non-negative integer wallet SHALL render no balance at all rather than a zero; the `金錢` body row is additionally gated on the bag's available inventory section, because it renders only inside the bag's three-section stack and the two renderings must never disagree.

#### Scenario: One wallet per drawer-layer opening
- **WHEN** every drawer is opened in turn with the `services` and `character` panels available
- **THEN** the only wallet values rendered across all of them are the inventory drawer's header subtitle and its `金錢` section row, both carrying the same integer copper value, and no other drawer or body element renders a balance

#### Scenario: An unavailable panel renders no balance
- **WHEN** the character panel that carries the wallet is unavailable
- **THEN** no drawer renders a balance, and none renders a zero in its place

#### Scenario: A missing wallet field renders no body row
- **WHEN** the inventory section is available but the character panel's wallet is not a committed non-negative integer
- **THEN** the `金錢` section renders no balance row and the header subtitle renders no balance either, since both read the same validated character-panel figure; neither renders a zero

### Requirement: Mutations issued from a drawer keep the dispatch and confirmation contract
Every affordance inside a drawer SHALL emit exactly the server-authored action identifier and payload
its descriptor carries, through the client's single dispatch entry, and SHALL be governed by the same
in-flight, epoch and revision gates as the same action issued from the dock. A disabled affordance
SHALL remain readable for its server-authored reason and SHALL submit nothing. While mutations are
locked — a submission in flight, an unaccepted revision, or a lost transport — every drawer affordance
SHALL be locked with them.

A destructive service action issued from a drawer SHALL sit behind an explicit confirmation step that
names what it does, with a cancel path that submits nothing. A quantity form inside a drawer SHALL
keep the server-advertised minimum and maximum and SHALL NOT permit a value outside them.

#### Scenario: A drawer affordance dispatches the exact server intent
- **WHEN** the player activates an enabled affordance inside a drawer
- **THEN** exactly one action is emitted carrying the descriptor's own action identifier and payload, through the same dispatch entry the dock uses

#### Scenario: Abandoning a quest from a drawer requires confirmation
- **WHEN** the player activates the abandon affordance on an active quest inside the quest drawer
- **THEN** a confirmation step renders naming the quest and what abandoning does, no mutation is sent, and cancelling returns without submitting

#### Scenario: A locked client locks the drawers
- **WHEN** a submission is in flight, its revision is unaccepted, or the transport is lost
- **THEN** every affordance inside every drawer is locked and emits nothing

#### Scenario: A quantity form keeps the server's bounds
- **WHEN** the player raises a quantity inside a drawer past the server-advertised maximum
- **THEN** the value is clamped to that maximum and no request can authorise a larger quantity

### Requirement: The command line is a collapsible row docked on the message region's top edge
The client's text control SHALL render as a single bar filling the stage's `command-line` anchor,
containing — in this order — a prompt chevron, the command input field with its send control, a hint
cluster, and the command-history controls. The bar SHALL carry no quick-word chip, no control that only
writes a fixed command word into the field, and no overlay or drawer opener: those openers live in the
top navigation bar's tool group. The `command-line` anchor SHALL be one row 44px tall docked to the top
edge of the bottom band's message region: its lower edge SHALL coincide with the band's upper edge, it
SHALL extend from the left HUD island column's right edge to the right edge of the band's left two
thirds in every mode — so in dialogue mode, where the message region spans the whole band, it stops
short of the dialogue host's portrait — and it SHALL overlay the lowest strip of the stage box, never
the band and never the message text.

The command line SHALL be collapsed by default. It SHALL start collapsed on every mount of the shell,
and its expanded state SHALL be client-local and never persisted, so no stored presentation state can
open it or keep it open. While collapsed, the row SHALL be hidden with `display:none`, so the bar and
its input field leave the layout, the accessibility tree, and the tab order, while the input field stays
in the DOM with its preserved identifier and keeps any unsent draft and history-walk state. The
message region SHALL carry, at its bottom-right corner, a labelled ⌨ toggle control that reports the
row's state through `aria-expanded` and names the row through `aria-controls`. The toggle SHALL be
rendered in every mode that renders the message region, SHALL NOT cover the message text (the text's
scroll region SHALL keep its last line clear of the toggle), and SHALL NOT be affected by the committed
narrative, the dialogue choice list, or the dock frame.

The command line SHALL expand, and focus SHALL move into its input field only after the row is
rendered, on exactly three paths: `/` pressed while no editable control is focused, activation of the ⌨
toggle while the row is collapsed, and the free-form dialogue borrow. It SHALL collapse, with focus
moved to the current mode's focus home (the action dock, or in dialogue mode the dialogue choice list
while it is rendered and the message window's page surface otherwise) before the row is hidden, on exactly two paths: Escape in the input field, and
a send the field accepts (the field clears). Activating the ⌨ toggle while the row is expanded SHALL
collapse it and leave focus on the toggle. A send the field rejects — offline, mutations locked, a
mutation in flight, or, for a borrowed free-form send, a presentation phase other than active — SHALL
leave the row expanded with the typed text and focus in the field. Losing
focus by any other means (a pointer activation elsewhere, a drawer or overlay opening) SHALL NOT
collapse the row.

The expanded bar SHALL NOT overlap the action dock, the narrative caption, the bottom band, or any HUD
island anchor at 1920x1080, 1440x900, or 1280x720. When horizontal space is insufficient, the hint
cluster SHALL be dropped first; the input field, its send control, and the history controls SHALL
never be dropped. (The command line and its toggle are absent from the layout in creation mode, per the
visibility matrix.)

#### Scenario: The field is one action away
- **WHEN** the shell mounts in exploration mode
- **THEN** the command-line row is hidden with `display:none`, the input field is present in the DOM but outside the tab order, the ⌨ toggle is rendered at the message region's bottom-right with `aria-expanded="false"`, and pressing `/` or activating the toggle once renders the row and puts focus in the input field

#### Scenario: The expanded row keeps its geometry at the minimum viewport
- **WHEN** the command line is expanded at 1280x720 and at 1920x1080, in exploration mode and in dialogue mode
- **THEN** the row is 44px tall (±1px), its lower edge sits on the bottom band's upper edge, its horizontal extent runs from the left HUD column's right edge to the right edge of the band's left two thirds, its rendered box intersects no HUD island anchor, band region, or other interactive stage anchor, and the input field, its send control, and the history controls are all rendered

#### Scenario: Constrained width drops the hint before any control
- **WHEN** the bar's content exceeds its available width
- **THEN** the hint cluster is removed first, and no input field, send control, or history control is removed

#### Scenario: Escape collapses and keeps the draft
- **WHEN** the player expands the command line with `/`, types a draft, presses Escape, and then activates the ⌨ toggle
- **THEN** Escape sends nothing, moves focus to the action dock, and hides the row, and the toggle expands the row again with the same draft in the field and focus in it

#### Scenario: A successful send collapses the line
- **WHEN** the player expands the command line, types a command, and presses Enter while the client is connected, unlocked, and has no mutation in flight
- **THEN** exactly one command is sent, the field clears, focus moves to the action dock, and the row is hidden with `display:none`

#### Scenario: A rejected send keeps the line open
- **WHEN** the player presses Enter in the expanded command line while mutations are locked or a mutation is in flight
- **THEN** the typed text stays in the field, focus stays in the field, and the row stays expanded

#### Scenario: The toggle closes the open line
- **WHEN** the command line is expanded and the player activates the ⌨ toggle with the pointer
- **THEN** the row is hidden, the toggle reports `aria-expanded="false"`, and focus is on the toggle

#### Scenario: The free-form borrow expands the line
- **WHEN** the command line is collapsed and the player activates the dialogue choice list's `⌨ 自由對話` row
- **THEN** the row expands, focus moves into the input field, and no action is dispatched until the player sends

#### Scenario: No opener or chip is rendered in the bar
- **WHEN** the bar renders expanded in exploration, combat, or dialogue mode
- **THEN** no quick-word chip, letter badge, chip cluster, or overlay or drawer opener (技能系譜, 圖鑑, 稱號冊, 設定, 說明, 角色肖像圖庫) is present in the bar

#### Scenario: The expanded state is never restored from storage
- **WHEN** the player expands the command line and reloads the page
- **THEN** the reloaded shell renders the command line collapsed

#### Scenario: Escape in dialogue returns to the message window
- **WHEN** the committed mode is dialogue, the player expands the command line with `/`, and presses Escape
- **THEN** nothing is sent, the row is hidden, and focus is on the dialogue's focus home — the choice list while it is shown, else the message window's page surface — never on the hidden action dock or the document body

### Requirement: The command line advertises only affordances this client implements
The hint cluster SHALL name only behaviour the client implements. It SHALL state the command-history
recall keys and the Tab-completion affordance — matching the draft's `↑↓ 歷史 ‧ Tab 補全` — and
Tab completion SHALL behave as named: pressing Tab inside the input field completes the current
draft against the client's candidate set (session command history and the committed exploration panel's exit names and interact-target display names, deduplicated). With exactly one matching candidate the field SHALL hold the full completion with
the caret at its end; with several the field SHALL hold the longest common prefix and successive
Tab presses SHALL cycle the matching candidates, with Shift+Tab reversing the cycle. A draft that
matches no candidate SHALL leave the field untouched, and Tab SHALL never move focus away from the
field at all (the release path is Escape, which the dock's shortcut legend names). The completion
cycle SHALL reset when the draft text is edited manually, and a change to the committed candidate
sources SHALL drop any in-flight cycle.

The history controls SHALL be labelled controls that drive the same history-walk state the recall
keys drive — one walk reached by two input paths — and SHALL NOT submit. No surface of the command
line SHALL name a key, gesture or affordance that has no implementation behind it.

#### Scenario: The hint names history and completion
- **WHEN** the hint cluster renders
- **THEN** it states the command-history recall keys and the Tab-completion affordance, matching
  the draft wording, and both are implemented

#### Scenario: Tab completes a unique candidate
- **WHEN** the field holds a draft matching exactly one candidate and the player presses Tab
- **THEN** the field holds that candidate in full with the caret at its end, and focus stays in
  the field

#### Scenario: Tab cycles ambiguous candidates
- **WHEN** the field holds a draft matching several candidates and the player presses Tab
  repeatedly
- **THEN** the field first completes to the longest common prefix and then cycles through the
  matching candidates, with Shift+Tab reversing the cycle, and any manual edit of the draft
  resets the cycle

#### Scenario: An unmatched draft is left alone
- **WHEN** the field holds a draft that matches no candidate and the player presses Tab
- **THEN** the field text and focus are unchanged

#### Scenario: The history controls walk the same state as the keys
- **WHEN** the player activates the previous-entry control and then presses the history recall key
- **THEN** both move through the same command-history walk in the same order, the draft is preserved across the walk, and neither submits

### Requirement: A full-screen overlay is one focus-trapped surface, and only one is open at a time
A full-screen overlay SHALL render as one shared surface laid over the stage, carrying the shared
reference-surface header naming the surface and a labelled close control, with its body as its only
scrolling region. Utility overlays SHALL use the same opaque reference workspace as the reference
drawers: 12px below the top navigation's bottom edge, 16px inside each side of the viewport, and one
command-line row height plus 12px above the viewport bottom, so the workspace covers the stage, the
bottom band, and the command-line row whether or not that row is expanded, and only the band's lowest
control strip stays exposed beneath it. A scrim SHALL cover everything below the top navigation behind
the overlay, recessing that exposed strip, and SHALL absorb pointer activation without closing the
overlay, so no command control behind the overlay is reachable by pointer; the scrim starts at the top
navigation's bottom edge and does not cover it, so the navigation stays operable and activating another
overlay or drawer trigger replaces the open overlay as below. The mode-owned creation workspace is excluded from these utility-frame bounds. While an overlay
is open it SHALL trap keyboard focus, so no surface behind it is reachable by sequential navigation. It
SHALL close on Escape and on activation of its close control, and both paths SHALL restore focus to the
control that opened it. It SHALL use the shared focus trap the client already owns rather than a second
implementation.

At most one overlay SHALL be open at any time; opening a second SHALL close the first, and the opener
recorded for the replacement is the control that opened it, so closing restores focus to the most recent
trigger, never to the trigger of the closed overlay. An overlay and a
reference drawer SHALL NOT be open together: opening either SHALL close the other, so at most one
focus-trapped surface exists at any moment. An open overlay SHALL register itself as an open surface so
the stage recession this capability already requires applies without a second mechanism.

Escape SHALL be resolved by a single precedence order, topmost first — a popover open inside the open
overlay, then the open overlay, then an open drawer, then the focused command field, then the dock's
current menu level — with each level consuming the key and stopping. A popover open inside an overlay
SHALL close on Escape without closing the overlay, keeping focus inside the overlay, and the next
Escape SHALL close the overlay; while no such popover is open, Escape closes the overlay as above.

A mode change into creation, a presentation-epoch reset and a loss of the transport SHALL each close
every open overlay. The mode-driven character-creation surface SHALL NOT be part of this single-open
stack, because it is not opened by the player and a utility control must never dismiss it.

#### Scenario: An overlay opens, traps focus, and returns it
- **WHEN** the player activates an overlay trigger, cycles focus forward past the overlay's last control and backward past its first, and then presses Escape
- **THEN** focus stays inside the overlay in both directions, the overlay closes on Escape, and focus returns to the trigger that opened it

#### Scenario: Only one overlay is open at a time
- **WHEN** an overlay is open and the player activates a different overlay's trigger
- **THEN** the first overlay closes as the second opens, and exactly one overlay is present

#### Scenario: An overlay and a drawer are never open together
- **WHEN** a reference drawer is open and the player activates an overlay trigger
- **THEN** the drawer closes as the overlay opens, and exactly one focus-trapped surface is present

#### Scenario: Escape resolves at exactly one level
- **WHEN** an overlay is open above a focused command field and a dock frame at depth two, and the player presses Escape once
- **THEN** the overlay closes, focus returns to its trigger, the command field's content is untouched, and the dock's menu depth is unchanged

#### Scenario: Closing the last overlay clears the recession
- **WHEN** the open overlay closes and no drawer remains open
- **THEN** the stage's recession mark is cleared

#### Scenario: A creation transition closes the overlays
- **WHEN** the committed mode changes to creation while an overlay is open
- **THEN** that overlay closes, focus is routed to the action dock, and the character-creation surface is not itself treated as one of the single-open overlays

#### Scenario: An overlay's own popover takes Escape first
- **WHEN** the full-map overlay is open with its legend popover expanded, and the player presses Escape twice
- **THEN** the first Escape closes only the popover and focus stays inside the overlay, and the second Escape closes the overlay and returns focus to the trigger that opened it

### Requirement: The map, settings, and help surfaces are reachable from the live client
The map, settings and help surfaces SHALL each be reachable from the running client by a labelled
control, not only from the component showcase. The minimap island SHALL carry a labelled control that
opens the map surface, rendered as a sibling of its map canvas rather than as a wrapper around its
actionable nodes; the island's non-interactive body MAY additionally open the same surface on pointer
click, which SHALL NOT replace or wrap the labelled control. The top navigation bar's labelled 設定
control and the 說明 control in its tool group SHALL open the settings and help surfaces, in every mode
that renders the top navigation bar, whether the command line is expanded or collapsed.

The map surface SHALL render the committed `local_map` payload through the same component the minimap
island renders, and SHALL re-render its available and unavailable branches whenever that read model is
replaced, so a superseded payload never leaves a stale map or a stale reason on screen; when a newly
committed payload resolves to the other layout variant, the surface follows the resolved value with no
control of its own. It SHALL open fitted, showing the whole drawing inside its body, and SHALL offer
exactly the view affordances the full-map fit-view requirement of the local-map capability defines —
wheel and `+` / `-` zoom within that requirement's bounds, labelled 放大 and 縮小 buttons, drag-pan, a
labelled 置中 button that recentres the current node, and a `?` disclosure button named 圖例 that opens
the state legend in a popover — and it SHALL name those gestures in words in its guide row. Those
affordances change only the view of the drawing: none of them SHALL change the committed payload, the
resolved layout variant, or any geometry the surface declares, and none SHALL be persisted. It SHALL
render no bearing, compass angle, distance, or coordinate figure, on any layer, and no zoom level,
scale ratio, or other figure describing the view.

The map surface's body SHALL carry the redesign draft's map-canvas framing (the radial-gradient dark
terrain background painted as pure CSS inside a rounded ink border), and SHALL NOT fabricate terrain
geometry the payload does not claim.

The help surface SHALL render the client's own control reference — the keys this client binds, the dock's
navigation model and the close paths — from a single client-owned source, and SHALL
state how the game's own help output is reached. It SHALL name no key binding
or control the client does not implement, SHALL describe `/` and the ⌨ toggle as expanding the command
line and Escape and a successful send as collapsing it, and SHALL NOT render authored game-help content for which
no committed panel exists, and SHALL NOT stand a placeholder in for it.

#### Scenario: Each surface has a live trigger
- **WHEN** the client renders in exploration mode with the `local_map` panel committed and the command line collapsed
- **THEN** the minimap island carries a labelled control that opens the map surface, and the top navigation bar carries a labelled 設定 control and a labelled 說明 control in its tool group that open the settings and help surfaces

#### Scenario: The map surface tracks read-model replacement in the live client
- **WHEN** the map surface is open and an update replaces the committed `local_map` payload with the registry-owned unavailable form, and then with a different available payload
- **THEN** the surface renders only the registry-owned reason, then the replacement map, and at no point shows a map or a reason from the superseded payload

#### Scenario: The map surface advertises no zoom or pan
- **WHEN** the map surface renders on any layer
- **THEN** its only view controls are the labelled 縮小, 放大, and 置中 buttons and the 圖例 disclosure
  button, its guide row names the wheel, `+` / `-`, and drag gestures in words, the legend appears only
  inside the 圖例 popover, and no zoom level, scale ratio, bearing, compass angle, or distance figure
  appears anywhere on the surface

#### Scenario: The map surface frames the draft canvas without invented terrain
- **WHEN** the map surface renders an available payload
- **THEN** the map body shows the radial-gradient ink background inside the rounded ink frame, and no terrain, coastline, or route geometry is drawn that the payload does not carry

#### Scenario: The help surface tells the truth about what it knows
- **WHEN** the help surface renders with no committed panel carrying authored guide content
- **THEN** it renders the client's own control reference, including `/` and the ⌨ toggle expanding the command line and Escape collapsing it, and a statement of how the game's help output is reached, and it renders no authored game-help entry and no placeholder standing in for one

### Requirement: Narrative prose scale is a client-local preference the settings surface owns
The client SHALL expose a narrative prose scale with three steps, selectable from the settings surface,
whose current step is marked by an indicator that does not rely on colour alone. The scale SHALL apply
to narrative and dialogue prose only — the message window's page text, the complete-log surface's lines,
the prompt line and the settings surface's reading sample, which previews the page text — and SHALL NOT alter HUD, dock, drawer, overlay or any other interface text, so the
stage's measured anchor geometry is unaffected at either supported viewport.

The prose scale and every other setting the surface offers SHALL be client-local presentation state. No
settings control SHALL dispatch an action: the client's action allowlist carries exactly one `options.*`
action, the suggestions dismissal, and this capability adds none. Each setting SHALL be applied
immediately to the presentation it governs — the document's presentation tokens for the prose scale,
the motion level, the text-to-HTML toggle and the colourblind palette, and the message window for the
reading preferences and the motion level — and SHALL be persisted through the client's versioned,
presentation-only browser store as a harmless display preference. Each setting SHALL be re-applied at
load, and SHALL be reset to its default — fully applied, never half-applied — whenever that store
resets. The motion level SHALL follow "The motion level is a client-local preference that governs every
client animation": a stored level overrides the operating system's reduced-motion preference, which
SHALL continue to apply while no level is stored.

The settings surface SHALL offer no control it does not implement.

#### Scenario: The prose scale moves prose and nothing else
- **WHEN** the player selects the largest prose scale
- **THEN** the message window's page text, the complete-log surface's lines, the prompt line and the settings surface's reading sample render larger, every other HUD, dock and overlay label is unchanged, and no stage anchor's rendered box intersects another's at 1440x900 or 1280x720

#### Scenario: No setting dispatches an action
- **WHEN** the player changes every control the settings surface offers
- **THEN** no `ui_action` is sent for any of them, and the only `options.*` action the client can dispatch remains the suggestions dismissal

#### Scenario: A setting survives a reload and resets cleanly
- **WHEN** the player changes the prose scale, the text speed, and the motion level, reloads the client, and then the presentation store's stored version is unrecognised
- **THEN** the chosen scale, text speed, and motion level are re-applied after the reload, and after the reset every setting is applied at its default, the motion level following the operating system again, with no setting left partly applied

#### Scenario: Reduced motion overrides, and defers when unset
- **WHEN** no motion level is stored and the operating system requests reduced motion
- **THEN** the effective motion level is `reduced`, so looping and travelling motion stops and message pages appear in full at once; and when the player then selects `完整`, the client honours that stored level over the operating system

#### Scenario: The surface offers nothing inert
- **WHEN** the settings surface's controls are enumerated
- **THEN** every control changes an outcome the client actually implements, and no control is rendered that has no effect

### Requirement: Narrative lines carry the reference's semantic classes
Committed narrative lines SHALL render with the reference draft's semantic presentation: a line of
committed `sys` kind SHALL render in the sans face at the reference's secondary size and colour with
a leading `◈` seal-colour marker contributed by the line's own class, not by invented text;
emphasis inside prose lines SHALL render in the reference's gold accent; plain prose lines SHALL
render in the serif reading face. The classes SHALL be mounted by the existing markup pipeline at
render time from committed line kinds only — the tokenizer, the player-echo divider lines, and the
box-drawing art path SHALL be unchanged, and no markup class SHALL be mounted for a kind the store
does not carry. The markup pipeline SHALL run exactly once for each retained server, system, or error
line, when the line is retained. Every surface that renders the line SHALL render from that one token
stream, never from a second tokenization or a second markup path. A player input line SHALL never
enter the pipeline. A fragment of a line that paging has split SHALL render with the same kind class,
and the same box-drawing class where it applies, as the whole line would. Only the first fragment
of a `sys` line SHALL show the leading `◈` marker.

#### Scenario: A sys line renders with the seal marker
- **WHEN** a committed narrative line of kind `sys` renders
- **THEN** the line carries the reference's sys treatment including the leading `◈` marker, and the
  marker is decorative (absent from the accessible name of any surrounding live region update that
  already names the line's text)

#### Scenario: Emphasis renders gold inside prose
- **WHEN** a committed prose line carries emphasis through the markup pipeline
- **THEN** the emphasis renders in the reference's gold accent without changing the surrounding
  prose face

#### Scenario: Unknown kinds do not gain semantic classes
- **WHEN** a committed line carries no semantic kind beyond plain output
- **THEN** it renders as plain serif prose without the sys marker

#### Scenario: Each line is tokenized once
- **WHEN** a server line is retained and is then rendered by the narrative surface and by the
  full-log surface, each more than once
- **THEN** the markup pipeline has run for that line exactly once, and both surfaces render the
  same token stream

#### Scenario: A split line's fragments keep the line's classes
- **WHEN** a `sys` line, and separately a prose line carrying emphasis, are each split into two
  fragments
- **THEN** both fragments of the `sys` line carry the sys face and colour, only the first shows the
  `◈` marker, and both fragments of the prose
  line render in the serif reading face with the emphasis still gold in whichever fragment holds it

### Requirement: The party drawer presents compbig rows and the fixed follow rules
The 同伴 ‧ 隊伍 drawer SHALL render on the shared reference drawer contract with the sub-count
`N / 4`, one compbig row per committed party slot (initial-letter/gold avatar with the same
portrait fallback, display name, bond stage line, HP bar with numerals, the joined 參戰 token
when the companion fights, and a 請其離隊 control), and one 空位 row stating the invite rule in
stage-name words — the raw affinity threshold number SHALL NOT be shown. The 空位 row's
`邀請當前 NPC…` control SHALL dispatch `explore.party_invite` with the exact existing payload
`{npc_id: <the committed invite-capable interact target's identity>, message: ""}` — the fixed
empty message, since the drawer invents no freeform invitation input — under the existing
dispatch and confirmation contract, enabled only when the committed exploration context names
an invite-capable interact target, and SHALL be disabled with its rule line as the reason
otherwise — it SHALL never fabricate a target. Activating 請其離隊 SHALL dispatch `explore.party_leave` for that identity
under the same contract. The drawer SHALL close the party section with three fixed follow-rule
statements matching the reference draft verbatim, and SHALL render no companion detail control
that has no backing read model.

#### Scenario: Rows follow the committed party
- **WHEN** the drawer is open and a party mutation commits a third companion
- **THEN** a third compbig row appears with its committed fields and the sub-count reads `3 / 4`

#### Scenario: Leaving dispatches through the confirmation contract
- **WHEN** the player activates 請其離隊 on a companion row
- **THEN** the existing confirmation flow submits `explore.party_leave` for that identity and the
  row disappears only when the corresponding commit lands

#### Scenario: The invite control is honest about its preconditions
- **WHEN** the exploration context carries no invite-capable interact target
- **THEN** 邀請當前 NPC… is disabled with the stated rule as its reason and dispatches nothing,
  and the raw invite threshold number is never shown

#### Scenario: The follow rules are the reference's three lines
- **WHEN** the drawer body is enumerated
- **THEN** the 跟隨規則 card carries the reference draft's three fixed statements and no invented
  rules

### Requirement: The objective tracker island presents the committed objectives only
The HUD SHALL carry the objective tracker as one line in the stage's `map` anchor, directly beneath
the minimap island, while the committed mode is exploration and the committed `objectives` panel is
available with a non-empty `rows` list; it SHALL be hidden with `display:none` in combat and dialogue
mode and SHALL render nothing when `rows` is empty, when the panel is unavailable, or in creation mode.
The line SHALL have one fixed row height whatever the payload holds and SHALL carry, in order: a
`目標` label; a stage box for the first row of `objectives.rows` showing a completion check when that
row's `stage_progress >= objective_quantity` and an empty box otherwise; that first row's
`objective_line`, truncated on one line with an overflow indicator while its full text stays the line's
accessible text and tooltip; a mono-gold slot carrying `stage_progress / objective_quantity` when the
first row's `objective_quantity` is greater than one and its `+reward_copper` when `objective_quantity`
is one and `reward_copper` is non-null, and carrying nothing otherwise; and, when more than one row is
committed, a mono-gold `+N` count where `N` is the number of further rows. Rows after the first, and
every row's `deadline_line`, SHALL NOT be rendered on the stage; the quest drawer presents them. The
tracker is display-only: it SHALL render no accept, abandon, turn-in, or tracking control and SHALL
dispatch no action. It SHALL present no objective prose the panel does not carry and no invented
optional or previous-stage rows.

#### Scenario: Active objectives list in payload order
- **WHEN** a snapshot commits two objective rows in exploration mode, the first with progress 2 of quantity 5 and the
  second a single-count quest with an 80-copper reward
- **THEN** the line renders `目標`, the first row's describe-seam objective line with its `2/5` tag, and
  a `+1` count, the second row's objective line and `+80` tag are not rendered on the stage, the line's
  height equals its single-row height, and no control is present

#### Scenario: A satisfied objective shows the done box
- **WHEN** the first committed row carries `stage_progress` equal to `objective_quantity`
- **THEN** the line's stage box renders the completion check

#### Scenario: An empty or unavailable objective list hides the island
- **WHEN** the committed `objectives.rows` becomes `[]` or the panel becomes unavailable
- **THEN** no objective line is rendered anywhere in the HUD

#### Scenario: The tracker dispatches nothing
- **WHEN** the player interacts with the objective line
- **THEN** no `ui_action` or text command is sent and no mutation control is present

#### Scenario: A long objective line truncates in place
- **WHEN** the first row's `objective_line` is longer than the line's width
- **THEN** the text is truncated with an overflow indicator, the line keeps its single-row height, and the full `objective_line` is the line's accessible text

### Requirement: The skill book offers a bounded declared-practice sub-screen
The skill-book drawer SHALL offer a 修煉 affordance on each active skill row the committed
`character` panel supports, and activating it SHALL replace the book body with a practice
sub-screen inside the same drawer: the drawer title becomes 修煉, the body lists the panel's
active skills for selection, and one bounded-duration control starts the practice. The browser
SHALL compute nothing about eligibility, duration outcome, or progression: every row state comes
from the committed panel, the duration control reuses the waiting surface's bounded hours form, and
confirmation SHALL submit exactly one `explore.practice` with the selected `skill` and the
converted whole `seconds` through the shared dispatch/confirmation lock. While a submission is in
flight or its declared presentation revision is pending, the control SHALL be disabled. The
server-authored result line (success summary or rejection message) SHALL render as escaped text
inside the sub-screen and nowhere else, and closing the sub-screen SHALL restore the book body,
the original drawer title, and the book's cast-syntax footer.

#### Scenario: Practice dispatches one server-trusted intent
- **WHEN** the player opens 修煉 from an active skill row, selects the skill, enters `2` hours, and confirms
- **THEN** exactly one `ui_action` is submitted — `explore.practice` with that `skill` and `seconds: 7200` — and the drawer controls stay locked until the result revision is adopted

#### Scenario: The result line is the server's
- **WHEN** a practice result arrives
- **THEN** its Traditional Chinese summary or rejection message renders verbatim as escaped text in the sub-screen, with no client-computed progression, elapsed-time, or eligibility claim

#### Scenario: The practice screen is gated by committed data only
- **WHEN** the `character` panel is unavailable or a row carries no practice support
- **THEN** no 修煉 affordance renders for that row and no practice state is invented

#### Scenario: Closing the practice screen restores the book
- **WHEN** the player closes the practice sub-screen
- **THEN** the drawer shows the skill book again with its original title and its cast-syntax footer, and no second drawer was opened

### Requirement: The reference surfaces have no permanently visible home and are reached from the top navigation or the dock
The skill book, the bag and equipment, the shop, the quest board, the lore reference and the character
status SHALL each render in exactly one place — its drawer — and SHALL NOT be present in the DOM while
that drawer is closed. The stage SHALL carry no permanently visible column of reference panels.

Each drawer SHALL be opened either by the dock frame that owns its surface, or by a single labelled
control inside a drawer that already presents the same read model, or by a surface this capability
names elsewhere as an opener for it. No reference surface SHALL require more than two actions from
the top navigation bar or the dock's root frame to reach. Opening a drawer SHALL NOT change any dock root item, any menu frame, any
menu key, or the meaning of Escape.

#### Scenario: No reference surface is mounted while the drawers are closed
- **WHEN** the stage renders in exploration mode with every drawer closed
- **THEN** no skill book, bag, shop, quest board, lore reference or character-status element exists in the DOM or in the tab order, and no reference column is rendered

#### Scenario: Every reference surface is reachable from the dock
- **WHEN** the player starts at the dock's root frame or the top navigation bar
- **THEN** each of the six reference surfaces is reached in at most two actions, and the narrative caption stays in the bottom band's message region

#### Scenario: An emptied right-hand stack costs nothing
- **WHEN** the stage renders at 1440x900 and 1280x720 with every drawer closed
- **THEN** the top-right `map` anchor renders no reference panel, contributes no visible box and no tab stop, and no interactive stage anchor's rendered box intersects another's

### Requirement: The action dock fills the band's command region at a fixed size
The action dock SHALL fill the bottom band's command region — the right third of the band, or the
whole band in creation mode — at the band's fixed height, and SHALL NOT be a floating panel placed
elsewhere on the stage. Its box SHALL be the command region's box in exploration, combat, and creation
mode and for every frame: no frame (the scene overview, a target's verb popover, the waiting frame, the
combat frames, the skill master-detail, the destructive confirmation, or an empty pane host) SHALL
widen, heighten, shorten, or move it, and
no surface outside the band SHALL be positioned from the frame the dock currently carries. In dialogue
mode the command region is collapsed and the dock SHALL be hidden with `display:none` together with it,
as "The command region collapses in dialogue mode and the message window spans the band" states; it
SHALL NOT be rendered anywhere else in that mode. The
content column SHALL be laid out as fixed chrome — the combat root's vertical command list in combat mode and no bar
in exploration mode, an optional breadcrumb line, and the shortcut-legend strip at the
bottom — around one remaining region that holds the current frame's rows or chips; that region SHALL
be the surface's only scrolling area, so no dock content is ever pushed outside the command region.
A target's verb popover SHALL render as a card laid over that region's visible box, inside the command
region, and SHALL scroll inside its own card when its rows exceed it. A frame whose content
does not fit the region's width SHALL wrap or collapse its own columns inside the region, never
overflow it horizontally. The panel SHALL be the same single `#action-dock` element in every mode,
carrying its existing tab index, its `data-mode` attribute and its role as the documented focus home
of every mode except dialogue, and SHALL NOT be remounted when the mode changes, including a change
into or out of dialogue.

The command region SHALL use the current charcoal-and-gold presentation, and the band that contains
it SHALL paint the reference's band chrome. Selected actions remain distinguishable by text and shape
as well as their gold or warm-red emphasis.

#### Scenario: The command region is the band's right third
- **WHEN** the shell renders in exploration mode at 1920x1080, 1440x900, and 1280x720
- **THEN** the `#action-dock` element lies inside the band's command region, the region's left edge is at two thirds of the stage width and its right edge at the stage's right edge (each ±1px), and the dock covers neither the message region nor the command line

#### Scenario: No frame resizes the command region
- **WHEN** the dock moves at 1440x900 from the scene overview to a target's verb popover, to the waiting frame, and, in combat, to the deepest skill target frame
- **THEN** the command region's rendered box is identical (±1px) in all four states, the band's height is unchanged, and the verb popover's card lies inside the command region

#### Scenario: An overflowing frame scrolls inside the panel
- **WHEN** the current frame holds more rows than the dock's row region can display
- **THEN** the row region scrolls internally, the dock's chrome (the combat root list, the breadcrumb,
  and the legend strip) stays fixed, and no row or chip is rendered outside the command region

#### Scenario: One dock element persists across a mode change
- **WHEN** the committed mode changes between exploration, dialogue, combat and creation
- **THEN** exactly one `#action-dock` element exists at every point, its `data-mode` attribute
  switches to the new mode, it is hidden with `display:none` exactly while the mode is dialogue, and
  it is not removed and re-created

#### Scenario: The panel stays inside its region at the minimum viewport
- **WHEN** the shell renders at 1280x720 with the deepest combat frame open
- **THEN** the dock's rendered box stays within the command region, no dock content overflows the
  region horizontally, and the frame's confirm control is reachable by scrolling the row region
  without being clipped

#### Scenario: The band's background matches the reference's shadowed gradient
- **WHEN** the bottom band renders in any mode
- **THEN** the band element paints a background gradient and a box-shadow, its top edge is the
  seam's fine gold line drawn by the band's own decoration, and the `#action-dock` content column
  itself paints no background, border, or shadow

### Requirement: The place card names the current location and the world time
This requirement carries the `place-card-relocation` amendment; the visible-mode set below narrows to exploration and combat with this change, matching the visibility matrix's dialogue `hidden` cells.
The stage SHALL carry a place card as the first island of its `map` anchor, at the stage box's
top-right corner directly below the top band and directly above the minimap island, while the
committed mode is exploration or combat, and SHALL NOT render it in
creation mode or settled dialogue mode. During live dialogue entry it MAY retain only the inert exit
paint permitted by "Surface visibility is gated by the committed game mode", outside the accessibility
tree and tab order from commit, and SHALL become `display:none` when the anchor's fade ends.
The card SHALL state the current location as its heading and the world date/time
beneath it, and SHALL be the only surface on the stage or in the top band that states either value.
The location SHALL be the best server-authored place name the client already holds, resolved in a
fixed order: the committed `local_map` panel's `current_node` label when that panel is available,
names a current node, that node is present in the panel's nodes, and its label is a non-empty string;
otherwise the committed status panel's actor location label; otherwise the card's own unavailable
placeholder `位置：--`. The world date/time SHALL be the committed world-time label, and the card's own
unavailable placeholder `時間：--` when none is committed. The card SHALL NOT compose a third string
from the two location candidates, SHALL NOT derive a name from any node or room identifier, SHALL NOT
render a raw room key while a committed panel carries the authored place name for the same room, and
SHALL render no raw mode label in place of the location.

The card SHALL wear the HUD island chrome (the translucent panel fill, the backdrop blur, the
hairline border, the shared radius and shadow, all from the shared design tokens), SHALL span the same
content-column width as the minimap island beneath it, SHALL keep a fixed
height whatever the label lengths, and SHALL truncate a label that exceeds its width with an overflow
indicator while keeping the full label as its accessible text. It SHALL be display-only: no control,
no tab stop, and no dispatch.

The card SHALL set its two values on two levels: the location heading in the serif face at the
`--text-lg` step, then a quiet decorative gold rule, hidden from assistive technology, then the
world-time line. The world-time line SHALL carry no leading separator glyph or rule before its first
value, SHALL use the
numeral face with tabular, lining figures at the `--text-sm` step (no smaller than the 12px chrome
floor), and SHALL render the committed world-time label (or its placeholder) verbatim, with every
date and time value intact: all time values SHALL remain server-authored, and the card SHALL NOT
reformat, abbreviate, or derive them. The heading, the rule, and the time line SHALL fit the card's
fixed height.

#### Scenario: The card names the location and the time
- **WHEN** the shell renders in exploration mode with a committed status location `測試起點` and world time `春季 3 日 ‧ 12:00`, and no `local_map` panel
- **THEN** the place card's heading reads `測試起點`, its second line reads `春季 3 日 ‧ 12:00`, and no other stage or top-band element states either string

#### Scenario: The card heads the map column
- **WHEN** the shell renders in exploration mode with a committed `local_map` panel
- **THEN** the place card is the first island of the `map` anchor, its rendered width equals the minimap island's rendered width, and the stage renders no place card in its left column

#### Scenario: The card names the region, not the raw room key
- **WHEN** the player stands in a wilderness cell whose status location label is the raw room key `Wilderness` while the committed `local_map` panel's current node is labelled 西部丘陵與谷地
- **THEN** the card's heading reads 西部丘陵與谷地, `Wilderness` is rendered nowhere in the card, and no composed string pairing the two appears

#### Scenario: The card falls back to its placeholders
- **WHEN** neither the `local_map` panel nor the status panel supplies a location label, and no world time is committed
- **THEN** the card reads `位置：--` and `時間：--`

#### Scenario: The card keeps its size and is absent in creation
- **WHEN** a location label longer than the card's width commits, and later the committed mode becomes creation, and later dialogue
- **THEN** the card's rendered box is unchanged and the label is truncated with its full text still exposed to assistive technology, and in creation mode and in settled dialogue mode the place card is not rendered and holds no tab stop; during live dialogue entry only its inert exit paint may remain until the map anchor's fade ends

#### Scenario: No prefix exists
- **WHEN** a time line has no preceding qualifier
- **THEN** it renders without a leading dash and retains every actual date/time value

#### Scenario: The heading and the time read as two levels
- **WHEN** the place card renders a location and a committed world time
- **THEN** a decorative gold rule lies between the heading and the time line, the heading is set one
  step below the display size the stage's island chrome uses at `--text-lg`, the time line's numerals
  are tabular lining figures in the numeral face, and the card keeps its fixed height

### Requirement: Text speed and auto-advance are client-local reading preferences the settings surface owns
The settings surface's reading section SHALL offer a text-speed control with the four steps `慢`
(`slow`), `標準` (`normal`), `快` (`fast`), and `瞬間` (`instant`), and an auto-advance toggle
(`自動翻頁`). The text speed SHALL default to `normal` and auto-advance SHALL default to off. The
current text-speed step SHALL be marked by an indicator that does not rely on colour alone, and SHALL
be exposed as the pressed state of its button. The text-speed control SHALL say that the `減少` and
`關閉` motion levels show pages at once, because an effective motion level other than `full`
overrides the chosen speed as `webclient-input-narrative` defines. Both preferences SHALL follow the
settings rules of "Narrative prose scale is a client-local preference the settings surface owns":
client-local, dispatching nothing, applied to the message window immediately, persisted through the
versioned presentation-only browser store, re-applied at load, and reset to their defaults when that
store resets. A stored value outside the defined steps SHALL be discarded, and the default SHALL
apply.

#### Scenario: Choosing a text speed applies and persists it
- **WHEN** the player opens the settings surface and selects `快`
- **THEN** the `快` button is pressed and marked by a non-colour indicator, the next page the
  message window shows types at the fast speed, the stored wrapper carries `textSpeed: "fast"`, and
  no `ui_action` is sent

#### Scenario: Auto-advance is off until the player turns it on
- **WHEN** the client loads with no stored preferences, and the player then turns on `自動翻頁`
  and reloads
- **THEN** auto-advance is off on the first load, and after the reload the toggle is on and a fully
  shown page with a next page advances on its own

#### Scenario: An invalid stored speed falls back to the default
- **WHEN** the stored wrapper carries a text speed outside the four steps
- **THEN** the client loads with the `normal` speed, and the other stored preferences still apply

### Requirement: A fixed-column dock pane stays inside the command region
When a dock pane's row region uses a fixed column count for keyboard row/col geometry, that fixed count
SHALL govern only which cell each row occupies. This requirement SHALL NOT prescribe how wide a column
or row renders: each pane form (the combat skill list, the target tokens, the scale chips) lays out its
rows with its own styles, and whether a form fills the pane's width or leaves width empty is a visual
decision of that form. Whatever the form, every row SHALL render inside the pane's box without
horizontal overflow: when the pane's available width is narrower than the rows' natural width, the rows
SHALL wrap or compress, and long content SHALL wrap within its row. Changing a row's rendered width
SHALL NOT change which row occupies which cell. The scene overview is not a fixed-column pane (its chips
wrap by width under the section geometry the exploration dock requirement defines).

#### Scenario: A narrow command region keeps every row inside the pane
- **WHEN** a combat skill, target, or scale pane renders in the command region at the minimum supported 1280x720 viewport
- **THEN** every row lies inside the pane's right edge, the pane shows no horizontal overflow, and a long label wraps within its row

#### Scenario: Rendered width never changes the keyboard cell mapping
- **WHEN** the player presses ArrowRight in a pane whose keyboard geometry fixes two columns
- **THEN** focus reaches the row that the fixed column count places in the second column, whatever width each row renders at

### Requirement: The command region collapses in dialogue mode and the message window spans the band
While the committed mode is `dialogue`, the bottom band's command region SHALL be collapsed and the
message region SHALL span the band's whole width at the band's fixed height from the commit's frame. The
collapsed region and the action dock inside it SHALL leave the accessibility tree, the tab order, and
pointer hit-testing from the commit's frame; the region SHALL then slide out to the right and fade over
the panel duration of the client's motion level, drawn over the widened message region, and SHALL be
`visibility: hidden` once that slide ends, so it contributes nothing visible. Leaving dialogue SHALL
bring the region back into reach in the commit's frame and slide it back in from the right. At
`reduced` the region only fades, within 150ms, and at `off` it hides and returns in the commit's
frame. The dock SHALL stay the same mounted `#action-dock` element, its router SHALL keep the exploration scene overview as its only frame (the reset on entering
dialogue that `webclient-exploration-menu` defines), and leaving dialogue SHALL show that overview
again with no remount. The dialogue SHALL NOT present any dock frame, and no exploration affordance
SHALL be removed from the committed `exploration` panel: movement stays reachable through the minimap
and the conversation's own controls.

In dialogue mode the shell's focus home SHALL be the dialogue choice list while it is rendered, and
otherwise the message window's page surface. Every path that returns
focus to the focus home — the command line's Escape and accepted send, the mode-change rescue, and the
return after a completed or rejected action — SHALL land there, never on the hidden dock and never on
the document body. On entering dialogue, focus held inside the command region SHALL move to the
message window's page surface before the region is hidden. On leaving dialogue for exploration, focus
held inside the message region, inside the `choices` anchor, or on the document body SHALL move to the
action dock once the region is rendered again.

While the mode is `dialogue`, the keyboard router SHALL claim only `/` (the command-line opener); every
other key SHALL be unclaimed by the dock router, so no key moves the hidden dock's focus, pushes or pops
a frame, or activates a hidden entry. The keys the dialogue choice list handles never reach the router,
and Enter and Space on the focused page surface keep their reading meaning.

#### Scenario: Entering dialogue collapses the command region
- **WHEN** the player activates 交談 in a host's verb popover at 1920x1080 and the commit makes the mode `dialogue`
- **THEN** from the commit's frame the band's command region and the `#action-dock` element are out of the accessibility tree and the tab order, the message region spans the band's whole width at 300px (±1px) height, the region is `visibility: hidden` once its slide ends, focus is on the message window's page surface while the greeting is read, and focus moves to the dialogue choice list when the greeting's last page is fully shown

#### Scenario: Leaving dialogue restores the overview without a remount
- **WHEN** the player activates the exit row and the commit returns the mode to `exploration`
- **THEN** the same `#action-dock` element is back in the accessibility tree in the commit's frame, slides back into the command region at the scene overview with no popover open, and focus is on the action dock

#### Scenario: Keys never drive the hidden dock
- **WHEN** the mode is dialogue, focus is on the document body, and the player presses ArrowRight, Enter, and Escape
- **THEN** none of the keys is claimed by the dock router, the router's focused key and depth are unchanged, and no `ui_action` is emitted

#### Scenario: Slash still opens the command line in dialogue
- **WHEN** the mode is dialogue, no editable control is focused, and the player presses `/`
- **THEN** the command line expands and focus moves into its input field with no literal `/` inserted

#### Scenario: Movement stays reachable during a conversation
- **WHEN** a dialogue session is live and the player activates an adjacent minimap node
- **THEN** the move dispatches exactly as in exploration mode, the movement settlement clears the session through the existing seam, the committed mode returns to `exploration`, and the command region renders the new room's overview

### Requirement: Stage actors present the player and the dialogue host with a speaking state
Each standing portrait on the stage SHALL be rendered by one stage-actor component. The controlled
figure and companions in `actor-left` SHALL follow the companion-lineup rule. The dialogue host SHALL
render once: when its committed identity joins to a committed party slot or controlled lineup figure,
its existing lineup StageActor is the host and no duplicate renders in `actor-right`; otherwise the
host's stage actor in `actor-right` SHALL present the committed `art` panel's `portrait_catalog` entry
named by `dialogue.host.portrait_ref` — the complete image bottom-aligned with contain fit, and a
grounded silhouette with host identity and authoritative availability when the entry is a placeholder.
When `portrait_ref` is null or names no catalog entry, the host's stage actor SHALL render the truthful
placeholder: the display name's initial and display name, never a stock or guessed image. The client
SHALL NOT construct a catalog key from host identity or any other field. Each foe's stage actor SHALL
present its committed catalog entry under the same complete-image, grounded-silhouette and
display-name-placeholder rule.

While committed mode is dialogue and the available host renders, stage actors SHALL carry a speaking
state. The speaker SHALL be at full brightness and listeners dimmed to 60% through the shared dim token.
The host SHALL speak except while an `explore.talk_scripted` or `explore.talk_freeform` action submitted
by the player is in flight — from dispatch until its result is handled and declared presentation revision
accepted, or until rejection — when the player SHALL speak. Derive this state from dispatch state,
committed mode and panel availability, never prose. Companions SHALL remain listeners unless their
identity matches that active host; a speaking companion temporarily receives the highest z without
moving, then restores baseline z. Outside dialogue, or while its panel is unavailable, the controlled
figure SHALL remain lit; foes SHALL never be dimmed. No other dialogue behavior changes: the name plate,
pagination, choices, focus, keyboard paths and non-party host mode-transition motion retain their contracts.
The dim SHALL NOT be the only speaking cue: the name plate names the host and each actor exposes its
speaking data attribute. Actors remain decorative, with no focusable element; motion owns transitions.

#### Scenario: The host portrait comes from the art catalog
- **WHEN** a non-party host's dialogue panel names ref `"41"` and its catalog entry carries an image and face rectangle
- **THEN** the actor-right host renders that complete image bottom-aligned with contain fit and requests no other image source

#### Scenario: A pending or missing portrait shows the truthful placeholder
- **WHEN** the host's catalog entry is pending, and later a host named `葛里安‧衛登` has a null ref
- **THEN** the first actor shows its grounded silhouette, identity and pending state; the second shows initial `葛`, identity and missing state, with neither inventing an image

#### Scenario: The host speaks and the player is dimmed
- **WHEN** a conversation opens and its greeting commits
- **THEN** the host renders lit with `data-speaking="true"` and the player dimmed with `data-speaking="false"`; a companion host appears only in its raised existing slot

#### Scenario: The player is lit until the reply commits
- **WHEN** the player's scripted pick remains in flight until its reply revision is accepted
- **THEN** the player is lit and the host dim until that revision, then the host is lit and the player dim again

#### Scenario: A rejected choice returns the light to the host
- **WHEN** the player's freeform speech is rejected
- **THEN** rejection handling restores the host's light and the player's dim

#### Scenario: Nothing is dimmed outside dialogue
- **WHEN** mode is exploration and later combat with two active foes
- **THEN** the controlled figure is lit in both and both foes are lit in combat; companions retain their listener dim, and actor-right carries no exploration actor

#### Scenario: A companion host is not duplicated on the opposite anchor
- **WHEN** dialogue host identity joins to a committed party or controlled lineup figure
- **THEN** that identity has exactly one standing figure in actor-left, actor-right has no duplicate host, and the name plate, pagination and focus retain their existing behavior

### Requirement: Dialogue choices appear centred over the stage after the line is fully read
While the committed mode is `dialogue` and the committed `dialogue` panel is available, the client SHALL
present the conversation's choices as one choice list in the stage's `choices` anchor, and nowhere
else. The list SHALL render only while the message window reports that the current response's last
page is on screen, fully shown, with no pending action mark, and while no action the player dispatched
is in flight; at every other moment — a page still typing, a further page not yet read, a pick or
free-form speech awaiting its reply — it SHALL NOT be rendered. Its rows SHALL be, in order: one pick
row per `dialogue.choices` entry in payload order, each carrying the digit badge of its 1-based position
and its bounded label; a `⌨ 自由對話` row; a `↦ 移動…` row; and a `✕ 結束對話` row. It SHALL render no
row the panel does not back, no reason tag, and no disabled pick.

Activating a pick row SHALL dispatch `explore.talk_scripted` with `{npc_id: host.identity, keyword_id}`
through the single dispatch entry. Activating `⌨ 自由對話` SHALL expand the command line and focus its
field through the free-form borrow path, bound to the host, and SHALL dispatch nothing itself.
Activating `✕ 結束對話` SHALL dispatch `explore.dialogue_leave` with `{npc_id: host.identity}` and nothing
else. Activating `↦ 移動…` SHALL dispatch nothing and SHALL replace the rows with the exit rows of the
committed exploration scene overview, in its order, each carrying the exit's direction glyph and, while
enabled, the destination's display name under the scene overview's exit-chip rules, and ending with a
back row; activating an enabled exit row SHALL dispatch the same `explore.move` payload the overview's
exit chip dispatches, and a disabled exit row SHALL stay focusable with its server-authored reason and
dispatch nothing. Escape or the back row in the exit rows SHALL return to the choice rows with the
`↦ 移動…` row focused. A committed room without exits SHALL still show the back row alone.

The list SHALL be one keyboard composite and one tab stop: DOM focus SHALL rest on the list container,
which names its focused row through an active-descendant reference. ArrowUp and ArrowDown SHALL move to
the previous and next row, wrapping; Home and End SHALL move to the first and last row; Enter and Space
SHALL activate the focused row; while the choice rows are shown, digit `1`–`N` SHALL activate pick N
directly; a held key's auto-repeat SHALL NOT activate. While the list holds focus its active row SHALL be
shown by shape and fill — a leading `▸` and the dock's muted-gold fill — never by colour alone, and an
active disabled exit row SHALL keep a quiet treatment that promises no action. Every key the list handles SHALL be consumed by it and SHALL NOT reach the keyboard
router or the page surface; `/` and every key the list does not handle SHALL pass on unchanged. A pointer
activation of a row SHALL focus that row and activate it through the same path as Enter. When the list
appears while focus is on the message window, inside the message region, or on the document body, focus
SHALL move to the list with its first row focused. Before an activation dispatches, focus SHALL move to
the message window's page surface, so the list's removal never leaves focus on a removed element or the
document body. Every activation is suppressed while a mutation is in flight or awaiting its declared
presentation revision, exactly like a dock entry, and no combination of key and pointer input SHALL
emit more than one request per deliberate activation.

The list's rows derive from the committed `dialogue` and `exploration` panels alone and SHALL NOT depend
on any dock frame or router descriptor. Its presence SHALL be derived from the window's reader state and
the dispatch state, never from narrative prose.

#### Scenario: The choices wait for the last page
- **WHEN** a greeting of two pages commits with three choices at the `normal` text speed
- **THEN** no choice list is rendered while page 1 types, after it is fully shown, or while page 2 types, and the list renders in the `choices` anchor with focus on its first row once page 2 is fully shown

#### Scenario: The rows follow the committed panel
- **WHEN** the list renders for a panel with three choices
- **THEN** it shows pick rows badged `1`, `2`, `3` with the panel's labels in payload order, then `⌨ 自由對話`, `↦ 移動…`, and `✕ 結束對話`, and nothing else

#### Scenario: A pick dispatches the scripted keyword
- **WHEN** the player activates pick 2 through pointer, Enter, or the `2` key
- **THEN** exactly one `explore.talk_scripted` request with the committed host identity and that row's `keyword_id` is submitted, the list is removed while the request is in flight, focus is on the message window's page surface, and the list returns once the reply's last page is fully shown

#### Scenario: Free dialogue borrows the command line
- **WHEN** the player activates `⌨ 自由對話`
- **THEN** the command line expands with focus in its field for a freeform utterance to the host, and no action is dispatched

#### Scenario: The exit row ends the conversation
- **WHEN** the player activates `✕ 結束對話`
- **THEN** exactly one `explore.dialogue_leave` request with the committed host identity is submitted and no other action is dispatched

#### Scenario: Move swaps in the exits and Escape returns
- **WHEN** the room has two exits, one locked, and the player activates `↦ 移動…`, focuses the locked exit and presses Enter, then presses Escape
- **THEN** the list shows the two exit rows with their direction glyphs and the back row, the locked row shows its reason and nothing is submitted, and Escape returns to the choice rows with `↦ 移動…` focused

#### Scenario: A move from the list leaves the conversation
- **WHEN** the player activates `↦ 移動…` and then an enabled exit row
- **THEN** exactly one `explore.move` request with the overview exit chip's payload is submitted, the movement settlement clears the session through the existing seam, and the committed mode returns to `exploration` with the dock at the new room's overview

#### Scenario: The list is one tab stop and keeps its keys
- **WHEN** the list has focus and the player presses Tab, then Shift+Tab back, then ArrowDown twice and Enter
- **THEN** Tab leaves the list in one step, the list is reached again in one step, the arrows move the active-descendant reference, Enter activates the focused row once, and the keyboard router saw none of those arrow or Enter keys

#### Scenario: The choices never show beside unread text
- **WHEN** a reply's first page is on screen and further lines of the same response arrive
- **THEN** the list stays unrendered until the response's last page is fully shown

### Requirement: The motion level is a client-local preference that governs every client animation
The client SHALL have exactly three motion levels: `full`, `reduced`, and `off`. The settings surface
SHALL offer them as one `動態效果` control with the three buttons `完整`, `減少`, and `關閉`. The pressed
button SHALL be the effective level, marked by an indicator that does not rely on colour alone. Selecting
a button SHALL store that level. The effective level SHALL be the stored level when one is stored.
While no level is stored, it SHALL be `reduced` when the operating system requests reduced motion and
`full` otherwise, and it SHALL follow a change of the operating system's preference without a reload.
A stored value that is not one of the three levels SHALL be discarded, as if nothing were stored.

The effective level SHALL be applied to the whole document at once, the moment it changes, and every
client animation and transition SHALL read it through the client's motion tokens:
- **`full`** plays every animation and transition the client defines.
- **`reduced`** plays no translation, no shake, no flash, and no looping animation (pulses, blinking,
  spinners). The stage and mode transitions the client defines play only as opacity fades of at most
  150ms. Every other transition, drawers and control feedback included, is instant. Message pages
  appear in full at once.
- **`off`** makes every visual change instant, fades included.

Every animation and transition duration, delay, and travel distance SHALL come from the client's motion
tokens. No component SHALL declare a literal duration. The motion level SHALL never withhold
information: at every level each transition ends in the same rendered state, and every state it
conveys is also conveyed without motion.

#### Scenario: The operating system is followed while nothing is stored
- **WHEN** the client loads with no stored motion level and the operating system requests reduced
  motion, and the operating system's preference then changes to no preference
- **THEN** the effective level is `reduced` and the `減少` button is pressed, and after the change the
  effective level is `full` and the `完整` button is pressed, with no reload and nothing stored

#### Scenario: A stored level overrides the operating system
- **WHEN** the operating system requests reduced motion and the player selects `完整`, then reloads
- **THEN** the effective level is `full` before and after the reload, the stored wrapper carries
  `motionLevel: "full"`, and no `ui_action` is sent

#### Scenario: Reduced keeps short fades and drops travel and loops
- **WHEN** the effective level is `reduced`
- **THEN** every stage and mode transition duration resolves to at most 150ms, every travel distance
  resolves to zero, no looping animation runs, drawers and control feedback change instantly, and
  message pages appear in full at once

#### Scenario: Off makes every change instant
- **WHEN** the effective level is `off`
- **THEN** every animation and transition duration and delay resolves to zero, including fades, and
  every committed change renders in its final state in the same frame

#### Scenario: No component hard-codes a duration
- **WHEN** the client's component styles are scanned for animation and transition declarations
- **THEN** every duration and delay they declare is a motion token, and none is a literal time

#### Scenario: Every level ends in the same state
- **WHEN** the same committed change renders at `full`, at `reduced`, and at `off`
- **THEN** once any transition has finished, the three renders carry the same content, the same
  accessibility tree, and the same focus

### Requirement: Presentation timing never gates committed state or input
The client SHALL apply every committed change to its state and to the document immediately; motion
SHALL only decide how the view moves between two committed states. A transition SHALL NOT delay a
committed value, a mode or visibility attribute, the accessibility tree, or the tab order beyond the
moment the change commits, and SHALL NOT delay the player's ability to act beyond its own duration at
the current motion level. A transition interrupted by a newer committed change SHALL run toward the
newer state, and SHALL NOT first finish the older one.

Presentation that plays in steps — message pages, and a combat round's beats as `webclient-combat-menu`
"A combat round plays beat by beat" defines — SHALL follow three rules. Steps play in the order their
data committed, and a step never reorders, drops, or alters committed data. A player click or press that
advances the presentation shows the current step's end state at once; for a playing combat round it
shows the whole round's end state. A new player action shows every queued step's end state, a playing
combat round's included, before its own response starts. Nothing is lost: every stepped text stays in
the full log. Any pause a stepped presentation waits for SHALL come from the motion tokens, read by the
client's script from the same tokens the styles use, and SHALL resolve to zero at `off`; revealing text
follows the reader's text speed. The one presentation that holds the player's input is a playing combat
round: it keeps the command panel locked until it ends, and the player can end it at once with a click
or press on the message window or a typed command.

#### Scenario: A mode change commits before its transition ends
- **WHEN** the effective level is `full` and a committed revision changes the mode
- **THEN** the stage's mode attribute, the committed surfaces' accessibility state, and the store's
  view carry the new mode in the same frame as the commit, before any transition finishes

#### Scenario: Input is available within the transition's duration
- **WHEN** the effective level is `full` and the player opens a drawer or a new response starts
- **THEN** the drawer takes focus and the message window accepts Enter at once, without waiting for
  a transition to finish

#### Scenario: A combat round holds the panel only until the player ends it
- **WHEN** the effective level is `full`, a combat round is playing, and the player clicks the message
  window
- **THEN** the command panel accepts activation again as soon as the declared revision is also
  accepted, and every displayed value is the committed value

#### Scenario: A click shows the step's end state and a new action flushes
- **WHEN** a page is typing and the player clicks the message window, and later acts while unread
  pages remain
- **THEN** the click shows the page in full at once, and the action shows the previous response's
  last page complete before the new response's first page starts, with every page still in the full
  log

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

### Requirement: A leaving element is out of reach while it animates out
Every stage element that animates out — a crossfading image or portrait, a previous place-card heading,
the message window's clearing layer, the vitals island, and every later leaving element the client
animates — SHALL leave the accessibility tree, the tab order, and pointer hit-testing at the moment the
change that removes it commits, and SHALL stay out of reach until it is removed or re-enters. Focus SHALL
never move onto a leaving element. When focus is inside an element that is about to leave, the client
SHALL move focus to its current focus home before the element leaves, so focus never falls to the
document body. An element that is entering MAY receive focus from its first frame. An element that
re-enters while it is still leaving SHALL be in reach again from that moment.

#### Scenario: A leaving layer cannot be reached
- **WHEN** the effective level is `full` and a scene crossfade, a place-card change, or a message clear
  is in progress
- **THEN** each leaving copy is inert, is absent from the accessibility tree, and receives no click, and
  sequential focus navigation never lands in it

#### Scenario: Focus leaves the vitals island before it animates out
- **WHEN** focus is on a condition chip and a committed revision hides the vitals island
- **THEN** focus has moved to the focus home before the island becomes inert, and at no point during its
  exit is focus on the island or on the document body

#### Scenario: A re-shown island is in reach again at once
- **WHEN** the vitals island starts to leave and a committed revision shows it again before its exit
  finishes
- **THEN** the island is no longer inert from that revision on, and its condition chips are focusable

### Requirement: Mode changes transition at the motion level
The stage SHALL animate live mode changes, taking every duration, delay, and distance from the client's
motion tokens, so they follow the effective motion level of "The motion level is a client-local
preference that governs every client animation":
- **Exploration → dialogue:** the command region slides out to the right over the panel duration (250ms
  at `full`) while the message window spans the band from the commit's frame. The dialogue host's stage
  actor slides in from the right and fades in over the actor duration (350ms at `full`). The name plate
  fades in. The greeting pages and types as `webclient-input-narrative` defines.
- **Dialogue → exploration:** the reverse. The host's stage actor slides out to the right and fades, the
  name plate fades out, the message window returns to two thirds of the band in the commit's frame, and
  the command region slides back in.
- **Exploration → combat:** a white flash lasting the flash duration (120ms at `full`) plays once over
  the stage and under every island, the combat veil fades in, and the command region's content flips
  to the combat root.
- **Combat → exploration:** the veil fades out and the command region's content flips back. No flash
  plays.
- **Dialogue choices:** each row of the dialogue choice list fades in and rises into place, delayed by
  the stagger step (40ms at `full`) times its position, and the list's card fades in. Rows swapped in by
  `↦ 移動…` or by its return stagger the same way.

Only a live mode change animates: mounting the client, reconnecting, and a resync that commits the same
mode SHALL play none of these transitions. Every leaving element SHALL be out of reach as "A leaving
element is out of reach while it animates out" requires. No transition SHALL delay a committed value or
the player's input beyond its own duration: the choice list takes focus and handles keys and pointer from
its first frame, and the dock is focusable from the first frame of its return. A mode change SHALL NOT
scroll the stage or any element that contains it: a surface that slides past the stage's edge SHALL be
clipped without widening any ancestor's scrollable area, and no focus move during a mode change SHALL
scroll an ancestor toward its target, so the stage never shifts sideways. The flash, the veil, and
the flip SHALL be decorative, absent from the accessibility tree, and SHALL never intercept a pointer.
At `reduced`, the slides, the flip's rotation, and the rise SHALL NOT move anything, the fades SHALL last
at most 150ms, the flash SHALL NOT be visible, and the stagger SHALL be zero. At `off`, every mode change
SHALL render its final state in the commit's frame.

#### Scenario: Entering dialogue slides the panel out and the host in
- **WHEN** the effective level is `full` at 1920x1080 and the player opens a conversation
- **THEN** in the commit's frame the message region is the band's full width and the command region is
  inert, the command region's computed transition runs 250ms toward a translated, transparent state and
  ends `visibility: hidden`, the host's stage actor enters from the right with a 350ms fade, and the name
  plate fades in

#### Scenario: Leaving dialogue reverses the transition
- **WHEN** the effective level is `full` and the player activates `✕ 結束對話`
- **THEN** the host's stage actor leaves toward the right and is inert while it leaves, the message
  region returns to two thirds of the band in the commit's frame, the command region is in reach at
  once and slides back in, and focus is on the action dock

#### Scenario: No stage ancestor scrolls horizontally during a mode change
- **WHEN** the effective level is `full` and focus is on the action dock while the player enters and
  leaves dialogue, then enters and leaves combat
- **THEN** in every frame of every transition the stage, each element that contains it, and the
  document keep a horizontal scroll offset of zero and a scrollable width no larger than their visible
  width, and the dock takes focus on the return without moving the stage

#### Scenario: Entering combat flashes, fades the veil, and flips the panel
- **WHEN** the effective level is `full` and a committed revision changes the mode from exploration to
  combat
- **THEN** the flash layer plays one 120ms animation, the combat veil's opacity transitions from zero,
  the command region's content plays the flip toward the combat root, and none of them is in the
  accessibility tree or receives a click

#### Scenario: Leaving combat plays no flash
- **WHEN** the effective level is `full` and the mode changes from combat to exploration
- **THEN** the veil fades out and the command region's content flips back, and the flash layer plays
  no animation

#### Scenario: Choice rows stagger in without delaying input
- **WHEN** the effective level is `full` and the dialogue choice list appears with five rows
- **THEN** row N's entrance is delayed by 40ms × N, the list holds focus in its first frame, and a digit
  pressed before the last row has finished entering activates that row

#### Scenario: A reconnect replays nothing
- **WHEN** the client reconnects while the committed mode is combat or dialogue
- **THEN** no flash, flip, slide, or stagger plays, and every surface renders its final state

#### Scenario: Reduced keeps short fades and drops every movement
- **WHEN** the effective level is `reduced` and the player enters and leaves dialogue, then enters combat
- **THEN** the command region, the host, the name plate, the veil, and the choice rows only fade, each
  within 150ms, no slide, rotation, or rise moves anything, no flash is visible, and the rows appear
  together

#### Scenario: Off renders every mode change at once
- **WHEN** the effective level is `off` and the mode changes into and out of dialogue and combat
- **THEN** in the commit's frame each surface holds its final state: the command region hidden or
  shown, the host present or absent, the veil at its final opacity, the flash invisible, and every
  choice row fully shown

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

### Requirement: Held combat decoration never holds canonical scene identity
A terminal combat hold SHALL retain combat gradient, sample selection and veil only. It SHALL NOT freeze committed art identity or other canonical HUD state. Completion, skip, flush and epoch reset SHALL release decorative hold through the existing playback lifecycle.

#### Scenario: Terminal outcome changes scene
- **WHEN** a terminal round is playing while a newer committed art panel names another scene
- **THEN** the new scene follows the normal truthful image/pending rules beneath held combat decoration; the prior combat scene is not mislabelled current

#### Scenario: Playback is reset
- **WHEN** a held terminal round is skipped, flushed or reset on reconnect
- **THEN** combat decoration is released and no held foe/veil remains after the existing lifecycle clears it

### Requirement: Standing portraits retain contours and truthful grounded fallbacks
Standing portraits SHALL retain their supplied image contours and align their feet or silhouette base with the stage floor. Missing artwork SHALL use a standing silhouette with the subject name and truthful availability state, without inventing generation or a URL. Repeated visual image captions SHALL be suppressed only on the stage; accessible identity and state SHALL remain available.

#### Scenario: Unavailable portrait is not generating
- **WHEN** an actor has missing or failed art
- **THEN** a grounded silhouette states the subject and missing or failed state once, and no generating shimmer runs

#### Scenario: Pending motion respects preference
- **WHEN** pending art renders at full, reduced and off motion
- **THEN** only full motion animates the silhouette; the pending label remains readable at every level

#### Scenario: Compact stage preserves labels
- **WHEN** the player silhouette, vitals and command line render at 1280x720
- **THEN** the silhouette identity and state are not occluded by vitals or the command line and all HUD controls remain reachable

### Requirement: The bottom band separates material and focus without obscuring controls
The fixed bottom band SHALL provide a continuous ink-and-gold reading surface with a decorative stage seam and aligned message-control and shortcut rows. Page text, command rows and popovers SHALL never paint over these reserved controls. Only the active control SHALL carry the strongest focus treatment; the command field SHALL expose one clear focus frame.

#### Scenario: Popover text is isolated
- **WHEN** a verb popover opens over populated scene chips
- **THEN** no chip text shows through it, the target heading is stated once, and background chips cannot activate

#### Scenario: Dense command content is bounded
- **WHEN** a frame contains more rows than fit
- **THEN** its own row region scrolls while the legend and message controls remain visible on one baseline

#### Scenario: Motion is reduced
- **WHEN** the player changes command frames with reduced motion or off
- **THEN** reduced uses no 3D rotation or wipe and off commits immediately without losing focus

### Requirement: CJK reading furniture follows the measured prose column
Prose SHALL have readable CJK line and paragraph spacing while preserving exact narrative content, the contracted reference font size, sentence-safe paging and map alignment. Page text SHALL use a line height of 1.5 times its font size and SHALL separate consecutive narrative lines by a gap of about half a line. Any CJK spacing treatment SHALL be presentation only (the rendered text content is unchanged) and SHALL NOT apply to box-drawing map lines, whose whitespace and alignment stay exact. Page measurement SHALL match displayed typography, so no page line is clipped at any viewport or prose scale. The page marker SHALL end at the prose column's right edge, or as close to it as the control strip's own controls allow, and SHALL stay inside the control strip. The dialogue name plate's underline SHALL start at the name's left edge. The message window's reading rule SHALL show only while the page surface holds keyboard focus. Decorative motion SHALL stop at the reduced and off motion levels.

#### Scenario: Resize preserves complete narrative
- **WHEN** mixed CJK and Latin prose is paged, then the viewport or reader scale changes
- **THEN** all content remains reachable without clipped lines, and the marker stays within the reserved strip at the prose edge, clear of the `日誌` control

#### Scenario: Maps preserve whitespace
- **WHEN** a response contains an ASCII map between prose blocks
- **THEN** the map retains its indentation and alignment while prose receives spacing treatment

#### Scenario: The marker follows the dialogue column
- **WHEN** a dialogue page is fully shown at 1920x1080
- **THEN** the marker's right edge lies within a few pixels of the left-aligned prose column's right edge, far from the band's right end

#### Scenario: Reduced motion keeps the marker still
- **WHEN** the motion level is reduced or off while a page marker is shown
- **THEN** the marker neither bobs nor fades

### Requirement: Pointer-open dialogue choices expose a local initial highlight
When an eligible dialogue choice list first opens through pointer interaction, it SHALL expose a non-activating initial highlight on its first enabled choice using the same active-descendant state as keyboard navigation. The highlight SHALL be visible even while the list does not hold focus; showing it SHALL NOT itself move focus (where focus goes when the list appears is unchanged) and SHALL NOT dispatch. When the list swaps to its exits, the first enabled exit SHALL be active; when no exit is enabled, the first exit SHALL stay active with its explanation reachable.

#### Scenario: Opening does not answer
- **WHEN** a pointer action leads to a fully-read response with enabled choices
- **THEN** the first enabled choice is highlighted and no choice dispatch occurs until deliberate activation

#### Scenario: A disabled first exit is skipped
- **WHEN** the player opens `↦ 移動…` and the first exit is disabled while a later one is enabled
- **THEN** the first enabled exit is active and nothing is dispatched

### Requirement: Combat details follow the active command frame
The combat command window SHALL show detail for the currently highlighted root command, category, group or skill, never a stale previously selected skill. Root detail MAY be client-local explanatory copy of what the command opens or does, never a gameplay value; category and group detail SHALL name that row's committed label and descriptor count. Command rows SHALL scroll inside a bounded region above the persistent legend. The Skills count SHALL remain the exact committed descriptor count rendered as neutral secondary text.

#### Scenario: Category does not show an old attack
- **WHEN** the player backs out of a skill and highlights a category
- **THEN** the detail shows that category label/count and no stale attack target or cost

#### Scenario: Last row stays reachable
- **WHEN** the player navigates beyond the visible list
- **THEN** the focused row scrolls into view above the unchanged hint strip

### Requirement: Basic attack starts focused on an eligible opposing candidate
Opening basic attack SINGLE targeting SHALL initially focus the first enabled opposing candidate already supplied by the server, without changing candidate order or legal explicit selection. If none exists it SHALL use the first enabled candidate, or the existing disabled explanatory focus when none is enabled.

#### Scenario: An ally precedes a foe
- **WHEN** the server lists an ally before an enabled foe for basic attack
- **THEN** the foe initially has focus, the ally remains selectable if allowed, and no request is sent before confirmation

#### Scenario: Opening Attack sends nothing
- **WHEN** the player activates Attack once
- **THEN** the target frame opens focused on the first enabled foe and no `combat.cast` is emitted until the player confirms a target

#### Scenario: No eligible opposing candidate exists
- **WHEN** all opposing candidates are disabled or absent
- **THEN** focus falls back without constructing a candidate or dispatching

### Requirement: Playback lock is visible without inventing progress
While combat playback locks mutation controls, the command region SHALL communicate that it is waiting and expose the existing skip interaction clearly. A decorative activity line SHALL NOT imply a server completion percentage and SHALL be static at reduced/off.

#### Scenario: The cue appears only while playback locks the commands
- **WHEN** a combat round starts playing by itself at `full` motion, and later at `off`
- **THEN** the command region shows the waiting cue with a skip control while the round plays, and at `off`, where nothing locks, no cue appears

#### Scenario: Skip settles the lock
- **WHEN** the player skips a locked playing round
- **THEN** the cue clears with playback and the existing canonical command state becomes available

### Requirement: Reference surfaces share an opaque accessible frame
Reference drawers and full-screen overlays SHALL present one shared header: a decorative leading glyph,
the surface title, an optional subtitle, and one icon-only close control of at least 36x36px carrying an
accessible name, in the same order and position on every surface. The header SHALL be presentational
only: it SHALL emit a close request and own no focus trap, Escape handling, opener record, or
open-surface registration, all of which stay with the drawer or overlay host that renders it. The
header glyph SHALL come from the same glyph registry the top navigation draws its entries from, so a
surface opened from a navigation control shows that control's glyph, and every reference drawer and
every utility overlay SHALL declare one; no surface SHALL fall back to a generic placeholder glyph. A
surface whose body used to render its own title and close control SHALL render them only through the
shared header, so each surface carries exactly one title and one close control.

The body of every reference drawer and utility overlay SHALL be a fully opaque ink panel over a
stage-dimming scrim, so no stage, band, or command-line text shows through it; a backdrop blur MAY
decorate the scrim, but opacity SHALL NOT depend on `backdrop-filter` support. The recession and the
scrim SHALL dim only what lies behind the panel, never the panel itself. Existing modal focus, close,
and restore behavior SHALL remain unchanged, and the workspace bounds SHALL remain those of the
reference drawer and overlay requirements.

#### Scenario: Blur is unavailable
- **WHEN** a reference surface opens in a browser without backdrop-filter
- **THEN** stage text is still invisible through the opaque panel and body content remains readable

#### Scenario: One owner handles closing
- **WHEN** a gallery nested editor closes and then the gallery closes
- **THEN** each close is handled by its existing modal owner, focus returns to the correct opener and no duplicate header or focus trap is introduced

#### Scenario: Headers agree
- **WHEN** the same tool is opened from navigation
- **THEN** the header uses the matching glyph and has one named close control in the shared position

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

### Requirement: Client help and finite display vocabularies are localized

The client-owned help reference, the combat detail's skill target type and element, and the party
drawer's guidance SHALL read in Traditional Chinese rather than English prose or raw identifiers.
Literal key names (Enter, Esc, Tab, Space, Shift, PageUp, PageDown, Home, End, arrows, digits) and
literal command syntax (`help`) SHALL stay verbatim, rendered as key caps and code; protocol
identifiers, payloads and user-authored content SHALL NOT change.

The help reference SHALL group its rows by where the keys act (指令列, 指令面板, 閱讀與對話) and SHALL
name only bindings the client implements, including the ⌨ toggle and the dock's positional picks
1–9 (never a stale range). The help overlay's header subtitle SHALL describe its content (按鍵、指令列與閱讀操作),
never another surface's navigation.

A skill's `target_spec` SHALL be shown by the closed name set 無目標 / 自身 / 單一目標 / 範圍, and its
`element` by the element registry's own name followed by 屬性 (火屬性); an identifier outside either
set SHALL read 未知目標類型 or 未知屬性, never the raw key and never a guessed mechanic. The party
drawer's follow rules SHALL name affinity by the established term 羈絆.

#### Scenario: Help describes real keys
- **WHEN** the help overlay opens
- **THEN** it names only implemented bindings in localized prose, lists the ⌨ toggle and the 1–9
  positional picks, and preserves literal key and command syntax

#### Scenario: An unknown skill enum reads neutrally
- **WHEN** the combat detail pane shows a skill whose target type or element is outside the known sets
- **THEN** it reads 未知目標類型 or 未知屬性 and shows no raw identifier

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

### Requirement: Companion standing portraits line up behind the controlled character in the actor-left anchor
The `actor-left` anchor SHALL render the currently controlled character's standing portrait as the group's rightmost figure with highest baseline z, and SHALL render each companion in committed `party.slots` order to its left, forming an overlapping horizontal row. Each companion portrait SHALL resolve from `portrait_ref` through `art.portrait_catalog`, falling back to its display name's initial-letter placeholder when null or unresolved. Each figure SHALL reuse the existing StageActor rendering and remain non-interactive decorative art: no focusable element, no pointer events.

Every figure, including the controlled character, SHALL have the same full anchor size and ground line: no progressively smaller scale, lift ramp or depth dimming. Horizontal overlap SHALL compress as necessary to keep the row inside the stage's left half at 1920x1080, 1440x900 and 1280x720, preserving a scaled left gutter; a multi-figure group MAY shift horizontally within that half. In dialogue the group SHALL compress overlap to clear the choice list without resizing figures. Zero companions SHALL render the existing solo portrait at its standard anchor position. The anchor SHALL have `overflow: visible`; the vitals dock MAY cover the lowest strip of feet, never face or torso.

The lineup SHALL be visible in exploration, combat and dialogue, hidden in creation. Companions SHALL use the existing StageActor listener dim unless their committed dialogue host identity is the active host speaker in dialogue mode. That speaking companion SHALL temporarily receive z above every baseline figure, returning to its exact baseline z when speaking changes or ends, including across possession swaps and lineup count changes. Speaking focus SHALL change only dim and z, never position, lift or size, and SHALL remain correct at off/reduced motion. The controlled figure SHALL retain its existing speaking and beat behavior. No figure box SHALL cross the stage's horizontal centre; the foe lineup is unchanged.

#### Scenario: A two-companion party renders a three-figure group
- **WHEN** the committed `party` panel carries two resolved-portrait slots at 1920x1080 in exploration mode
- **THEN** three equally sized figures share a ground line, the player is rightmost with highest baseline z, the companions overlap leftward in party order, no box crosses the horizontal centre and no figure is focusable

#### Scenario: A zero-companion party renders only the player
- **WHEN** the committed `party` panel is available with an empty `slots` list
- **THEN** the `actor-left` anchor renders the player's solo portrait at the standard standing position, byte-stable with the solo layout before this change

#### Scenario: A companion with no portrait shows the initial letter
- **WHEN** a party slot carries `portrait_ref: null` for display name `蕾娜`
- **THEN** that figure renders the initial `蕾` through the stage actor's truthful placeholder, with no invented image or constructed URL

#### Scenario: The full party fits the left half at every viewport
- **WHEN** the committed party carries four slots and the shell renders at 1920x1080, 1440x900, and 1280x720
- **THEN** all five equally sized figures render with compressed horizontal overlap inside the left half; in exploration/combat each face is at least partially visible, and in dialogue a speaking companion is brought above the overlapping listeners without moving its slot

#### Scenario: A speaking companion rises temporarily without moving
- **WHEN** the committed dialogue host is a companion and the existing speaker signal changes from player to host and back
- **THEN** that companion changes from dim baseline z to lit highest z and back, preserving its exact geometry; possession swaps, lineup changes and off motion cannot retain stale speaking z

#### Scenario: The companion line and the foe line-up do not overlap
- **WHEN** the committed mode is combat with two companions and three active foes at 1280x720
- **THEN** no companion figure's rendered box intersects any foe figure's rendered box

### Requirement: Possession moves the possessed companion to the group's front
While the possession banner is available, the possessed companion SHALL occupy the rightmost slot and A SHALL occupy exactly that companion's former slot, without moving the remaining companions. Release SHALL restore both original positions. Join the committed bounded-string `status.actor.identity` (the controlled session actor, not the hybrid resource owner) to decimal-string-normalized integer party identities. Resolve only committed catalog references and the roster portrait. When no party row matches, the controlled front SHALL use a truthful null-art placeholder labelled by the committed banner's host name, never A's portrait or an invented catalog key.

#### Scenario: Possessing a companion moves it to the front
- **WHEN** the possession banner becomes available for the party's second companion 蕾娜 while the party has two slots
- **THEN** 蕾娜's figure renders frontmost, the player character's figure renders in the companion row, and the first companion keeps its behind position

#### Scenario: Release restores the player to the front
- **WHEN** the possession banner commits its unavailable form
- **THEN** the player character's figure returns to the front position and the released companion's figure returns to its companion-row position

#### Scenario: A possessed companion without a portrait still fronts
- **WHEN** the possession banner names a companion whose `portrait_ref` is null
- **THEN** the front figure renders the truthful initial-letter placeholder rather than the player's portrait
