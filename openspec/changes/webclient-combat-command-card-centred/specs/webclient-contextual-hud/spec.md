## ADDED Requirements

### Requirement: The combat command card stands at the stage's dead centre
While the committed mode is `combat`, the client SHALL present the same `#action-dock` element as one narrow card in the stage's `choices` anchor, framed like the stage's other choice cards, with the band's command region collapsed. The card's horizontal centre SHALL be the stage's horizontal centre in every combat state; its width SHALL follow the gap on the party side; and it SHALL NOT cover a foe name plate, foe gauge or focused-target cue.

#### Scenario: The width and height follow the stated formulas
- **WHEN** combat renders at 1451x790 and at 1600x900
- **THEN** the card's width is `clamp(240px × S, 2 × (stage centre − party edge − 16px × S), 280px × S)` (±1px), where S is the desktop chrome factor and the party edge is the right edge of the controlled figure's box as the uncompressed companion line-up places it; its top is the `choices` anchor's top, its bottom stands at least 8px × S above the foe name-plate line, its height is the smaller of 400px × S and that span, and it MAY stand over foe art or the margin of the controlled figure's box

#### Scenario: The card is at dead centre for every party size and foe count
- **WHEN** combat renders at 1451x790 and at 1600x900 with one, two, three and five active foes, each with a solo player, a four-figure party (the player and three companions) and a five-figure party
- **THEN** `#action-dock` lies inside the `choices` anchor and its horizontal centre is the stage's horizontal centre (±1px) in every case; no case shifts it left or right of the centre

#### Scenario: The width follows the guaranteed gap on the party side
- **WHEN** combat renders with a solo player, a three-figure party, a four-figure party and a five-figure party at 1451x790 and at 1600x900
- **THEN** the card's width is `clamp(240px × S, 2 × (stage centre − controlled figure's box right edge − 16px × S), 280px × S)` (±1px): 280, 280, 263.6 and 240 at 1451x790 and 308.8, 308.8, 264.6 and 264.6 at 1600x900; with up to four figures the card does not intersect any party figure's box, and with five figures it intersects only the controlled figure's box and by at most 24.5px at 1451x790 and 49.5px at 1600x900

#### Scenario: The card never covers a foe plate, gauge or cue
- **WHEN** combat renders at 1451x790 and at 1600x900 with one, two and three active foes, including while the attack target frame focuses the rearmost foe
- **THEN** the card's bottom edge is at least 8px × S above the top edge of every foe name plate, so it intersects no foe name plate, no foe gauge and no focused-target cue; with one foe it intersects no foe stage actor box either

#### Scenario: The card keeps the stage's other surfaces clear
- **WHEN** combat renders at 1451x790 and at 1600x900 with one and with three active foes and the command line expanded
- **THEN** the card lies inside the stage box below the top band and intersects no `vitals`, `map` (the place card and the participant frame), band, or command-line anchor, and the vitals dock stays visible

#### Scenario: No frame resizes the card
- **WHEN** the player moves at 1451x790 from the combat root through Skills, a category, a group, a skill frame, a master's 威力 scale step and the target step, and separately opens the Forfeit confirmation
- **THEN** the card's rendered box is identical (±1px) in every frame, the row region scrolls inside the card keeping the focused row in view, and the detail strip and the shortcut legend stay at the card's foot

#### Scenario: Every frame lays out in one narrow column
- **WHEN** the combat root, a category, a group, a skill frame, a master's scale step, a SINGLE target frame, an AREA target frame and the Forfeit confirmation render in a 240px × S wide card
- **THEN** the root, category, group, skill and SINGLE/SELF/NONE target frames render one row per line in a single column, the AREA token grid keeps its two columns and the scale step its one column per scale, every row and chip lies inside the card without horizontal overflow, a long label wraps within its row, and the keyboard cell mapping of every frame is unchanged

#### Scenario: The detail folds into a strip below the rows
- **WHEN** a frame with a detail renders in the card — the combat root, a category, a skill frame, or a master's scale step — and a disabled entry is focused
- **THEN** the row region and the detail strip are direct children of the pane host, the strip lies entirely below the row region across the card's inner width at a fixed height of three text lines, its first line states the focused entry's cost and target requirement where it carries them, the remaining lines state its description or, for a disabled entry, its server-authored reason in place of the description, clipped with an ellipsis, and the strip's full text stays in the DOM and is the focused row's accessible description

#### Scenario: The breadcrumb and the legend fit the narrow card
- **WHEN** the card renders a frame three levels below the root, and the shortcut legend
- **THEN** the breadcrumb is one line whose back control and current frame name stay visible while earlier crumbs ellipsize, and the legend keeps its text, wrapping at its separators onto at most two lines

#### Scenario: The card wears the shared card frame
- **WHEN** the card renders
- **THEN** it paints the same frame as the dialogue choice list's card — the gold-edged ink panel, the crest on its top edge and the four corner brackets — its frame brightens while keyboard focus is within it, and the crest and brackets are absent from the accessibility tree and never intercept a pointer

#### Scenario: The band collapses while the card stands
- **WHEN** the committed mode changes from exploration to combat at 1451x790, and later back
- **THEN** in combat the band's command region is `display:none` and the message region spans the band's whole width at the band's fixed height, its reading column keeping its measure; on the return the command region renders again at the band's right third holding the same `#action-dock` element

