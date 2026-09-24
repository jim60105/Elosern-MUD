## MODIFIED Requirements

### Requirement: The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces
The WebClient SHALL render as a full-bleed stage that fills the viewport, with the scene backdrop as
the lowest layer, the portrait anchors above it, the HUD islands above those, the bottom band above
those, and the command line topmost among the persistent surfaces. HUD surfaces SHALL be placed by
named stage anchors — the top-left `place` and `vitals` anchors, the top-right `map` anchor, the portrait anchors
`actor-left` and `actor-right`, the bottom band's two regions `band-message` and `band-command`, and
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
SHALL span the whole band. The band SHALL carry the reference's band chrome (the upward gradient,
the hairline top border, and the upward shadow) on the band itself, not on the content inside it.
The stage box — the region between the top band's lower edge and the bottom band's upper edge — is
where the scene is seen, and at the 1920x1080 reference viewport it SHALL be at least 65% of the
viewport's height — at least 702px of 1080; the 48px top band and the 300px bottom band leave 731px. Every surface other than the band SHALL be positioned relative to the
band-height token so that none of them overlaps the band.

The portrait anchors SHALL stand on the band: each SHALL be bottom-aligned to the band's upper edge,
SHALL be `min(62vh, 680px)` tall but never taller than the stage box, SHALL be inset 6% of the stage
width from its own side, and SHALL never cover the band. The `actor-left` anchor SHALL carry the
player's standing portrait — the current roster character's portrait, resolved exactly as the
stage portrait was before this requirement, with the truthful placeholder when no image exists —
in exploration, dialogue, and combat mode. The `actor-right` anchor SHALL carry no content. The
portrait anchors are non-interactive art: they SHALL carry no focusable element and SHALL NOT
intercept pointer events, and they MAY sit behind the HUD islands and the command-line row.

At 1920x1080, 1440x900, and 1280x720 no interactive stage anchor (`place`, `vitals`, `map`,
`band-message`, `band-command`, `command-line`) SHALL overlap another interactive anchor's content,
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
- **WHEN** the shell renders at 1920x1080 and the player moves through the exploration root, the interaction workspace, the waiting frame, an empty pane host, the deepest combat frame, and a dialogue exchange with four picks
- **THEN** the bottom band's rendered height is 300px (±1px) in every one of those states, and the message region's and the command region's boxes are unchanged between them

#### Scenario: The band splits two thirds and one third
- **WHEN** the shell renders in exploration mode at 1920x1080, 1440x900, and 1280x720
- **THEN** the message region spans the left two thirds of the band's width and the command region spans the remaining right third (each ±1px), both share the band's top and bottom edges, and in creation mode the command region spans the whole band

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

### Requirement: Surface visibility is gated by the committed game mode
The shell SHALL expose the committed mode on the stage root as `data-elosern-mode`, and surface
visibility SHALL be derived from that single attribute. A surface hidden for the current mode SHALL be
removed from rendering with `display:none` — never dimmed, never merely visually hidden — so it leaves
the accessibility tree and the tab order. The matrix SHALL be:

| Surface | exploration | combat | dialogue | creation |
|---|---|---|---|---|
| place card (location, world time) | visible | visible | visible | hidden |
| narrative caption (band message region) | visible | visible | visible (dialogue focus) | hidden |
| vitals island (vitals/conditions) | by the vitals rule | visible | by the vitals rule | hidden |
| minimap island | visible | **hidden** | visible | hidden |
| party quickbar island | while the party is non-empty | while the party is non-empty | while the party is non-empty | hidden |
| objective line (under the minimap) | visible | hidden | hidden | hidden |
| player standing portrait | visible | visible | visible | hidden |
| action dock (band command region) | visible | visible | visible (regular exploration form) | visible (creation form, full band width) |
| command line | visible | visible | visible | hidden |
| scene backdrop | visible (exploration stage) | visible (combat stage) | visible (unchanged art) | visible |

While the committed mode is `dialogue` the scene backdrop SHALL keep rendering its committed
exploration art truthfully — the reference's dialogue focus is carried by the dialogue box
itself, not by mutating the backdrop. Per-surface requirements that name their own visible-mode
sets SHALL stay consistent with this matrix. A cell that names a data rule instead of `visible` means
the surface is shown in that mode only while its own requirement's rule holds for the committed state,
and is otherwise hidden the same way (`display:none`, or not rendered at all where that requirement
says so). When a mode change, or a committed revision that turns a
surface's data rule false, hides the surface that currently holds focus, the shell SHALL move focus to
the action dock before the surface is removed, using the existing focus-restore path.

#### Scenario: The minimap disappears in combat
- **WHEN** the committed mode changes from exploration to combat
- **THEN** the minimap island is absent from the DOM layout and from the tab order, and it is not merely dimmed

