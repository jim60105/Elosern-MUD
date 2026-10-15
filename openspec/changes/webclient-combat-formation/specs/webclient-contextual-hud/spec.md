## ADDED Requirements

### Requirement: Combat figures stand in a shared-scale formation
While the committed mode is `combat`, or while a round that ended the fight still plays, the stage SHALL place the controlled figure, every drawn companion and every active foe (up to 16 minus the party count, in presenter order) at the boxes that "Combat formation geometry is one pure shared-scale function" returns for the live stage geometry. Every figure on both sides SHALL be drawn at the same scale at every moment, and exploration and dialogue SHALL keep their existing standing positions.

#### Scenario: Every active foe stands
- **WHEN** a combat snapshot commits one, three, five, eight and fifteen active foes with a solo player at 1451x790
- **THEN** exactly that many foe stage actors render, in presenter order, at the formation's boxes (±1px), and no foe is left to another surface

#### Scenario: Both sides are drawn at one scale
- **WHEN** combat renders at 1451x790 and at 1600x900 for parties of one, three and five figures against one, four, eight and the maximum (16 minus the party count) foes, and again while a foe joins, while one leaves, and during the entry into combat
- **THEN** every rendered figure box on both sides has the same height (±1px) as every other in the same frame, sampled at the start, the middle and the end of each transition