#### Scenario: The dock moves, never remounts
- **WHEN** the committed mode changes from exploration to combat, from combat to exploration, and from combat to dialogue
- **THEN** exactly one `#action-dock` element exists at every point and it is the same node before and after each change, its `data-mode` follows the committed mode, and it is a descendant of the `choices` anchor exactly while the mode is combat

#### Scenario: Focus survives the move
- **WHEN** focus is on the exit compass or on the dock and the mode changes into combat, and later focus is inside the card and the mode changes back to exploration
- **THEN** after the commit's render focus is on `#action-dock` or inside it in combat, and on the exit compass in exploration, never on the document body; focus the player put in the command field or an open drawer stays where it was

#### Scenario: Keys and pointer behave as before
- **WHEN** the card is shown and the player uses the arrow keys, Enter, Escape, the digits 1–9, the breadcrumb's back control, and pointer clicks on rows
- **THEN** every key and activation routes through the same keyboard router and dispatch entry as in the band, emits byte-identical payloads, and the card adds no key handling of its own

#### Scenario: The card enters with combat and never on a reconnect
- **WHEN** the mode live-changes into combat at `full`, at `reduced`, and at `off`, and when the client reloads or reconnects in combat
- **THEN** at `full` the card fades in over 250ms while rising by the small shift, starting once the 120ms flash has played; at `reduced` it only fades, within 150ms and with no delay; at `off`, and on a reload or reconnect, it renders at rest in the commit's frame; in every case its rows take keys and pointer from the commit's frame

#### Scenario: Playback veils the card's body
- **WHEN** a combat round plays by itself and locks the commands, and later the player activates 跳過演出
- **THEN** the waiting cue with its skip control covers the card's body inside the card while the card keeps its box, and the skip ends the round through the existing skip path

## MODIFIED Requirements

### Requirement: The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces
The WebClient SHALL render as a full-bleed stage filling the viewport, layered bottom-up: the scene backdrop, the portrait anchors, the HUD islands, the bottom band, and the command line topmost among the persistent surfaces. HUD surfaces SHALL be placed by named stage anchors — `vitals`, `map`, `actor-left`, `actor-right`, `band-message`, `band-command`, `choices`, `presence`, and `command-line` — and SHALL NOT sit inside a page-scrolling container that can push a required surface out of view.

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
- **WHEN** the HUD islands hold more content than their anchor's height, or the dock frame or the narrative holds more content than its band region or the combat command card
- **THEN** the island stack, the band region, or the card itself is bounded and scrolls internally, and no required surface is pushed below the visible viewport

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
- **THEN** the bottom band's rendered height is 220px (±1px) in every one of those states, the message region's and the command region's boxes are unchanged between the exploration states, and in the combat and dialogue states the message region spans the band's whole width at the same height while the command region is collapsed

