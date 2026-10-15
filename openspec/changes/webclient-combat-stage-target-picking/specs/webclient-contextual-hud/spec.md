## ADDED Requirements

### Requirement: The stage target step presents the targets on the stage figures
During the stage target step that "Combat targets are picked on the stage figures" defines, the combat command card SHALL collapse to a target prompt, every stage figure SHALL take the same listener dim that non-speaking figures take in dialogue except the figures of the focused position's lit set, each selectable figure SHALL carry an arrow marker above it, and the focused position SHALL be lit with a highlight that pulses at `full` and stays static at `reduced` and `off`.

#### Scenario: The card collapses to a target prompt
- **WHEN** the stage target step opens at 1451x790 and at 1600x900 with one, two and three standing foes and parties of one, four and five figures
- **THEN** the card keeps its horizontal centre, width and top, its height is at most 72px × S, it shows the action's label (with the chosen 威力 label when the skill carries one), 選擇目標, the focused position's name and side or group label and size, and `Esc 返回`; an AREA step also shows one chip per group position and the confirm chip; the row region is hidden, DOM focus is on `#action-dock`, and the prompt intersects no arrow marker, foe name plate or gauge

#### Scenario: Every figure dims except the lit set
- **WHEN** the step focuses one foe among three standing foes with a four-figure party
- **THEN** that foe's stage actor is lit (`data-speaking="true"`) and every other stage actor — the controlled figure, each companion and the other foes — carries the dialogue listener dim (`data-speaking="false"`, the shared `--actor-dim` brightness); no figure moves, resizes, lifts or changes z; when the step ends every figure returns to its combat state in the same frame

#### Scenario: Selectable figures carry arrow markers
- **WHEN** the step renders with three candidates among five standing figures
- **THEN** exactly the three candidate figures carry an arrow marker centred over their figure box with its bottom 4px × S above the box's top and never inside the top band; the focused marker is a larger filled arrow and an unfocused one an outlined arrow, each showing the digit of its item in the frame's server order when that digit is 1–9; an AREA member already selected adds a check mark; a non-candidate figure carries no marker

#### Scenario: A group position lights the whole group
- **WHEN** the step focuses the `all-enemies` group position with three standing foes
- **THEN** all three foes are lit with the focused arrow and the focused highlight together, every party figure is dimmed, and the prompt and the announcement name 全體敵人 and its size 3

#### Scenario: The focus highlight follows the motion level
- **WHEN** the step focuses a foe at `full`, at `reduced`, and at `off`, and when the operating system requests reduced motion
- **THEN** at `full` the lit figure carries a highlight ring that pulses in a steady loop; at `reduced`, at `off` and under the reduced-motion request it carries a static brighter ring and an underline under its arrow with no animation; in every case the focused arrow's filled shape distinguishes the focus without relying on brightness

#### Scenario: The focused target is announced
- **WHEN** the step opens on a foe, the focus moves to an ally, to an off-stage foe, to the `all-allies` group position, and to the AREA confirm position with two members selected
- **THEN** a polite live region inside the card announces, in order, the foe's name and 敵方, the ally's name and 我方, the off-stage foe's name with 敵方 and 場外, 全體我方 with its size, and 施展 with 已選 2 名; it announces only focus and selection changes, never a dim or pulse change

#### Scenario: An off-stage position cues the participant frame
- **WHEN** the step focuses a candidate that no stage figure draws
- **THEN** no stage figure is lit, every stage figure is dimmed, the prompt marks the target 場外, and the participant frame row of that candidate carries the focused-target cue

#### Scenario: Pointer hit areas exist only during the step
- **WHEN** the step is open, and after it ends
- **THEN** during the step each candidate figure has one hit area over its figure box and its arrow marker that take a pointer, and no other part of either portrait anchor does; after the step no hit area, marker or pointer-taking element remains in the portrait anchors

#### Scenario: A reload or reconnect renders the step at rest
- **WHEN** the client mounts, reloads or reconnects, or a panel replacement commits, while the current frame is a stage target step
- **THEN** the collapsed prompt, the dim, the lit set and the markers render in their final state in the commit's frame with no entrance or fade, and at `full` only the steady focus loop runs

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
- **THEN** the portrait anchors carry no focusable element and intercept no pointer events, except the hit areas and arrow markers over selectable figures during the stage target step, and they MAY sit behind the HUD islands, the `choices` anchor, and the command-line row