#### Scenario: The dead-centre gap stays clear
- **WHEN** combat renders any of those cases, including at the farthest point of every beat gesture
- **THEN** no figure box intersects the band from `stage centre − 132px × S` to `stage centre + 132px × S` (the card's columns) at any moment, and none intersects the band from `stage centre − 148px × S` to `stage centre + 148px × S` at rest

#### Scenario: The party forms up only in combat
- **WHEN** the committed mode changes exploration → combat → exploration with a five-figure party, and exploration → dialogue
- **THEN** in combat the party stands at the formation's boxes; on the return to exploration, and in dialogue, every party figure stands where the exploration line-up places it today (±1px)

#### Scenario: Entering and leaving combat moves figures with the motion level
- **WHEN** the mode live-changes into and out of combat at `full`, at `reduced`, and at `off`, and when the client reloads or reconnects in combat
- **THEN** at `full` each party figure glides and scales from its exploration box to its formation box (and back) over the actor duration times the travel factor, with the foes entering as the flash releases at the formation scale; at `reduced` the figures take their final boxes in the commit's frame and only fade where they enter or leave; at `off`, and on a reload or reconnect, every figure renders at its final box in the commit's frame

#### Scenario: A changing roster re-forms the line together
- **WHEN** a foe joins or flees during combat so that the shared scale or the rank count changes
- **THEN** every figure on both sides glides to its new box and scale with the same duration and easing in the same frames (instant below `full`), and the leaving foe fades where it stands

#### Scenario: Resizing keeps the formation and its pointer targets live
- **WHEN** the viewport is resized from 1451x790 to 1600x900 and back while combat is shown
- **THEN** the formation is recomputed from the new stage geometry within one frame of the resize, every figure box, plate and pointer target matches the new formation, and a pointer action on a figure's target or a plate works at once after the resize

#### Scenario: The formation is decorative art
- **WHEN** the formation renders
- **THEN** its figures are hidden from assistive technology, carry no focusable element, and intercept no pointer events outside the interactions other requirements define

### Requirement: Combat figures carry glance plates
While the formation is shown, each drawn combat figure other than the controlled figure SHALL carry one plate in its formation plate slot, in the stage's `plates` layer, showing at a glance the participant's name, a thin hit-point stroke and a tabular hit-point readout, with a third line reserved for condition glyphs; the controlled figure's vitals stay in the vitals dock. A plate SHALL NOT overlap another plate, the command card, the vitals dock or the top band.

#### Scenario: A full plate reads name, stroke and numbers
- **WHEN** a companion at 42 of 120 hit points and a foe at 18 of 30 stand in a formation with `full` plate slots
- **THEN** each 112px × S by 52px × S plate shows on its first line the display name in the serif small text (ellipsized within the plate, the full name kept in the DOM and in its accessible name), on its second line a 4px × S tapered stroke filled to the current fraction followed by the readout `42` / `120` and `18` / `30` with the current value bright and `/ maximum` receding in tabular figures, and keeps its third line empty for condition glyphs

#### Scenario: A compact plate keeps the stroke and the number
- **WHEN** the formation returns `compact` plate slots
- **THEN** each 72px × S by 36px × S plate hides the name visually (the name stays its accessible name), shows on its first line the stroke (at least 30px × S long) and the current hit points, and keeps its second line for a condition glyph

#### Scenario: Plates never collide
- **WHEN** combat renders for every party count 1–5 against foe counts 1, 3, 7, 8 and 16 minus the party count at 1451x790 and 1600x900
- **THEN** every plate lies inside its slot (±1px), no two plates intersect, and no plate intersects the command card's column, the vitals dock or the top band

#### Scenario: Plates follow playback
- **WHEN** a combat round plays damage beats on a foe and on a companion
- **THEN** each plate's stroke and readout show the displayed value the beat publishes (`displayHp`) and settle to the committed value when the round ends, so the plate never shows a later value than the beat's page

#### Scenario: The plates layer is outside the portrait anchors
- **WHEN** the formation renders
- **THEN** the plates render in the stage's `plates` layer above the portrait anchors and below the HUD islands, the band and the command card, the layer holds only the plates, carries no focusable element in this requirement, and outside combat renders nothing

#### Scenario: Repeated names carry their session token
- **WHEN** three foes share the display name 哥布林 and a fourth is named 狼
- **THEN** each 哥布林 plate shows its session token after the name (`哥布林 e1`, `哥布林 e2`, `哥布林 e3`) and the 狼 plate shows no token; a token is shown only while two drawn participants share a name

## MODIFIED Requirements

### Requirement: The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces
The WebClient SHALL render as a full-bleed stage filling the viewport, layered bottom-up: the scene backdrop, the portrait anchors, the HUD islands, the bottom band, and the command line topmost among the persistent surfaces. HUD surfaces SHALL be placed by named stage anchors — `vitals`, `map`, `actor-left`, `actor-right`, `band-message`, `band-command`, `choices`, `presence`, `plates`, and `command-line` — and SHALL NOT sit inside a page-scrolling container that can push a required surface out of view.

#### Scenario: The requirement carries its amendments
- **WHEN** the `place-card-relocation` and `vitals-bar-redesign` amendments apply to this requirement
- **THEN** the party-line wording below replaces the solo-portrait wording of the `actor-left` anchor

#### Scenario: Fixed chrome dimensions are reference dimensions
- **WHEN** the shell renders at viewports above 790px tall or 1451px wide, the 1451x790 reference viewport
- **THEN** the fixed CSS-pixel chrome dimensions in this requirement are reference dimensions at viewports up to 790px tall or 1451px wide, above both chrome dimensions scale once under the desktop proportional-scaling contract, viewport-relative band/prose/portrait dimensions are not multiplied again, and the named acceptance-size non-overlap rules remain

#### Scenario: The stage fills the viewport with layered surfaces
- **WHEN** the shell mounts at 1451x790
- **THEN** the scene backdrop fills the stage box, and the player portrait, the HUD islands, the bottom band, and the command line are layered above it in that order with no page-level scrollbar

#### Scenario: Required surfaces never scroll out of view
- **WHEN** the HUD islands hold more content than their anchor's height, or the dock frame or the narrative holds more content than its band region
- **THEN** the island stack or the band region itself is bounded and scrolls internally, and no required surface is pushed below the visible viewport

#### Scenario: Anchors do not overlap at the minimum viewport
- **WHEN** the shell renders at the 1451x790 reference viewport with every mode-visible surface present
- **THEN** no interactive stage anchor's rendered box intersects another interactive anchor's rendered box

#### Scenario: The top band's own elements do not collide
- **WHEN** the shell renders at the 1451x790 reference viewport with every top-band element present and a maximum-length character name committed
- **THEN** the band's elements render side by side without intersecting, the variable-width element is truncated within its bound, and no band element's box extends into the island anchor region

#### Scenario: A band popover overlays without displacing
- **WHEN** a transient popover is opened from a top-band element
- **THEN** the band's rendered box is unchanged, the popover renders above the island anchors, and Escape or outside activation closes it

#### Scenario: The bottom band keeps one height whatever it holds
- **WHEN** the shell renders at 1451x790 and the player moves through the exploration root (the compass, the 建議 pill, and the readout), a person's verb card, the wait card, an empty pane host, the deepest combat frame, and a dialogue exchange with four picks
- **THEN** the bottom band's rendered height is 220px (±1px) in every one of those states, the message region's and the command region's boxes are unchanged between the exploration and combat states, and in the dialogue state the message region spans the band's whole width at the same height

#### Scenario: The band splits two thirds and one third
- **WHEN** the shell renders in exploration mode at 1451x790 and at 2560x1440
- **THEN** the message region spans the left two thirds of the band's width and the command region spans the remaining right third (each ±1px), both share the band's top and bottom edges, in creation mode the command region spans the whole band, and in dialogue mode the message region spans the whole band while the command region is not rendered

#### Scenario: The player portrait stands on the band
- **WHEN** the shell renders in exploration mode at 1451x790 with a committed roster portrait for the current character
- **THEN** the `actor-left` anchor renders that portrait frontmost, its bottom edge coincides with the band's top edge, its height is `min(62vh, 680px)` (±1px) — its left-edge inset is the value its anchor rule derives, never below 6% of the stage width, it holds no focusable element, and the `actor-right` anchor renders no content

#### Scenario: The portrait never outgrows the stage box
- **WHEN** the shell renders in a window short enough that `min(62vh, 680px)` exceeds the stage box's height
- **THEN** the player portrait's height equals the stage box's height and its top edge is not above the top band's lower edge

#### Scenario: The stage box is at least 65% of the reference viewport
- **WHEN** the shell renders in exploration mode at 1451x790
- **THEN** the top band is 48px tall, the bottom band is 220px tall (each ±1px), and the stage box between them is at least 513.5px tall (65% of 790)

#### Scenario: The top band carries no location or time
- **WHEN** the shell renders in exploration mode with a committed location label and world time
- **THEN** the top band's rendered height is 48px, no element inside the top band states the location label or the world time, and the place card in the `map` anchor below the top band states both

#### Scenario: The left column carries no place card
- **WHEN** the shell renders in exploration mode with a committed location and world time
- **THEN** no place card renders anywhere in the stage's left column, and the `vitals` anchor's box is not offset by any place card's height

#### Scenario: The dialogue host stands opposite the player
- **WHEN** the committed mode changes from exploration to dialogue at 1451x790 with an available `dialogue` panel whose host is not already in the party lineup
- **THEN** the `actor-right` anchor renders the host's stage actor, its bottom edge coincides with the band's top edge, its right edge is inset by its anchor rule's clearance value (never below 6% of the stage width), its height equals the player portrait's height, it holds no focusable element, and on the return to exploration `actor-right` renders no content again

#### Scenario: The host's face clears the minimap at the smaller viewports
- **WHEN** the committed mode is dialogue with a committed `local_map` panel at 1451x790 and at 2560x1440
- **THEN** the `actor-right` anchor's right inset is at least 6% of the stage width, its horizontal centre lies left of the leftmost edge of the right-hand island column — the place card and the minimap card, which share that column's width — and no interactive stage anchor overlaps another

#### Scenario: The choice list sits over the stage between the portraits
- **WHEN** the dialogue choice list renders four picks and its three trailing rows at 1451x790 and at 2560x1440 with the minimap island present and the command line expanded
- **THEN** the `choices` anchor and the list are horizontally centred on the stage box (±1px), lie entirely inside the stage box above the command-line row, intersect no `vitals`, `map`, band, or command-line anchor, and every row is reachable

#### Scenario: The top band carries only the navigation chrome
- **WHEN** the shell renders with the possession banner present, a character switcher, a connection state, a committed location label, and world time
- **THEN** the top band is 48px tall at every supported viewport and carries only the brand, the top navigation bar, the possession banner when present, the character switcher, and the connection state, and it carries no location label and no time label

#### Scenario: The vitals and map anchors stand at their stage gutters
- **WHEN** the shell renders in exploration mode with every island present
- **THEN** the `vitals` anchor is the stage's lower-left vitals dock that "The vitals dock stands at the stage's lower-left above the band" defines — bottom-anchored on the band's upper edge in the left gutter, at the left column's fixed width that does not depend on the content it holds — and the `map` anchor sits at the stage box's top-right corner below the top band, its content column (the place card, then the minimap island, then the objective line, then any other island this capability places there) right-aligned to the stage's right gutter and bounded above the bottom band

#### Scenario: The band's height comes from one shared token
- **WHEN** the shell renders at 1451x790 and at 2560x1440
- **THEN** the bottom band spans the full stage width along the stage's bottom edge at one fixed height, `clamp(190px, 27.85vh, 400px)` with its two px bounds multiplied once by the desktop chrome factor (220px at the 1451x790 reference viewport, 401px at 2560x1440), taken from a single shared band-height token, and the band carries the reference's band chrome (the upward gradient, the hairline top border, and the upward shadow) on the band itself, not on the content inside it

#### Scenario: Nothing grows or shrinks the band
- **WHEN** frames, panes, line counts, dialogue exchanges, and mode changes come and go
- **THEN** the band's height depends on none of its content, the dock frame, the committed mode, or any measurement, and none of them grows or shrinks it

#### Scenario: The band splits message and command regions per mode
- **WHEN** the shell renders in exploration mode, in creation mode, and in dialogue mode
- **THEN** the band is divided into the message region `band-message`, covering the left two thirds of the band's width, and the command region `band-command`, covering the remaining right third; in creation mode, where the message region is hidden, the command region spans the whole band, and in dialogue mode, where the command region is collapsed, the message region spans the whole band

#### Scenario: Every surface avoids the band through the band-height token
- **WHEN** the shell renders in exploration mode at the 1451x790 reference viewport
- **THEN** the stage box — the region between the top band's lower edge and the bottom band's upper edge, where the scene is seen — is at least 65% of the viewport's height (at least 513.5px of 790; the 48px top band and the 220px bottom band leave 522px), and every surface other than the band is positioned relative to the band-height token so that none of them overlaps the band

#### Scenario: The portrait anchors stand on the band and clear the island columns
- **WHEN** the shell renders with the vitals stack on the left and the place card and minimap card on the right
- **THEN** each portrait anchor is bottom-aligned to the band's upper edge, `min(62vh, 680px)` tall but never taller than the stage box, inset at least 6% of the stage width from its own side, and never covering the band; where 6% would place the figure's face (the anchor's horizontal centre) under the island column on its side, the inset grows just enough to clear that column; at the 1451x790 reference viewport both insets take their column-clearance value, and only that value acts as a floor where no column reaches the portrait's face height

#### Scenario: The actor-left anchor carries the controlled figure and the party line
- **WHEN** the shell renders in exploration, dialogue, and combat mode
- **THEN** the `actor-left` anchor carries the controlled character's stage actor — the current roster character's portrait, or the possessed companion's while the possession banner is available — with the committed party's companion stage actors lined up behind it as "Companion standing portraits line up behind the controlled character in the actor-left anchor" defines, each with the truthful placeholder when no image exists; in combat these figures stand at the boxes "Combat figures stand in a shared-scale formation" sets

#### Scenario: The actor-right anchor's content follows the committed mode
- **WHEN** the committed mode is `dialogue` with an available `dialogue` panel whose host identity does not already join to a committed party or controlled lineup figure, and later `combat` with at least one foe active or while a round that ended the fight still plays as "Combat beats are choreographed on the stage at the motion level" defines, and later any other state
- **THEN** the `actor-right` anchor carries the dialogue host's stage actor in the first state, every active foe at the boxes that "Combat figures stand in a shared-scale formation" sets in the second, and no content in every other state; in combat the portrait anchors span the stage so formation boxes are stage coordinates, and no figure enters the dead-centre gap that requirement keeps clear; every stage actor follows "Stage actors present the player and the dialogue host with a speaking state"

#### Scenario: The portrait anchors are non-interactive art
- **WHEN** any stage actor renders
- **THEN** the portrait anchors carry no focusable element and intercept no pointer events, and they MAY sit behind the HUD islands, the `choices` anchor, and the command-line row

#### Scenario: The choices anchor is bounded by the stage box
- **WHEN** dialogue mode renders the choice content, taller than the available span allows
- **THEN** the `choices` anchor renders only in dialogue mode, horizontally centred on the stage box, at most `min(560px, 40%)` of the stage width wide, above the portrait anchors, its content vertically centred in and bounded by the part of the stage box between the top band and the scene caption row that stands on the command-line row so it never meets the scene caption or the expanded command line, scrolling internally when its content is taller than that span allows, and it never grows into the top band, the command-line row, or the bottom band

#### Scenario: Interactive anchors never overlap at or above the reference viewport
- **WHEN** the shell renders at 1451x790, and at every larger viewport up to the chrome factor's cap
- **THEN** no interactive stage anchor (`vitals`, `map`, `band-message`, `band-command`, `choices`, `command-line`) overlaps another interactive anchor's content, and the top band's own elements neither overlap one another nor extend into the HUD island anchor region: a band element whose content is variable-width is bounded and truncated rather than sized by its content

#### Scenario: Only transient popovers may enter the band region
- **WHEN** a transient popover is opened from a top-band element, and when a surface that permanently occupies vertical space is proposed for the band
- **THEN** the transient popover MAY overlay the island anchors while open, provided it does not change the band's own rendered box and closes on Escape and on outside activation, and a surface that permanently occupies vertical space is not introduced into the band this way

#### Scenario: The plates layer is a named stage layer
- **WHEN** combat renders its formation
- **THEN** the `plates` layer is a stage-sized, non-scrolling layer above the portrait anchors and below the HUD islands, the band, the `choices` anchor and the command line, holding only the figure plates

### Requirement: Surface visibility is gated by the committed game mode
The shell SHALL expose the committed mode on the stage root as `data-elosern-mode`, and surface visibility SHALL be derived from that single attribute. A surface hidden for the current mode SHALL be removed from rendering with `display:none` — never dimmed, never merely visually hidden — so it leaves the accessibility tree and the tab order, excepting only the two hold states defined in the scenarios below. The matrix SHALL be:

```text
| Surface | exploration | combat | dialogue | creation |
|---|---|---|---|---|
| place card (location, world time; `map` anchor, above the minimap) | visible | **hidden** (the formation needs the right column) | **hidden** | hidden |
| message window (band message region) | visible | visible | visible (whole band width, paged, name plate) | hidden |
| dialogue choice list (`choices` anchor, centred over the stage) | not rendered | not rendered | once the current response's last page is fully shown, while no action is in flight | not rendered |
| vitals dock (condition icons + vitals bars; `vitals` anchor, lower-left) | by the vitals rule | visible | **hidden** | hidden |
| minimap island | visible | **hidden** | **hidden** | hidden |
| objective line (under the minimap) | visible | hidden | hidden | hidden |
| controlled character and companion standing portraits (`actor-left`) | visible | visible (in the combat formation) | visible (listeners dimmed while the host speaks; the party line stays) | hidden |
| dialogue host standing portrait (`actor-right`) | not rendered | not rendered | while the `dialogue` panel is available (dimmed while the player speaks) | not rendered |
| foe line-up (`actor-right`, every active foe up to 15, in the combat formation) | only while a round that ended the fight still plays (held, inert) | while at least one foe is active | not rendered | not rendered |
| figure plates (`plates` layer, one per drawn non-controlled combat figure) | only while a round that ended the fight still plays (held, inert) | visible | not rendered | not rendered |
| action dock (band command region) | visible | visible | **hidden** (command region collapsed: inert at commit, slides out, then `visibility: hidden`) | visible (creation form, full band width) |
| command-line toggle (⌨, message region's bottom-right) | visible | visible | visible | hidden |
| log control (日誌, beside the command-line toggle) | visible | visible | visible | hidden |
| command line (row on the message region's top edge) | while expanded | while expanded | while expanded | hidden |
| scene backdrop | visible (exploration stage; the combat stage while a round that ended the fight still plays) | visible (combat stage) | visible (unchanged art) | visible |
```

#### Scenario: The minimap disappears in combat
- **WHEN** the committed mode changes from exploration to combat
- **THEN** the minimap island is absent from the DOM layout and from the tab order, and it is not merely dimmed, while the `map` anchor renders nothing, every active foe stands in the combat formation, and each non-controlled figure carries its plate

#### Scenario: The place card stays visible through combat
- **WHEN** the committed mode changes from exploration to combat with a committed location and world time
- **THEN** the place card keeps its committed location and time but is not rendered (`display:none`) while the mode is combat, because the combat formation uses the stage's right column, and it renders again above the minimap island when the mode returns to exploration

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
- **WHEN** the focused element belongs to a surface that the incoming mode hides, including the exit compass, a place-card room action, the 建議 pill, or a person's verb card or a room card when the incoming mode is dialogue
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

#### Scenario: The command region animates out in dialogue
- **WHEN** the committed mode changes to `dialogue`
- **THEN** the band's command region is the one exception to `display:none` hiding: it animates out as "The command region collapses in dialogue mode and the message window spans the band" defines — it leaves the accessibility tree, the tab order, and pointer hit-testing at the commit, and is `visibility: hidden` once its slide ends

#### Scenario: The combat stage hold is the second exception
- **WHEN** a round whose publication already committed another mode still plays, as "Combat beats are choreographed on the stage at the motion level" defines
- **THEN** the decorative combat veil and the foe line-up MAY remain on the stage, outside the accessibility tree, the tab order, and pointer hit-testing, and the scene backdrop SHALL keep presenting the combat stage (its combat gradient and, where a bundled sample wash accompanies a degraded scene, the combat sample) until the round ends, while every other surface follows the committed mode at the commit

#### Scenario: Dialogue exits settle to display:none
- **WHEN** the mode commits to `dialogue`, and separately when the client mounts, reconnects, runs at motion-off, or lacks discrete display transitions
- **THEN** dialogue's `vitals` and `map` anchors MAY retain exit paint over the existing reveal duration while inert, outside the accessibility tree and pointer hit-testing from commit, and settle at `display:none`; in the mount, reconnect, motion-off, and no-discrete-transition cases they are hidden immediately

#### Scenario: Dialogue focus is carried off the backdrop
- **WHEN** the committed mode is `dialogue`
- **THEN** the scene backdrop keeps rendering its committed exploration art truthfully — the dialogue's focus is carried by the stage actors, the name plate, and the message window, and the choice list, not by mutating the backdrop

#### Scenario: Data-rule cells hide like mode-hidden surfaces
- **WHEN** a matrix cell names a data rule instead of `visible`, such as the command line's `while expanded` cell
- **THEN** the surface is shown in that mode only while its own requirement's rule holds for the committed state, and is otherwise hidden the same way (`display:none`, or not rendered at all where that requirement says so); the command line's own requirement defines when the row is expanded, and a collapsed row is hidden with `display:none` exactly like a mode-hidden surface

#### Scenario: Per-surface requirements stay consistent with the matrix
- **WHEN** a per-surface requirement names its own visible-mode set
- **THEN** it stays consistent with this matrix; the place card's visibility follows the matrix exactly — shown in exploration, hidden in combat, dialogue and creation — hiding the `map` anchor in dialogue hides the place card with the minimap, and the card's own visibility rule SHALL NOT claim dialogue after this change

#### Scenario: The mode gate outranks the dock's data rule
- **WHEN** the committed mode is `dialogue` and a committed revision drops a vital below its maximum or adds a new condition
- **THEN** the vitals dock stays hidden through the mode gate regardless of its data rule, its reveal transition does not play until the mode leaves dialogue — the dialogue's attention surface is the message window and the name plate, and the dock returns through its normal reveal when the mode commits back to exploration or combat — while the low-HP stage vignette, not mode-gated, keeps rendering in dialogue so a critical HP state is still conveyed through the stage frame

#### Scenario: Every playing mode names one focus home
- **WHEN** a mode change, a committed revision that turns a surface's data rule false, or a collapse of the command line hides the surface that currently holds focus
- **THEN** the shell moves focus to the focus home of the mode being entered or kept before the surface is removed, using the existing focus-restore path — the action dock in exploration, combat, and creation mode, and the message window's focus target in dialogue mode, as "The command region collapses in dialogue mode and the message window spans the band" defines — and a mode change into creation also collapses the command line, so leaving creation never reveals an expanded row

#### Scenario: The visibility matrix carries its amendments
- **WHEN** the `place-card-relocation` (place card in the `map` anchor), `vitals-bar-redesign` (the vitals dock at the lower left), and `companion-portrait-lineup` (the party quickbar row removed, the portrait row naming the companion line) amendments apply to this requirement
- **THEN** dialogue mode hides the cockpit and navigation surfaces: the place card, the minimap island, and the vitals dock are hidden while the committed mode is `dialogue`

### Requirement: Companion standing portraits line up behind the controlled character in the actor-left anchor
The `actor-left` anchor SHALL render the currently controlled character's standing portrait as the group's rightmost figure with highest baseline z, and SHALL render each companion in committed `party.slots` order to its left, forming an overlapping horizontal row outside combat; in combat the same figures stand at the boxes "Combat figures stand in a shared-scale formation" sets. Each figure SHALL reuse the existing StageActor rendering and remain non-interactive decorative art: no focusable element, no pointer events.

#### Scenario: Portraits resolve through the catalog
- **WHEN** a companion portrait renders
- **THEN** it resolves from `portrait_ref` through `art.portrait_catalog`, falling back to its display name's initial-letter placeholder when null or unresolved

#### Scenario: Every figure shares one size and ground line
- **WHEN** the lineup renders any number of figures
- **THEN** every figure, including the controlled character, has the same full anchor size and ground line; no progressively smaller scale, lift ramp or depth dimming

#### Scenario: The row compresses to stay in the left half
- **WHEN** the row renders at 1451x790, 1741x948 and 2560x1440, in exploration and dialogue
- **THEN** horizontal overlap compresses as necessary to keep the row inside the stage's left half, preserving a scaled left gutter; a multi-figure group MAY shift horizontally within that half; in dialogue the group compresses overlap to clear the choice list without resizing figures; zero companions render the existing solo portrait at its standard anchor position; the anchor has `overflow: visible`; and the vitals dock MAY cover the lowest strip of feet, never face or torso

#### Scenario: Visibility follows the mode
- **WHEN** the committed mode is exploration, combat, dialogue, or creation
- **THEN** the lineup is visible in exploration, combat and dialogue, and hidden in creation

#### Scenario: A speaking companion rises in z only
- **WHEN** a non-controlled rendered companion is the active host speaker in dialogue mode or the selected surviving exploration verb-card target, and when that speaking/focus changes or ends
- **THEN** companions use the existing StageActor listener dim otherwise; the speaking companion temporarily receives z above every baseline figure, returning to its exact baseline z when speaking changes or ends, including across possession swaps and lineup count changes; dialogue speaking and exploration focus change only dim and z, never position, lift or size, and remains correct at off/reduced motion; and the controlled figure retains its existing speaking and beat behavior

#### Scenario: No figure crosses the stage's centre
- **WHEN** the lineup and the foe lineup render together in combat
- **THEN** no figure box enters the dead-centre gap of "Combat figures stand in a shared-scale formation", and both sides are drawn at the same scale

#### Scenario: A two-companion party renders a three-figure group
- **WHEN** the committed `party` panel carries two resolved-portrait slots at 1451x790 in exploration mode
- **THEN** three equally sized figures share a ground line, the player is rightmost with highest baseline z, the companions overlap leftward in party order, no box crosses the horizontal centre and no figure is focusable

#### Scenario: A zero-companion party renders only the player
- **WHEN** the committed `party` panel is available with an empty `slots` list
- **THEN** the `actor-left` anchor renders the player's solo portrait at the standard standing position, byte-stable with the solo layout before this change

#### Scenario: A companion with no portrait shows the initial letter
- **WHEN** a party slot carries `portrait_ref: null` for display name `蕾娜`
- **THEN** that figure renders the initial `蕾` through the stage actor's truthful placeholder, with no invented image or constructed URL

#### Scenario: The full party fits the left half at every viewport
- **WHEN** the committed party carries four slots and the shell renders at 1451x790 and at 2560x1440
- **THEN** all five equally sized figures render with compressed horizontal overlap inside the left half in exploration, each face at least partially visible; in combat they stand in the formation at the shared scale; and in dialogue a speaking companion is brought above the overlapping listeners without moving its slot

#### Scenario: A speaking companion rises temporarily without moving
- **WHEN** the committed dialogue host is a companion and the existing speaker signal changes from player to host and back
- **THEN** that companion changes from dim baseline z to lit highest z and back, preserving its exact geometry; possession swaps, lineup changes and off motion cannot retain stale speaking z

#### Scenario: The companion line and the foe line-up do not overlap
- **WHEN** the committed mode is combat with two companions and three active foes at 1451x790
- **THEN** no companion figure's rendered box intersects any foe figure's rendered box

#### Scenario: Exploration reuses companion emphasis
- **WHEN** a verb card opens for a non-controlled rendered companion while another companion and the controlled figure are present
- **THEN** only the selected companion gains the existing highest focus z and loses listener dim; the other companion keeps baseline/listener dim and the controlled figure keeps its independent dim/beat behavior, without position, size or ground-line changes

#### Scenario: Exploration closure restores current baselines
- **WHEN** that card closes through back, look-close, departure, movement or invalidation, including after lineup count changes
- **THEN** the surviving non-controlled figures use the current geometry's exact baseline z and listener dim with no remembered focus z, at full, reduced and off motion

#### Scenario: Possession preserves the controlled role during focus
- **WHEN** possession/release swaps the front figure while an exploration card is open
- **THEN** identity joins use the current rendered figures, a selected non-controlled companion can be emphasized at its current slot, and the controlled front never receives companion-listener elevation or loses its existing beat/dim semantics

### Requirement: The HUD island stack renders as bounded floating islands, not column cards
The surfaces placed in the stage's island anchors SHALL render as floating HUD islands: a translucent panel fill, a backdrop blur, a hairline border, the shared corner radius, and the shared drop shadow, each island a separate box separated by the anchor's gap — never a single boxed column card and never an opaque `<aside>` stacked in a layout column. No reference panel and no portrait anchor content SHALL be placed in either island anchor.

#### Scenario: The vitals anchor is one dock
- **WHEN** the shell renders the stage box's lower left
- **THEN** it is the vitals dock that "The vitals dock stands at the stage's lower-left above the band" defines: it carries the condition icon row and the vitals bars as one dock, and carries neither a character head card nor a portrait catalog strip nor a party quickbar

#### Scenario: The map anchor stacks its islands in one order
- **WHEN** the shell renders the `map` anchor
- **THEN** it carries, in this order, the place card, the minimap island, the objective line, and the title ballot menu while it is mounted, each present only while its own requirement renders it

#### Scenario: The populated stack never needs anchor scrolling
- **WHEN** the shell renders at the 1451x790 reference viewport and at 2560x1440 with every island populated
- **THEN** the stack's rendered height fits within its anchor, so no required island depends on scrolling the anchor to be seen

#### Scenario: One token change reaches every island
- **WHEN** a design token changes or the reduced-motion block applies
- **THEN** every island's chrome, expressed through the shared design tokens, is reached at once

#### Scenario: The left anchor renders separate islands
- **WHEN** the shell renders in exploration mode with a vital below its maximum, a committed `harmful` condition, and a non-empty party
- **THEN** the condition icon row and the vitals bars render as the lower-left dock's two surfaces in that order, the dock carries the translucent blurred panel chrome, no head card, place card, portrait catalog strip, or party quickbar is rendered, and the party appears only as standing portraits in the `actor-left` anchor

#### Scenario: The populated stack fits its anchor at the minimum viewport
- **WHEN** the shell renders at the 1451x790 reference viewport with every island populated and the condition overflow disclosed
- **THEN** each island anchor's stack fits inside its anchor, the place card's rendered box does not intersect the minimap island below it, and neither stack intersects the bottom band, the command line, or the other island anchor's content

#### Scenario: Island chrome comes from the shared tokens
- **WHEN** an island renders
- **THEN** its fill, border, radius, shadow, and transitions resolve from the shared design tokens rather than from per-component literals

#### Scenario: The map anchor stacks its islands in order
- **WHEN** the shell renders in exploration mode with a committed `local_map` panel, a non-empty `objectives` panel, and title-ballot candidates, and later in combat mode
- **THEN** exploration renders the place card, the minimap island, the objective line, and the title ballot menu in that order in the `map` anchor, and combat renders nothing in the `map` anchor

#### Scenario: The island stack carries its amendments
- **WHEN** the `place-card-relocation` and `vitals-bar-redesign` amendments apply to this requirement
- **THEN** the party quickbar is removed with this change

### Requirement: Combat identity and status remain legible without changing authority
The combat presentation SHALL show each standing participant's name, hit-point stroke and numeric HP on its figure plate (the controlled figure's in the vitals dock), and distinguish the acting or focused-target foe by a non-colour cue without making it interactive. No plate SHALL obscure a standing figure's head. A zero canonical round SHALL be described as preparation rather than incremented.

#### Scenario: Playback HP agrees
- **WHEN** a beat changes display HP for a participant whose portrait reference names a displayed value
- **THEN** its plate's readout and stroke use that value and settle to committed HP together; a null or unmapped reference keeps committed HP on its plate

#### Scenario: First round is not fabricated
- **WHEN** session round is zero and then one
- **THEN** the ribbon shows preparation and then canonical round one, never adding one

#### Scenario: Portrait is missing
- **WHEN** a participant catalog entry is a placeholder
- **THEN** the figure shows its truthful placeholder with one initial and accessible state, and its plate keeps the participant's name; the session token stays in the plate's accessible name only

### Requirement: The place card names the current location and the world time
The stage SHALL carry a place card as the first island of its `map` anchor, at the stage box's top-right corner directly below the top band and directly above the minimap island, while the committed mode is exploration, and SHALL NOT render it in combat mode (where the combat formation uses the stage's right column), creation mode or settled dialogue mode. The card SHALL state the current location as its heading and the world date/time beneath it, and SHALL be the only surface on the stage or in the top band that states either value.