#### Scenario: The minimap returns on leaving combat
- **WHEN** the committed mode changes from combat back to exploration
- **THEN** the minimap island renders again with the committed `local_map` payload

#### Scenario: Focus is rescued before its surface is hidden
- **WHEN** the focused element belongs to a surface that the incoming mode hides
- **THEN** focus is moved to the action dock before the surface is removed, and no focus is lost to the document body

#### Scenario: Creation mode presents only the creation surfaces
- **WHEN** the committed mode is creation
- **THEN** the place card, the narrative caption, the `vitals` and `map` anchors with every island in them, the player standing portrait, and the command line are absent, and the action dock renders the creation form across the whole bottom band

#### Scenario: Dialogue mode keeps the cockpit visible
- **WHEN** the committed mode changes from exploration to dialogue
- **THEN** the place card, narrative caption, minimap, player standing portrait, action dock, and command line all
  remain rendered, the objective line is hidden with `display:none` because only exploration shows it, the vitals and party islands keep following the same data rules as in
  exploration, the action dock keeps its regular exploration form
  with every ordinary root affordance present, and only the narrative presentation changes

#### Scenario: Dialogue backdrop keeps its committed art
- **WHEN** the committed mode is dialogue
- **THEN** the scene backdrop renders the same committed exploration art as before the mode
  change, unmodified

#### Scenario: The objective line shows only in exploration
- **WHEN** a non-empty committed `objectives` panel stays committed while the mode changes from exploration to combat, then to dialogue, then back to exploration
- **THEN** the objective line renders in exploration, is hidden with `display:none` in combat and in dialogue, and renders again on the return to exploration

### Requirement: The HUD island stack renders as bounded floating islands, not column cards
The surfaces placed in the stage's `vitals` and `map` anchors SHALL render as floating HUD
islands: a translucent panel fill, a backdrop blur, a hairline border, the shared corner radius, and
the shared drop shadow, each island a separate box separated by the anchor's gap — never a single
boxed column card and never an opaque `<aside>` stacked in a layout column. The `vitals` anchor,
under the place card, SHALL carry the vitals, the conditions, and the compact party quickbar as sibling
islands in that fixed order, each present only while its own requirement renders it, and SHALL carry
no character head card and no portrait catalog strip. The `map` anchor SHALL carry, in this order, the
minimap island, the objective line, the combat participant frame while it is mounted, and the title
ballot menu while it is mounted, each present only while its own requirement renders it; no reference
panel and no portrait anchor content SHALL be placed in either island anchor. The stack's rendered height SHALL fit within its anchor at both 1440x900 and 1280x720 with
every island populated, so no required island depends on scrolling the anchor to be seen. Every
island's chrome SHALL be expressed through the shared design tokens, so a token change or the
reduced-motion block reaches all of them at once.

#### Scenario: The left anchor renders separate islands
- **WHEN** the shell renders in exploration mode with a vital below its maximum, a committed `harmful` condition, and a non-empty party
- **THEN** the vitals, the conditions, and the party quickbar render as three separately-chromed islands in that order, each with the translucent blurred panel chrome, none of them is a single opaque column card, and no head card or portrait catalog strip is rendered

#### Scenario: The populated stack fits its anchor at the minimum viewport
- **WHEN** the shell renders at 1280x720 with every island populated and the condition overflow disclosed
- **THEN** each island anchor's stack fits inside its anchor, the `vitals` stack does not intersect the place card, and neither stack intersects the bottom band, the command line, or the other island anchor's content

#### Scenario: Island chrome comes from the shared tokens
- **WHEN** an island renders
- **THEN** its fill, border, radius, shadow, and transitions resolve from the shared design tokens rather than from per-component literals

#### Scenario: The map anchor stacks its islands in order
- **WHEN** the shell renders in exploration mode with a committed `local_map` panel, a non-empty `objectives` panel, and title-ballot candidates, and later in combat mode
- **THEN** exploration renders the minimap island, the objective line, and the title ballot menu in that order in the `map` anchor, and combat renders the participant frame there with no minimap and no objective line

### Requirement: The minimap island states only its own drawing convention
The minimap SHALL render as a bounded HUD island at the top of the stage's `map` anchor, directly
below the top band and above the objective line, carrying the committed `local_map` payload's title. Where the resolved layout variant is the
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
or a movement destination: the place name belongs to the stage's place card, and a
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