#### Scenario: The band splits two thirds and one third
- **WHEN** the shell renders in exploration mode at 1451x790 and at 2560x1440
- **THEN** the message region spans the left two thirds of the band's width and the command region spans the remaining right third (each ±1px), both share the band's top and bottom edges, in creation mode the command region spans the whole band, and in dialogue and combat mode the message region spans the whole band while the command region is not rendered

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
- **THEN** the band is divided into the message region `band-message`, covering the left two thirds of the band's width, and the command region `band-command`, covering the remaining right third; in creation mode, where the message region is hidden, the command region spans the whole band, and in dialogue and combat mode, where the command region is collapsed, the message region spans the whole band

#### Scenario: Every surface avoids the band through the band-height token
- **WHEN** the shell renders in exploration mode at the 1451x790 reference viewport
- **THEN** the stage box — the region between the top band's lower edge and the bottom band's upper edge, where the scene is seen — is at least 65% of the viewport's height (at least 513.5px of 790; the 48px top band and the 220px bottom band leave 522px), and every surface other than the band is positioned relative to the band-height token so that none of them overlaps the band

#### Scenario: The portrait anchors stand on the band and clear the island columns
- **WHEN** the shell renders with the vitals stack on the left and the place card and minimap card on the right
- **THEN** each portrait anchor is bottom-aligned to the band's upper edge, `min(62vh, 680px)` tall but never taller than the stage box, inset at least 6% of the stage width from its own side, and never covering the band; where 6% would place the figure's face (the anchor's horizontal centre) under the island column on its side, the inset grows just enough to clear that column; at the 1451x790 reference viewport both insets take their column-clearance value, and only that value acts as a floor where no column reaches the portrait's face height

#### Scenario: The actor-left anchor carries the controlled figure and the party line
- **WHEN** the shell renders in exploration, dialogue, and combat mode
- **THEN** the `actor-left` anchor carries the controlled character's stage actor — the current roster character's portrait, or the possessed companion's while the possession banner is available — with the committed party's companion stage actors lined up behind it as "Companion standing portraits line up behind the controlled character in the actor-left anchor" defines, each with the truthful placeholder when no image exists

#### Scenario: The actor-right anchor's content follows the committed mode
- **WHEN** the committed mode is `dialogue` with an available `dialogue` panel whose host identity does not already join to a committed party or controlled lineup figure, and later `combat` with at least one foe active or while a round that ended the fight still plays as "Combat beats are choreographed on the stage at the motion level" defines, and later any other state
- **THEN** the `actor-right` anchor carries the dialogue host's stage actor in the first state, the foe line-up that "Foes stand opposite the player during combat" defines in the second, and no content in every other state; the foe line-up MAY extend leftward beyond the anchor's own box, within the bounds that requirement sets, and SHALL NOT cross the stage's horizontal centre, which the companion line-up's figures also never cross; every stage actor follows "Stage actors present the player and the dialogue host with a speaking state"

#### Scenario: The portrait anchors are non-interactive art
- **WHEN** any stage actor renders
- **THEN** the portrait anchors carry no focusable element and intercept no pointer events, and they MAY sit behind the HUD islands, the `choices` anchor, and the command-line row

#### Scenario: The choices anchor is bounded by the stage box
- **WHEN** dialogue mode renders the choice content, taller than the available span allows
- **THEN** the `choices` anchor renders only in dialogue mode, while an exploration card is open, and in combat mode — where it holds the combat command card, whose horizontal placement, width, top-anchored placement and height "The combat command card stands at the stage's dead centre" sets — and otherwise it is horizontally centred on the stage box, at most `min(560px, 40%)` of the stage width wide; in every mode it stands above the portrait anchors, its content vertically centred in and bounded by the part of the stage box between the top band and the scene caption row that stands on the command-line row so it never meets the scene caption or the expanded command line, scrolling internally when its content is taller than that span allows, and it never grows into the top band, the command-line row, or the bottom band

#### Scenario: Interactive anchors never overlap at or above the reference viewport
- **WHEN** the shell renders at 1451x790, and at every larger viewport up to the chrome factor's cap
- **THEN** no interactive stage anchor (`vitals`, `map`, `band-message`, `band-command`, `choices`, `command-line`) overlaps another interactive anchor's content, and the top band's own elements neither overlap one another nor extend into the HUD island anchor region: a band element whose content is variable-width is bounded and truncated rather than sized by its content

#### Scenario: Only transient popovers may enter the band region
- **WHEN** a transient popover is opened from a top-band element, and when a surface that permanently occupies vertical space is proposed for the band
- **THEN** the transient popover MAY overlay the island anchors while open, provided it does not change the band's own rendered box and closes on Escape and on outside activation, and a surface that permanently occupies vertical space is not introduced into the band this way

### Requirement: Surface visibility is gated by the committed game mode
The shell SHALL expose the committed mode on the stage root as `data-elosern-mode`, and surface visibility SHALL be derived from that single attribute. A surface hidden for the current mode SHALL be removed from rendering with `display:none` — never dimmed, never merely visually hidden — so it leaves the accessibility tree and the tab order, excepting only the two hold states defined in the scenarios below. The matrix SHALL be:

```text
| Surface | exploration | combat | dialogue | creation |
|---|---|---|---|---|
| place card (location, world time; `map` anchor, above the minimap) | visible | visible | **hidden** | hidden |
| message window (band message region) | visible | visible (whole band width, paged) | visible (whole band width, paged, name plate) | hidden |
| dialogue choice list (`choices` anchor, centred over the stage) | not rendered | not rendered | once the current response's last page is fully shown, while no action is in flight | not rendered |
| combat command card (`choices` anchor; the action dock itself) | not rendered | visible | not rendered | not rendered |
| vitals dock (condition icons + vitals bars; `vitals` anchor, lower-left) | by the vitals rule | visible | **hidden** | hidden |
| minimap island | visible | **hidden** | **hidden** | hidden |
| objective line (under the minimap) | visible | hidden | hidden | hidden |
| controlled character and companion standing portraits (`actor-left`) | visible | visible | visible (listeners dimmed while the host speaks; the party line stays) | hidden |
| dialogue host standing portrait (`actor-right`) | not rendered | not rendered | while the `dialogue` panel is available (dimmed while the player speaks) | not rendered |
| foe line-up (`actor-right`, at most three active foes) | only while a round that ended the fight still plays (held, inert) | while at least one foe is active | not rendered | not rendered |
| action dock (band command region) | visible | **in the combat command card** (command region collapsed: `display:none`) | **hidden** (command region collapsed: inert at commit, slides out, then `visibility: hidden`) | visible (creation form, full band width) |
| command-line toggle (⌨, message region's bottom-right) | visible | visible | visible | hidden |
| log control (日誌, beside the command-line toggle) | visible | visible | visible | hidden |
| command line (row on the message region's top edge) | while expanded | while expanded | while expanded | hidden |
| scene backdrop | visible (exploration stage; the combat stage while a round that ended the fight still plays) | visible (combat stage) | visible (unchanged art) | visible |
```

#### Scenario: Combat presents the dock as the centred card
- **WHEN** the committed mode changes from exploration to combat, and later back to exploration
- **THEN** in combat the band's command region is `display:none`, the message region spans the band, and the same `#action-dock` element renders as the combat command card in the `choices` anchor as "The combat command card stands at the stage's dead centre" defines; on the return the command region renders at the band's right third holding that element again, and the `choices` anchor holds no dock

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
- **THEN** it stays consistent with this matrix; the place card's visibility follows the matrix exactly — shown in exploration and combat, hidden in dialogue and creation — hiding the `map` anchor in dialogue hides the place card with the minimap, and the card's own visibility rule SHALL NOT claim dialogue after this change

#### Scenario: The mode gate outranks the dock's data rule
- **WHEN** the committed mode is `dialogue` and a committed revision drops a vital below its maximum or adds a new condition
- **THEN** the vitals dock stays hidden through the mode gate regardless of its data rule, its reveal transition does not play until the mode leaves dialogue — the dialogue's attention surface is the message window and the name plate, and the dock returns through its normal reveal when the mode commits back to exploration or combat — while the low-HP stage vignette, not mode-gated, keeps rendering in dialogue so a critical HP state is still conveyed through the stage frame

#### Scenario: Every playing mode names one focus home
- **WHEN** a mode change, a committed revision that turns a surface's data rule false, or a collapse of the command line hides the surface that currently holds focus
- **THEN** the shell moves focus to the focus home of the mode being entered or kept before the surface is removed, using the existing focus-restore path — the action dock in exploration, combat, and creation mode, and the message window's focus target in dialogue mode, as "The command region collapses in dialogue mode and the message window spans the band" defines — and a mode change into creation also collapses the command line, so leaving creation never reveals an expanded row

#### Scenario: The visibility matrix carries its amendments
- **WHEN** the `place-card-relocation` (place card in the `map` anchor), `vitals-bar-redesign` (the vitals dock at the lower left), and `companion-portrait-lineup` (the party quickbar row removed, the portrait row naming the companion line) amendments apply to this requirement
- **THEN** dialogue mode hides the cockpit and navigation surfaces: the place card, the minimap island, and the vitals dock are hidden while the committed mode is `dialogue`

### Requirement: Combat skills are chosen through a bounded master-detail
In combat, opening Skills SHALL present the committed skill categories as a bounded frame of category entries, each carrying its server-authored label and the count of its own skill descriptors. Opening a category SHALL present that category's sub-groups as a frame when the category carries more than one sub-group, and SHALL open the skill frame directly when it carries exactly one — so no menu level ever offers a single choice.

#### Scenario: The skill frame lists descriptors beside a detail region
- **WHEN** a skill frame renders
- **THEN** it lists that group's descriptors in the server's order, each row carrying the skill's label and its resource cost, with a detail region — a strip below the rows inside the combat command card — naming the focused skill, its description, its cost, its target requirement and, when it is unavailable, its server-authored reason

#### Scenario: Server grouping is never reshaped
- **WHEN** any skill level renders
- **THEN** category, group and skill ordering is exactly the committed panel's order at every level; the frames do not reorder, filter or merge the server's grouping, and render no badge or field the skill descriptor does not carry

#### Scenario: Scale and target steps keep behaviour and payload
- **WHEN** the player proceeds through the power-scale step and the target step
- **THEN** both are unchanged in behaviour and payload: the scale frame renders each advertised scale with its server-computed cost in ascending order, the target frame renders the valid participants as selectable tokens distinguishing the player's side from the opposing side and preserving the existing multi-select marker, and every submitted cast payload is byte-identical to the payload the same choices produce today

#### Scenario: Arrow navigation keeps the focused row in view
- **WHEN** a frame renders or focus changes
- **THEN** the focused row is scrolled into view within the bounded row region, so arrow navigation never leaves the focused row off-screen

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

### Requirement: The action dock fills the band's command region at a fixed size
Outside combat the action dock SHALL fill the bottom band's command region — the right third of the band, or the whole band in creation mode — at the band's fixed height, and SHALL NOT be a floating panel placed elsewhere on the stage. In combat mode the dock SHALL instead stand as the combat command card that "The combat command card stands at the stage's dead centre" defines. Its box SHALL be the command region's box in exploration and creation mode and the card's fixed box in combat, for every frame, and no other surface SHALL be positioned from the frame the dock currently carries.

#### Scenario: No frame moves or resizes the dock
- **WHEN** the dock carries the exploration root (with or without a person's verb card or a room card open over the stage), the combat frames, the skill master-detail, the destructive confirmation, or an empty pane host
- **THEN** no frame widens, heightens, shortens, or moves its box

#### Scenario: Dialogue hides the dock with the region
- **WHEN** the committed mode is dialogue
- **THEN** the command region is collapsed and the dock is hidden with `display:none` together with it, as "The command region collapses in dialogue mode and the message window spans the band" states; it is not rendered anywhere else in that mode

#### Scenario: Fixed chrome surrounds one scrolling region
- **WHEN** the dock's content column lays out
- **THEN** it is laid out as fixed chrome — the combat root's vertical command list in combat mode and no bar in exploration mode, an optional breadcrumb line, and the shortcut-legend strip at the bottom in combat only — around one remaining region that holds the current frame's rows or chips, and that region is the surface's only scrolling area, so no dock content is ever pushed outside the command region or, in combat, the card

#### Scenario: Popovers and wide frames stay inside the region
- **WHEN** a person's verb card, the wait card, or the suggestions card renders, or a frame's content does not fit the region's width
- **THEN** the card renders centred over the stage in the `choices` anchor, outside the command region, scrolling inside its own card when its rows exceed it, while the command region keeps its box, and the wide frame wraps or collapses its own columns inside the region or the combat card, never overflowing it horizontally

#### Scenario: One dock element persists across every mode
- **WHEN** the committed mode changes, including into or out of dialogue or combat
- **THEN** the panel is the same single `#action-dock` element in every mode, carrying its existing tab index, its `data-mode` attribute and its role as the documented focus forwarding target, with the compass owning exploration-root focus and the active row container owning other dock frames, and it is not remounted

#### Scenario: The presentation stays readable beyond colour
- **WHEN** the command region and its band render
- **THEN** the command region uses the current charcoal-and-gold presentation, the band that contains it paints the reference's band chrome, and selected actions remain distinguishable by text and shape as well as their gold or warm-red emphasis

#### Scenario: The command region is the band's right third
- **WHEN** the shell renders in exploration mode at 1451x790 and at 2560x1440
- **THEN** the `#action-dock` element lies inside the band's command region, the region's left edge is at two thirds of the stage width and its right edge at the stage's right edge (each ±1px), and the dock covers neither the message region nor the command line

#### Scenario: No frame resizes the command region
- **WHEN** the dock moves at 1451x790 from the exploration root to a person's verb card over the stage and to the wait card, and later, in combat, from the combat root to the deepest skill target frame
- **THEN** the command region's rendered box is identical (±1px) in the three exploration states, the combat command card's rendered box is identical (±1px) in every combat frame, the band's height is unchanged throughout, and each card lies over the stage above the band

#### Scenario: An overflowing frame scrolls inside the panel
- **WHEN** the current frame holds more rows than the dock's row region can display
- **THEN** the row region scrolls internally, the dock's chrome (the combat root list, the breadcrumb,
  and the combat-only legend strip) stays fixed, and no row or chip is rendered outside the command region or, in combat, the card

#### Scenario: One dock element persists across a mode change
- **WHEN** the committed mode changes between exploration, dialogue, combat and creation
- **THEN** exactly one `#action-dock` element exists at every point, its `data-mode` attribute
  switches to the new mode, it is hidden with `display:none` exactly while the mode is dialogue, it stands
  in the combat command card exactly while the mode is combat, and it is not removed and re-created

#### Scenario: The panel stays inside its region at the minimum viewport
- **WHEN** the shell renders at 1451x790 with the deepest combat frame open
- **THEN** the dock's rendered box is the combat command card's box inside the `choices` anchor, no dock
  content overflows the card horizontally, and the frame's confirm control is reachable by scrolling
  the row region without being clipped

#### Scenario: The band's background matches the reference's shadowed gradient
- **WHEN** the bottom band renders in any mode
- **THEN** the band element paints a background gradient and a box-shadow, its top edge is the
  seam's fine gold line drawn by the band's own decoration, and outside combat the `#action-dock`
  content column itself paints no background, border, or shadow (in combat it paints the shared card
  frame of the combat command card)

### Requirement: A fixed-column dock pane stays inside the command region
When a dock pane's row region uses a fixed column count for keyboard row/col geometry, that fixed count SHALL govern only which cell each row occupies. Changing a row's rendered width SHALL NOT change which row occupies which cell.

#### Scenario: Pane forms own their own layout
- **WHEN** a pane form (the combat skill list, the target tokens, the scale chips) lays out its rows
- **THEN** this requirement prescribes not how wide a column or row renders: each form uses its own styles, and whether a form fills the pane's width or leaves width empty is a visual decision of that form

#### Scenario: Rows never overflow the pane horizontally
- **WHEN** the pane's available width is narrower than the rows' natural width
- **THEN** whatever the form, every row renders inside the pane's box without horizontal overflow: the rows wrap or compress, and long content wraps within its row

#### Scenario: The scene overview is not a fixed-column pane
- **WHEN** the exploration root renders
- **THEN** its pane is the compass beside the 建議 pill and the readout, with no row region at all — the exploration root is not a fixed-column pane

#### Scenario: A narrow command region keeps every row inside the pane
- **WHEN** a combat skill, target, or scale pane renders in the combat command card at the 1451x790 reference viewport with three foes standing
- **THEN** every row lies inside the pane's right edge, the pane shows no horizontal overflow, and a long label wraps within its row

#### Scenario: Rendered width never changes the keyboard cell mapping
- **WHEN** the player presses ArrowRight in a pane whose keyboard geometry fixes two columns
- **THEN** focus reaches the row that the fixed column count places in the second column, whatever width each row renders at

### Requirement: Mode changes transition at the motion level
The stage SHALL animate live mode changes, taking every duration, delay, and distance from the client's motion tokens, so they follow the effective motion level of "The motion level is a client-local preference that governs every client animation".

#### Scenario: Dialogue entry and exit animate as reverses
- **WHEN** the mode changes exploration → dialogue, and dialogue → exploration
- **THEN** entering: the command region slides out to the right over the panel duration (250ms at `full`) while the message window spans the band from the commit's frame, the dialogue host's stage actor slides in from the right and fades in over the actor duration (350ms at `full`), the name plate fades in, and the greeting pages and types as `webclient-input-narrative` defines; leaving: the reverse — the host's stage actor slides out to the right and fades, the name plate fades out, the message window returns to two thirds of the band in the commit's frame, and the command region slides back in

#### Scenario: Combat entry flashes; exit plays no flash
- **WHEN** the mode changes exploration → combat, and combat → exploration
- **THEN** entering: a white flash lasting the flash duration (120ms at `full`) plays once over the stage and under every island, the combat veil fades in, the command region collapses, and the combat command card comes in over the stage as the flash releases; leaving: the veil fades out, the command region returns and its content flips back to the exploration root, and no flash plays

#### Scenario: Choice rows stagger in
- **WHEN** the dialogue choice list appears, or rows are swapped in by `↦ 移動…` or by its return
- **THEN** each row fades in and rises into place, delayed by the stagger step (40ms at `full`) times its position, and the list's card fades in; swapped rows stagger the same way

#### Scenario: Only live changes animate
- **WHEN** the client mounts, reconnects, or a resync commits the same mode
- **THEN** none of these transitions plays

#### Scenario: Transitions never delay state, input, or scroll
- **WHEN** any mode transition plays
- **THEN** every leaving element is out of reach as "A leaving element is out of reach while it animates out" requires; no transition delays a committed value or the player's input beyond its own duration — the choice list takes focus and handles keys and pointer from its first frame, the combat command card's rows take keys and pointer from the commit's frame, and the dock is focusable from the first frame of its return; and the mode change scrolls nothing — a surface that slides past the stage's edge is clipped without widening any ancestor's scrollable area, no focus move during a mode change scrolls an ancestor toward its target, and the stage never shifts sideways

#### Scenario: Decorations stay out of the tree and off the pointer
- **WHEN** the flash, the veil, the card's entrance, or the flip plays
- **THEN** each is decorative, absent from the accessibility tree, and never intercepts a pointer

#### Scenario: Reduced and off settle every mode change
- **WHEN** a mode change plays at `reduced`, and at `off`
- **THEN** at `reduced` the slides, the flip's rotation, the card's rise, and the rows' rise move nothing, the fades last at most 150ms, the flash is not visible, and the stagger is zero; at `off` every mode change renders its final state in the commit's frame

#### Scenario: Entering dialogue slides the panel out and the host in
- **WHEN** the effective level is `full` at 1451x790 and the player opens a conversation
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
  the combat command card plays one entrance — a 250ms fade and a rise by the small shift, delayed by
  the 120ms flash — while it already holds the dock's rows, the command region plays no flip, and none
  of the decorations is in the accessibility tree or receives a click

#### Scenario: Leaving combat plays no flash
- **WHEN** the effective level is `full` and the mode changes from combat to exploration
- **THEN** the veil fades out, the command region renders again and its content flips back, the combat
  command card is gone at the commit, and the flash layer plays no animation

#### Scenario: Choice rows stagger in without delaying input
- **WHEN** the effective level is `full` and the dialogue choice list appears with five rows
- **THEN** row N's entrance is delayed by 40ms × N, the list holds focus in its first frame, and a digit
  pressed before the last row has finished entering activates that row

#### Scenario: A reconnect replays nothing
- **WHEN** the client reconnects while the committed mode is combat or dialogue
- **THEN** no flash, flip, slide, card entrance, or stagger plays, and every surface renders its final
  state, the combat command card at rest

#### Scenario: Reduced keeps short fades and drops every movement
- **WHEN** the effective level is `reduced` and the player enters and leaves dialogue, then enters combat
- **THEN** the command region, the host, the name plate, the veil, the combat command card, and the
  choice rows only fade, each within 150ms, the card with no delay, no slide, rotation, or rise moves anything, no flash is visible, and the rows appear
  together

#### Scenario: Off renders every mode change at once
- **WHEN** the effective level is `off` and the mode changes into and out of dialogue and combat
- **THEN** in the commit's frame each surface holds its final state: the command region hidden or
  shown, the combat command card present or absent at rest, the host present or absent, the veil at its final opacity, the flash invisible, and every
  choice row fully shown

### Requirement: The bottom band separates material and focus without obscuring controls
The fixed bottom band SHALL provide a continuous ink-and-gold reading surface with a decorative stage seam and an aligned message-control row; the shortcut legend stands at the foot of the dock that carries it (in combat, inside the combat command card). Page text, command rows and cards SHALL never paint over these reserved controls. Only the active control SHALL carry the strongest focus treatment; the command field SHALL expose one clear focus frame.

#### Scenario: Popover text is isolated
- **WHEN** a person's verb card opens over the stage with populated scene chips in the command panel
- **THEN** no stage or chip text shows through the card, the person is named once by the speaker line, and the inert command panel's chips cannot activate

#### Scenario: Dense command content is bounded
- **WHEN** a frame contains more rows than fit
- **THEN** its own row region scrolls while the shortcut legend at the card's foot and the band's message controls remain visible and unmoved

#### Scenario: Motion is reduced
- **WHEN** the player changes command frames with reduced motion or off
- **THEN** reduced uses no 3D rotation or wipe and off commits immediately without losing focus

### Requirement: Playback lock is visible without inventing progress
While combat playback locks mutation controls, the combat command card SHALL communicate that it is waiting and expose the existing skip interaction clearly. A decorative activity line SHALL NOT imply a server completion percentage and SHALL be static at reduced/off.

#### Scenario: The cue appears only while playback locks the commands
- **WHEN** a combat round starts playing by itself at `full` motion, and later at `off`
- **THEN** the combat command card shows the waiting cue over its body with a skip control while the round plays, keeping its box, and at `off`, where nothing locks, no cue appears

#### Scenario: Skip settles the lock
- **WHEN** the player skips a locked playing round
- **THEN** the cue clears with playback and the existing canonical command state becomes available