#### Scenario: Dialogue entry leaves only inert exit paint
- **WHEN** the mode live-enters dialogue
- **THEN** the card MAY retain only the inert exit paint permitted by "Surface visibility is gated by the committed game mode", outside the accessibility tree and tab order from commit, and becomes `display:none` when the anchor's fade ends

#### Scenario: The card carries the room actions at the exploration root
- **WHEN** the committed mode is exploration while the exploration panel is available and the exploration dock is at its root frame
- **THEN** the card also carries the room actions `webclient-room-actions` defines — a 查看房間 icon button beside the heading and a 等待 button beside the time — and in every other mode and state it carries no control

#### Scenario: The location resolves in a fixed order
- **WHEN** the card resolves its location
- **THEN** it uses the best server-authored place name the client already holds: the committed `local_map` panel's `current_node` label when that panel is available, names a current node, that node is present in the panel's nodes, and its label is a non-empty string; otherwise the committed status panel's actor location label; otherwise the card's own unavailable placeholder `位置：--`

#### Scenario: The world time is committed or placeholdered
- **WHEN** the card renders its world date/time
- **THEN** it is the committed world-time label, and the card's own unavailable placeholder `時間：--` when none is committed

#### Scenario: The card composes and guesses nothing
- **WHEN** location candidates exist or identifiers are available
- **THEN** the card composes no third string from the two location candidates, derives no name from any node or room identifier, renders no raw room key while a committed panel carries the authored place name for the same room, and renders no raw mode label in place of the location