### Requirement: The party quickbar island presents the committed party only
The `vitals` anchor SHALL carry a compact party island, beneath the vitals and conditions islands, while
the committed `party` panel is available with at least one slot in exploration, combat, or dialogue
mode, and SHALL render no party island — no header, no count, and no cell — when the panel is
unavailable, when its `slots` list is empty, or when the committed mode is creation. The island's
header SHALL read `同伴` with the slot count as `N / 4`, where `N` equals the committed slot count. Each
row of `party.slots` SHALL render one compact cell, in payload order and in one row, carrying: an avatar
showing the bound portrait only when the row's `portrait_ref` resolves through the client's art
catalog, otherwise the display name's initial letter in the reference's gold display face; beneath it
an HP hairline bar whose fill ratio is `hp_current / hp_maximum`; and an accessible name, also exposed
as the cell's tooltip, stating the display name, the HP numerals, and the row's bond stage name. When
the committed combat panel's participant rows carry a row with the same `identity`, the cell SHALL
additionally show that participant's session token (e.g. `a2`) as a visible badge on the avatar; a
companion not fighting SHALL show no token. The island SHALL render no invite cell and no padding for
missing companions: inviting and the 空位 row live in the 同伴 · 隊伍 drawer, where every row's name,
numerals, and bond stage are also visible text. Activating the island or any cell SHALL open the
同伴 · 隊伍 drawer and SHALL NOT dispatch any action. The island SHALL present no affinity numeral, no
companion trait the panel does not carry, and no estimate.

Because the island is absent for an empty party, the character-status drawer SHALL carry one
labelled `同伴 · 隊伍` control, rendered while the committed `party` panel is available, that opens
the 同伴 · 隊伍 drawer and dispatches nothing, so that drawer stays reachable at every party size.

#### Scenario: The quickbar mirrors the committed party
- **WHEN** a snapshot commits two party slots with HP 180/220 and 144/160 and bond stages 親睦
  and 信賴
- **THEN** the island reads `同伴 2 / 4` and renders exactly two compact cells with their HP hairline
  bars, each cell's accessible name and tooltip state its display name, `180/220` or `144/160`, and
  `親睦` or `信賴`, no invite cell is rendered, and no numeric affinity appears

#### Scenario: The combat token is joined by identity
- **WHEN** the committed combat panel carries a participant row whose `identity` equals a party
  slot's `identity` with token `a2`
- **THEN** that companion's cell shows the `a2` badge on its avatar, and a party row with no matching
  participant shows no token

#### Scenario: No portrait falls back to the initial letter
- **WHEN** a party row carries `portrait_ref: null` for display name `蕾娜`
- **THEN** the avatar renders the gold initial `蕾`, not an invented image

#### Scenario: An unavailable party panel hides the island
- **WHEN** the committed `party` panel switches to the unavailable form
- **THEN** no party island is rendered anywhere in the HUD (not an emptied or dimmed island)

#### Scenario: The quickbar opens the drawer without mutating
- **WHEN** the player activates a party cell
- **THEN** the 同伴 · 隊伍 drawer opens and no `ui_action` or text command is sent

#### Scenario: An empty party renders no island
- **WHEN** the committed `party` panel is available with an empty `slots` list in exploration mode
- **THEN** no party island, header, count, or invite cell is rendered anywhere in the HUD, and nothing in the `vitals` anchor is focusable on its behalf

#### Scenario: The party drawer stays reachable with an empty party
- **WHEN** the committed party is empty and the player opens the character-status drawer and activates its `同伴 · 隊伍` control
- **THEN** the 同伴 · 隊伍 drawer opens with its 空位 row and follow rules, and no `ui_action` or text command is sent

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

### Requirement: The combat participant frame presents the session's participants and their portraits
In combat the shell SHALL render a participant frame as a HUD island in the stage's top-right `map`
anchor, where the minimap is hidden in combat, and SHALL NOT place it in either portrait anchor, grouped into the
player's side and the opposing side using the committed participants' server-authored team values, in
the presenter's order. Each participant SHALL render its session token, its display name, its current
and maximum hit points as numerals, and its state; a non-active state SHALL be conveyed by an explicit
text marker in addition to any colour. The frame SHALL NOT invent a field the participant descriptor
does not carry.

Each participant's portrait SHALL be resolved only by looking its server-authored portrait reference
up in the committed art panel's portrait catalog: a resolvable entry SHALL render that entry, an
entry that resolves to a placeholder SHALL render the placeholder card, and a null reference or an
unavailable art panel SHALL render no portrait at all. The client SHALL NOT construct a portrait
subject key or URL. While the participant frame is mounted it SHALL be the sole presenter of the
portrait catalog, so no separate portrait strip is rendered alongside it.

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
- **THEN** it is not reachable by sequential keyboard navigation, the dock's active row container remains the surface's only listbox, and no portrait strip is rendered outside the frame

#### Scenario: The frame sits in the map anchor, not on a portrait anchor
- **WHEN** a combat session commits participants at 1440x900 and 1280x720
- **THEN** the participant frame is a descendant of the `map` anchor, the `actor-right` anchor holds no participant content, and the frame's visible box intersects neither the bottom band nor the command line

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
