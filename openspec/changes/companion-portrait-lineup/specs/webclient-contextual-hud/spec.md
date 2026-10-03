## REMOVED Requirements

### Requirement: The party quickbar island presents the committed party only
**Reason**: The party quickbar island is deleted from the stage. Companions are represented by standing portraits in the `actor-left` anchor ("Companion standing portraits line up behind the controlled character in the actor-left anchor"), and the full companion view stays reachable through the 同伴 ‧ 隊伍 drawer's existing control. The drawer requirement "The party drawer presents compbig rows and the fixed follow rules" is unchanged.
**Migration**: None. No users exist; the quickbar's information (HP hairline, bond stage) lives on in the party drawer, and the standing portraits carry presence rather than numerals.

## ADDED Requirements

### Requirement: Companion standing portraits line up behind the controlled character in the actor-left anchor
The `actor-left` anchor SHALL render the currently controlled character's standing portrait as the group's frontmost (rightmost) figure, and SHALL render each companion in the committed `party.slots` order as a standing portrait behind it (to its left), forming a depth-staged row that grows leftward from the anchor's natural standing position. Each companion portrait SHALL be resolved from `party.slots[].portrait_ref` through the art panel's `portrait_catalog`, falling back to the display name's initial-letter placeholder — the same truthful fallback the existing stage actor uses — when the reference is null or names no catalog entry. Each figure SHALL follow "Stage actors present the player and the dialogue host with a speaking state" for its rendering and SHALL be non-interactive decorative art: no focusable element, no pointer events.

The depth staging SHALL mirror the foe line-up's pattern: each figure behind the front one SHALL be progressively smaller, shifted leftward with a fixed exposed fraction, and lifted slightly to suggest depth. The group SHALL right-align to the anchor's standard standing position so the controlled character occupies the position the player's solo portrait occupies today, and the row SHALL stay within the stage's left half: when the group count grows, the overlap SHALL compress so every figure remains at least partially visible at 1920x1080, 1440x900, and 1280x720. A zero-companion party SHALL render only the controlled character's solo portrait, identical to the solo layout. The `actor-left` anchor SHALL carry `overflow: visible` so the row may extend beyond the anchor's own box, and the vitals dock MAY overlap the lowest strip of every figure's feet.

The lineup SHALL be visible in exploration, combat, and dialogue mode and hidden in creation mode, following the portrait anchor's mode-visibility contract; in dialogue the figures dim as listeners exactly as the player's portrait does. No figure's rendered box SHALL cross the stage's horizontal centre, so the companion line and the foe line-up never intersect.

#### Scenario: A two-companion party renders a three-figure group
- **WHEN** the committed `party` panel carries two resolved-portrait slots at 1920x1080 in exploration mode
- **THEN** the `actor-left` anchor renders three figures — the player's portrait frontmost at the group's right, two companion portraits behind it going left, each progressively smaller with a slight upward lift — no figure crosses the stage's horizontal centre, and no figure carries a focusable element

#### Scenario: A zero-companion party renders only the player
- **WHEN** the committed `party` panel is available with an empty `slots` list
- **THEN** the `actor-left` anchor renders the player's solo portrait at the standard standing position, byte-stable with the solo layout before this change

#### Scenario: A companion with no portrait shows the initial letter
- **WHEN** a party slot carries `portrait_ref: null` for display name `蕾娜`
- **THEN** that figure renders the initial `蕾` through the stage actor's truthful placeholder, with no invented image or constructed URL

#### Scenario: The full party fits the left half at every viewport
- **WHEN** the committed party carries four slots and the shell renders at 1920x1080, 1440x900, and 1280x720
- **THEN** all five figures render with compressed overlap, every figure stays within the stage's left half, and each figure's face region is at least partially visible

#### Scenario: The companion line and the foe line-up do not overlap
- **WHEN** the committed mode is combat with two companions and three active foes at 1280x720
- **THEN** no companion figure's rendered box intersects any foe figure's rendered box