#### Scenario: The card wears island chrome at a fixed size
- **WHEN** the card renders
- **THEN** it wears the HUD island chrome (the translucent panel fill, the backdrop blur, the hairline border, the shared radius and shadow, all from the shared design tokens), spans the same content-column width as the minimap island beneath it, keeps a fixed height whatever the label lengths, and truncates a label that exceeds its width with an overflow indicator while keeping the full label as its accessible text

#### Scenario: The card is display-only
- **WHEN** the card renders outside exploration, or while the exploration panel is unavailable
- **THEN** it carries no control, no tab stop, and no dispatch; in exploration with the panel available its only controls are the 查看房間 and 等待 buttons, which never truncate the heading's accessible name, and the card itself dispatches nothing

#### Scenario: The two values read on two levels
- **WHEN** the card renders heading and time
- **THEN** it sets them on two levels: the location heading in the serif face at the `--text-lg` step, then a quiet decorative gold rule, hidden from assistive technology, then the world-time line; the heading, the rule, and the time line fit the card's fixed height

#### Scenario: The time line keeps every server value intact
- **WHEN** the world-time line renders
- **THEN** it carries no leading separator glyph or rule before its first value, uses the numeral face with tabular, lining figures at the `--text-sm` step (no smaller than the 16px chrome floor), and renders the committed world-time label (or its placeholder) verbatim, with every date and time value intact: all time values remain server-authored, and the card reformats, abbreviates, or derives none of them

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