#### Scenario: The choices anchor is bounded by the stage box
- **WHEN** dialogue mode renders the choice content, taller than the available span allows
- **THEN** the `choices` anchor renders only in dialogue mode, while an exploration card is open, and in combat mode — where it holds the combat command card, whose horizontal placement, width, top-anchored placement and height "The combat command card stands at the stage's dead centre" sets — and otherwise it is horizontally centred on the stage box, at most `min(560px, 40%)` of the stage width wide; in every mode it stands above the portrait anchors, its content vertically centred in and bounded by the part of the stage box between the top band and the scene caption row that stands on the command-line row so it never meets the scene caption or the expanded command line, scrolling internally when its content is taller than that span allows, and it never grows into the top band, the command-line row, or the bottom band

#### Scenario: Interactive anchors never overlap at or above the reference viewport
- **WHEN** the shell renders at 1451x790, and at every larger viewport up to the chrome factor's cap
- **THEN** no interactive stage anchor (`vitals`, `map`, `band-message`, `band-command`, `choices`, `command-line`) overlaps another interactive anchor's content, and the top band's own elements neither overlap one another nor extend into the HUD island anchor region: a band element whose content is variable-width is bounded and truncated rather than sized by its content

#### Scenario: Only transient popovers may enter the band region
- **WHEN** a transient popover is opened from a top-band element, and when a surface that permanently occupies vertical space is proposed for the band
- **THEN** the transient popover MAY overlay the island anchors while open, provided it does not change the band's own rendered box and closes on Escape and on outside activation, and a surface that permanently occupies vertical space is not introduced into the band this way

### Requirement: The combat command card stands at the stage's dead centre
While the committed mode is `combat`, the client SHALL present the same `#action-dock` element as one narrow card in the stage's `choices` anchor, framed like the stage's other choice cards, with the band's command region collapsed. The card's horizontal centre SHALL be the stage's horizontal centre in every combat state; its width SHALL follow the gap on the party side; and it SHALL NOT cover a foe name plate, foe gauge or focused-target cue.

#### Scenario: The width and height follow the stated formulas
- **WHEN** combat renders at 1451x790 and at 1600x900
- **THEN** the card's width is `clamp(224px × S, 2 × (stage centre − party edge − 16px × S), 280px × S)` (±1px), where S is the desktop chrome factor and the party edge is the right edge of the controlled figure's box as the uncompressed companion line-up places it; its top is the `choices` anchor's top, its bottom stands at least 8px × S above the foe name-plate line, its height is the smaller of 400px × S and that span, and it MAY stand over foe art or the margin of the controlled figure's box

#### Scenario: The card is at dead centre for every party size and foe count
- **WHEN** combat renders at 1451x790 and at 1600x900 with one, two, three and five active foes, each with a solo player, a four-figure party (the player and three companions) and a five-figure party
- **THEN** `#action-dock` lies inside the `choices` anchor and its horizontal centre is the stage's horizontal centre (±1px) in every case; no case shifts it left or right of the centre