### Requirement: Possession moves the possessed companion to the group's front
While the possession banner is available, the possessed companion SHALL stand at the group's front (rightmost position), rendered from that companion's party slot portrait, and the player character SHALL move into the companion row at the position the possessed companion formerly held, rendered as a companion figure. The remaining companions SHALL keep their party-order positions. On release the player character SHALL return to the front and the released companion to its companion position. The swap SHALL follow the committed state through the established epoch transition, with no interpolated guess: the front figure SHALL be resolved by joining the committed `status` panel's `actor.identity` to the committed `party.slots[].identity` — while possessing, the session actor is the possessed NPC, whose identity appears among the owner-keyed party slots the party panel keeps listing — and the figures come from the committed `party.slots`, the committed roster portrait, and the committed possession banner alone. When the join finds no slot — a party the client has not yet learned or a companion dismissed at the same commit — the front SHALL be the stage actor the portrait resolution already yields from the committed actor, and no invented portrait SHALL stand in.

#### Scenario: Possessing a companion moves it to the front
- **WHEN** the possession banner becomes available for the party's second companion 蕾娜 while the party has two slots
- **THEN** 蕾娜's figure renders frontmost, the player character's figure renders in the companion row, and the first companion keeps its behind position

#### Scenario: Release restores the player to the front
- **WHEN** the possession banner commits its unavailable form
- **THEN** the player character's figure returns to the front position and the released companion's figure returns to its companion-row position

#### Scenario: A possessed companion without a portrait still fronts
- **WHEN** the possession banner names a companion whose `portrait_ref` is null
- **THEN** the front figure renders the truthful initial-letter placeholder rather than the player's portrait

## MODIFIED Requirements

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
actor while the committed mode is `dialogue` and the committed `dialogue` panel is available, SHALL carry
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
- **WHEN** the committed mode changes from exploration to dialogue at 1920x1080 with an available `dialogue` panel
- **THEN** the `actor-right` anchor renders the host's stage actor, its bottom edge coincides with the band's top edge, its right edge is 6% of the stage width from the stage's right edge, its height equals the player portrait's height, it holds no focusable element, and on the return to exploration `actor-right` renders no content again

#### Scenario: The host's face clears the minimap at the smaller viewports
- **WHEN** the committed mode is dialogue with a committed `local_map` panel at 1440x900 and at 1280x720
- **THEN** the `actor-right` anchor's right inset is at least 6% of the stage width, its horizontal centre lies left of the leftmost edge of the right-hand island column — the place card and the minimap card, which share that column's width — and no interactive stage anchor overlaps another

#### Scenario: The choice list sits over the stage between the portraits
- **WHEN** the dialogue choice list renders four picks and its three trailing rows at 1920x1080, 1440x900, and 1280x720 with the minimap island present and the command line expanded
- **THEN** the `choices` anchor and the list are horizontally centred on the stage box (±1px), lie entirely inside the stage box above the command-line row, intersect no `vitals`, `map`, band, or command-line anchor, and every row is reachable

### Requirement: Surface visibility is gated by the committed game mode
This requirement carries the `place-card-relocation` amendment; the party-quickbar row is removed and the portrait row names the companion line.
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
follows the committed mode at the commit. The matrix SHALL be:

| Surface | exploration | combat | dialogue | creation |
|---|---|---|---|---|
| place card (location, world time; `map` anchor, above the minimap) | visible | visible | visible | hidden |
| message window (band message region) | visible | visible | visible (whole band width, paged, name plate) | hidden |
| dialogue choice list (`choices` anchor, centred over the stage) | not rendered | not rendered | once the current response's last page is fully shown, while no action is in flight | not rendered |
| vitals dock (condition icons + vitals bars; `vitals` anchor, lower-left) | by the vitals rule | visible | by the vitals rule | hidden |
| minimap island | visible | **hidden** | visible | hidden |
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
The place card's visibility SHALL follow this matrix exactly as it did while it stood in the left
column: it is shown in every playing mode and hidden in creation, and moving it into the `map` anchor
SHALL NOT make it inherit the minimap's combat hiding — in combat the card stays visible above the
participant frame.
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
- **THEN** the place card, message window, minimap, the player's front figure, the companion standing portraits, command-line toggle, and log control all
  remain rendered, the dialogue host's standing portrait is rendered in `actor-right`, the command line keeps its expanded or collapsed state, the objective line is hidden with `display:none` because only exploration shows it, the vitals island keeps following the same data rule as in
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