#### Scenario: The place card carries its amendment
- **WHEN** the `place-card-relocation` amendment applies to this requirement
- **THEN** the visible-mode set narrows to exploration and combat with this change, matching the visibility matrix's dialogue `hidden` cells

#### Scenario: The card is absent in combat
- **WHEN** the committed mode changes from exploration to combat, and later back
- **THEN** in combat the place card is not rendered (`display:none`, outside the accessibility tree) while it keeps its committed location and time, and on the return it renders again as the first island of the `map` anchor

### Requirement: Combat beats are choreographed on the stage at the motion level
While a combat round plays by itself, as `webclient-combat-menu` "A combat round plays beat by beat" defines, each beat SHALL play one stage gesture once its page is fully shown, on the stage actors that the beat names and that stand on the stage (the player in `actor-left`, a foe in the foe line-up), taking every duration and distance from the client's motion tokens.

#### Scenario: Each beat kind plays its gesture
- **WHEN** a beat's page is fully shown
- **THEN** the first beat of each action: the acting stage actor steps 12px × S toward the stage's centre and back within 240ms, staying inside its 16px × S gutter beside the command card; `damage`: the target's stage actor shakes 6px from side to side for 180ms with a brief flash, a decorative number naming the damage rises from it and fades over 600ms, and its displayed hit points move to the beat's `hp_after` as the gesture starts, in the vitals or on the figure's plate, with the trailing bar following; `target_defeated`: a foe's stage actor fades and drops out of the line-up — the player's stage actor never leaves the stage; `roll` and `other`: no gesture