#### Scenario: The width follows the guaranteed gap on the party side
- **WHEN** combat renders with a solo player, a three-figure party, a four-figure party and a five-figure party at 1451x790 and at 1600x900
- **THEN** the card's width is `clamp(224px × S, 2 × (stage centre − controlled figure's box right edge − 16px × S), 280px × S)` (±1px): 280, 280, 263.6 and 224 at 1451x790 and 308.8, 308.8, 249.8 and 247.0 at 1600x900; with up to four figures the card does not intersect any party figure's box, and with five figures it intersects only the controlled figure's box and by at most 16.5px at 1451x790 and 40.5px at 1600x900

#### Scenario: The card never covers a foe plate, gauge or cue
- **WHEN** combat renders at 1451x790 and at 1600x900 with one, two and three active foes, including while the attack target frame focuses the rearmost foe
- **THEN** the card's bottom edge is at least 8px × S above the top edge of every foe name plate, so it intersects no foe name plate, no foe gauge and no focused-target cue; with one foe it intersects no foe stage actor box either

#### Scenario: The card keeps the stage's other surfaces clear
- **WHEN** combat renders at 1451x790 and at 1600x900 with one and with three active foes and the command line expanded
- **THEN** the card lies inside the stage box below the top band and intersects no `vitals`, `map` (the place card and the participant frame), band, or command-line anchor, and the vitals dock stays visible

#### Scenario: No frame resizes the card
- **WHEN** the player moves at 1451x790 from the combat root through Skills, a category, a group, a skill frame, a master's 威力 scale step and the target step, and separately opens the Forfeit confirmation
- **THEN** the card's rendered box is identical (±1px) in every frame except the stage target step, where it collapses to the target prompt that "The stage target step presents the targets on the stage figures" defines at the same centre, width and top; the row region scrolls inside the card keeping the focused row in view, and the detail strip and the shortcut legend stay at the card's foot

#### Scenario: Every frame lays out in one narrow column
- **WHEN** the combat root, a category, a group, a skill frame, a master's scale step, a SINGLE target frame, an AREA target frame and the Forfeit confirmation render in a 224px × S wide card
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
- **THEN** every key and activation routes through the same keyboard router and dispatch entry as in the band and emits byte-identical payloads; the card adds no key handling of its own, and the only client-side key claim is the stage target step's arrow-key mapping that "Combat targets are picked on the stage figures" defines

#### Scenario: The card enters with combat and never on a reconnect
- **WHEN** the mode live-changes into combat at `full`, at `reduced`, and at `off`, and when the client reloads or reconnects in combat
- **THEN** at `full` the card fades in over 250ms while rising by the small shift, starting once the 120ms flash has played; at `reduced` it only fades, within 150ms and with no delay; at `off`, and on a reload or reconnect, it renders at rest in the commit's frame; in every case its rows take keys and pointer from the commit's frame

#### Scenario: Playback veils the card's body
- **WHEN** a combat round plays by itself and locks the commands, and later the player activates 跳過演出
- **THEN** the waiting cue with its skip control covers the card's body inside the card while the card keeps its box, and the skip ends the round through the existing skip path

### Requirement: Foes stand opposite the player during combat
While the committed mode is `combat`, the `actor-right` anchor SHALL carry a foe line-up: one stage actor for each committed combat participant whose team is the opposing side and whose state is active, in the presenter's order, at most three. When no foe is active the line-up SHALL render nothing.

#### Scenario: Only foes of the opposing side stand on the stage
- **WHEN** more than three foes are active, or party members other than the player are committed
- **THEN** foes beyond the third do not stand on the stage — the participant frame lists them, and no "+N" count is drawn — party members other than the player do not stand on the stage, and the player alone stands in `actor-left`

#### Scenario: The line-up is a depth-staged row that grows leftward
- **WHEN** one, two, or three foes stand
- **THEN** the first foe stands in front, nearest the stage's right edge, and each later foe stands behind the one before it: further toward the stage's centre, overlapping that foe and drawn behind it, smaller, and standing a little higher (up-stage) than it

#### Scenario: Staged sizes follow the reference ratios
- **WHEN** one, two, or three foes are shown
- **THEN** the foes' heights are, front to back, 100%; 90% and 78%; or 80%, 70%, and 61% of the player's stage actor's height, and every later foe shows 46% of its width past the foe in front of it; the front foe stands on the band's upper edge, and each foe behind stands 3.5% of the portrait anchor's height higher than the one in front of it

#### Scenario: The row's inset clears the participant frame
- **WHEN** the line-up renders at 1451x790 and at every larger viewport up to the chrome cap
- **THEN** the row's right inset is the portrait anchor's right inset, grown just enough that the front foe's horizontal centre (its face) lies at least 24px left of the participant frame's column, within the `map` anchor in combat, and no foe's stage actor crosses the stage's vertical centre line or intersects the player's stage actor

#### Scenario: Each foe plate names, gauges, and cues
- **WHEN** a foe stage actor renders
- **THEN** it exposes that participant's portrait reference as a data attribute for tests and for the beat presentation; it shows its display name above its decorative hit-point gauge and distinguishes acting or focused-target presentation with a non-colour cue (during the stage target step, also the arrow marker over the figure); names ellipsize within their plate while retaining full DOM text; and its gauge is a slim track centred under the figure on the scene caption's baseline, above the command-line row, filled to that foe's current hit points (the displayed value while a combat round plays) over its maximum, with a trailing bar that follows a drop after the vitals' trail delay so the damage shows as a gap

#### Scenario: The line-up is decorative art
- **WHEN** the line-up renders
- **THEN** it is hidden from assistive technology, carries no focusable element, intercepts no pointer events outside the stage target step — during that step only the hit areas and arrow markers over selectable foes, which "The stage target step presents the targets on the stage figures" defines, take a pointer — and states no tokens, hit-point numerals, or participant states, which remain the participant frame's

#### Scenario: A playing round holds the line-up to its beats
- **WHEN** a combat round plays by itself, and later ends — by itself or because the player ended it
- **THEN** during the round the line-up stands the foes that were active before the round, in the presenter's order, and a foe leaves it only when its own defeat beat plays; when the round ends the line-up stands the committed active foes

#### Scenario: Mode changes and set changes animate the line-up
- **WHEN** the committed mode live-changes into or out of `combat`, or a foe joins or leaves the active set within combat
- **THEN** entering brings the line-up in — after half the flash's duration it fades in over the actor duration of the client's motion level (350ms at `full`) while each foe slides in from the right, the front foe furthest; leaving fades it out while the foes drift a step to the right; within combat a leaving foe fades out where it stands, a joining foe slides and fades in, and the remaining foes glide to their new places and sizes; every leaving copy is out of reach as "A leaving element is out of reach while it animates out" requires

#### Scenario: Entrances never replay and motion levels hold
- **WHEN** the client mounts in combat, reloads, or reconnects, or the motion level is `reduced` or `off`
- **THEN** mount, reload, and reconnect play no entrance; at `reduced` the line-up only fades, within 150ms, and nothing in it moves or glides; at `off` every change renders its final state in the commit's frame; and no change scrolls the stage or any element that contains it

#### Scenario: One foe stands opposite the player
- **WHEN** a combat snapshot commits one active foe with a catalog portrait at 1451x790
- **THEN** `actor-right` renders one foe stage actor with that image, its bottom edge on the band's top
  edge, its height equal to the player's stage actor's height (±1px), its horizontal centre at least 24px
  left of the participant frame's left edge, a gauge and name under it, and no focusable element

#### Scenario: Three foes stand in depth toward the centre
- **WHEN** a combat snapshot commits three active foes at 1451x790 and at 2560x1440
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

#### Scenario: Foes take the listener dim during the stage target step
- **WHEN** the stage target step is active with two foes standing and the focus on the front foe
- **THEN** the rear foe's stage actor carries the same listener dim as a non-speaking figure in dialogue and the front foe's does not; outside the stage target step no foe is dimmed

### Requirement: The combat participant frame presents the session's participants and their portraits
In combat the shell SHALL render a participant frame as a HUD island in the stage's top-right `map` anchor, where the minimap is hidden in combat, and SHALL NOT place it in either portrait anchor, grouped into the player's side and the opposing side using the committed participants' server-authored team values, in the presenter's order. The frame SHALL NOT invent a field the participant descriptor does not carry.

#### Scenario: Each participant row states its backed values
- **WHEN** a participant renders in the frame
- **THEN** it renders its session token, its display name, its current and maximum hit points as numerals — the current value being, while a combat round plays, the displayed value that `webclient-combat-menu` "A combat round plays beat by beat" defines — and its state

#### Scenario: Non-active states carry an explicit text marker
- **WHEN** a participant's state is not active
- **THEN** it is conveyed by an explicit text marker in addition to any colour

#### Scenario: The frame is the sole numeral surface
- **WHEN** the frame and the foe line-up render together
- **THEN** the frame lists every participant of both sides, including the foes the foe line-up does not stand on the stage, and remains the only surface that states participant tokens, hit points, and states: the foe line-up in `actor-right` carries decorative portraits, names, non-colour acting/target cues and hit-point gauges without numerals

#### Scenario: Long names bound; six rows clear the foe heads
- **WHEN** a display name exceeds the frame's width, or the frame holds six participants at 1451x790 and 2560x1440
- **THEN** the name ends in an ellipsis on screen while its full text stays in the DOM, and the frame's rows are compact enough that a frame of six participants ends above the foe line-up's gauges; at both acceptance sizes its visible content does not cover a standing foe head

#### Scenario: Portraits resolve only through the committed catalog
- **WHEN** a participant's server-authored portrait reference is looked up in the committed art panel's portrait catalog
- **THEN** a resolvable entry renders that entry; an entry that resolves to a placeholder renders a compact initial with its truthful availability state accessible outside the bitmap; an entry whose image URL fails to load renders a compact initial with a localized load-failure state accessible outside the bitmap; and a null reference or an unavailable art panel renders no portrait at all — the client constructs no portrait subject key or URL

#### Scenario: The frame and stage actors alone present the catalog
- **WHEN** the participant frame is mounted
- **THEN** the frame and the stage actors are the only presenters of the portrait catalog, so no separate portrait strip is rendered alongside them

#### Scenario: The frame never competes for focus
- **WHEN** the participant frame renders
- **THEN** it is display-only: it is not a row container, not part of the dock's composite widget, and not a second tab stop — targets are chosen in the stage target step, where a focused or selectable candidate that stands on no stage figure is cued on its frame row

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
- **WHEN** a combat session commits participants at 1451x790 and 2560x1440
- **THEN** the participant frame is a descendant of the `map` anchor, the `actor-right` anchor holds only the foe line-up's stage actors and gauges and no frame row, token, or hit-point numeral, and the frame's visible box intersects neither the bottom band nor the command line

#### Scenario: An off-stage candidate is cued on its frame row
- **WHEN** the stage target step focuses a candidate that no stage figure draws — a fourth foe, a knocked-out foe, or a party participant the line-up does not draw
- **THEN** that participant's frame row carries the focused-target cue (an arrow glyph and a non-colour outline, exposed as `data-target-cue="focus"`), every other selectable off-stage row carries `data-target-cue="selectable"`, the frame stays display-only and outside the tab order, and the cue clears when the step ends

### Requirement: Companion standing portraits line up behind the controlled character in the actor-left anchor
The `actor-left` anchor SHALL render the currently controlled character's standing portrait as the group's rightmost figure with highest baseline z, and SHALL render each companion in committed `party.slots` order to its left, forming an overlapping horizontal row. Each figure SHALL reuse the existing StageActor rendering and remain non-interactive decorative art: no focusable element, and no pointer events outside the stage target step, during which only the hit areas and arrow markers over selectable figures take a pointer.

#### Scenario: Portraits resolve through the catalog
- **WHEN** a companion portrait renders
- **THEN** it resolves from `portrait_ref` through `art.portrait_catalog`, falling back to its display name's initial-letter placeholder when null or unresolved

#### Scenario: Every figure shares one size and ground line
- **WHEN** the lineup renders any number of figures
- **THEN** every figure, including the controlled character, has the same full anchor size and ground line; no progressively smaller scale, lift ramp or depth dimming

#### Scenario: The row compresses to stay in the left half
- **WHEN** the row renders at 1451x790, 1741x948 and 2560x1440, in any mode
- **THEN** horizontal overlap compresses as necessary to keep the row inside the stage's left half, preserving a scaled left gutter; a multi-figure group MAY shift horizontally within that half; in dialogue the group compresses overlap to clear the choice list without resizing figures; zero companions render the existing solo portrait at its standard anchor position; the anchor has `overflow: visible`; and the vitals dock MAY cover the lowest strip of feet, never face or torso

#### Scenario: Visibility follows the mode
- **WHEN** the committed mode is exploration, combat, dialogue, or creation
- **THEN** the lineup is visible in exploration, combat and dialogue, and hidden in creation

#### Scenario: A speaking companion rises in z only
- **WHEN** a non-controlled rendered companion is the active host speaker in dialogue mode or the selected surviving exploration verb-card target, and when that speaking/focus changes or ends
- **THEN** companions use the existing StageActor listener dim otherwise; the speaking companion temporarily receives z above every baseline figure, returning to its exact baseline z when speaking changes or ends, including across possession swaps and lineup count changes; dialogue speaking and exploration focus change only dim and z, never position, lift or size, and remains correct at off/reduced motion; and the controlled figure retains its existing speaking and beat behavior

#### Scenario: No figure crosses the stage's centre
- **WHEN** the lineup and the foe lineup render together
- **THEN** no figure box crosses the stage's horizontal centre, and the foe lineup is unchanged

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
- **THEN** all five equally sized figures render with compressed horizontal overlap inside the left half; in exploration/combat each face is at least partially visible, and in dialogue a speaking companion is brought above the overlapping listeners without moving its slot

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

#### Scenario: The party takes the listener dim during the stage target step
- **WHEN** the stage target step is active for a skill whose candidates include the controlled figure and one companion, with the focus on that companion
- **THEN** that companion's stage actor is lit (`data-speaking="true"`) and every other party figure, the controlled figure included, carries the listener dim; no figure moves, lifts, resizes or changes z for the step, and when the step ends every figure returns to its combat dim state