#### Scenario: Pauses and actorless beats follow the gesture
- **WHEN** a gesture finishes, or a beat names a participant with no stage actor (a party member other than the player, or a foe beyond the line-up's maximum)
- **THEN** the next beat's pause starts when the gesture has played, and an actorless beat plays no gesture

#### Scenario: Choreography is decorative
- **WHEN** gestures, rising numbers, or flashes play
- **THEN** they are absent from the accessibility tree, never intercept a pointer, and are never the only carrier of any value, which the beat's page and the numerals already state

#### Scenario: The round that ends the fight holds decoration only
- **WHEN** the round's publication has already committed a mode other than `combat`, and later the round ends — by itself or because the player ended it
- **THEN** while the round plays the combat veil stays at its combat opacity and the foe line-up stays on the stage, inert; when it ends the veil fades out and the line-up leaves as a live change out of combat does; and the mode attribute, every mode-gated surface, the command region's content, focus, and the accessibility tree follow the committed mode at the commit, with the committed flash and flip playing at the commit as "Mode changes transition at the motion level" defines

#### Scenario: Reduced and off release the stage
- **WHEN** beats play at `reduced`, and at `off`
- **THEN** at `reduced` no step, shake, flash, rise, or drop moves or brightens anything, a defeated foe only fades within 150ms, and the pauses are kept; at `off` no round plays by itself, so no gesture and no stage hold occur

#### Scenario: The actor steps and the target reacts
- **WHEN** the effective level is `full` and a playing round shows the player's roll beat and then its
  damage beat on a foe on the stage
- **THEN** the player's stage actor plays one 240ms step toward the centre on the roll beat, and on the
  damage beat the foe's stage actor plays one 180ms shake with a flash, a number naming the damage rises
  from it over 600ms, and the foe's plate stroke and readout move to the beat's `hp_after`

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

## REMOVED Requirements

### Requirement: Foes stand opposite the player during combat
**Reason**: Replaced by "Combat figures stand in a shared-scale formation": every active foe (up to 15) now stands, at the scale the party shares, instead of at most three depth-staged foes, so the dead-centre command card has a clear gap.
**Migration**: The foe line-up's depth table (`FOE_SCALES`, `FOE_EXPOSED`, `FOE_LIFT`) and its three-foe cap are retired; tests asserting the 100/90/78/80/70/61% heights move to the formation's boxes.

### Requirement: The combat participant frame presents the session's participants and their portraits
**Reason**: The user asked to remove the redundant roster; each figure now carries its own plate ("Combat figures carry glance plates"), every active foe stands on the stage, and the `map` anchor is not rendered in combat.
**Migration**: `ParticipantFrame.vue`, its stories and its tests (`tests/core/participant_frame.test.js`, `tests/combat/participant_frame.test.js`) are deleted together with the `participant-frame` test id; browser assertions on it move to the plates.
