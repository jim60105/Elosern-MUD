## ADDED Requirements

### Requirement: The stage target step presents the targets on the stage figures
During the stage target step that "Combat targets are picked on the stage figures" defines, the combat command card SHALL collapse to a target prompt, every stage figure SHALL take the same listener dim that non-speaking figures take in dialogue except the figures of the focused position's lit set, each selectable figure SHALL carry an arrow marker above it, and the focused position SHALL be lit with a highlight that pulses at `full` and stays static at `reduced` and `off`.

#### Scenario: The card collapses to a target prompt
- **WHEN** the stage target step opens at 1451x790 and at 1600x900 with one, two and three standing foes and parties of one, four and five figures
- **THEN** the card keeps its horizontal centre, width and top and its height is at most 136px × S; in `--text-sm` it shows one line with the action's label (with the chosen 威力 label when the skill carries one), 選擇目標 and `Esc 返回`, and one line with the focused position's summary, each ending in an ellipsis when too long; an AREA step adds one chip per group position and the confirm chip, wrapping onto at most two chip rows; the row region is hidden, DOM focus is on `#action-dock`, and the prompt intersects no arrow marker or figure plate (they all stand outside the formation's dead-centre gap)

#### Scenario: Every figure dims except the lit set
- **WHEN** the step focuses one foe among three standing foes with a four-figure party, one foe defeated
- **THEN** that foe's stage actor is lit (`data-speaking="true"`) and every other stage actor — the controlled figure, each companion and the other foes — carries the dialogue listener dim (`data-speaking="false"`, the shared `--actor-dim` brightness) except the defeated foe, which keeps its defeated treatment; the figure plates are never dimmed, because they carry the hit points the choice depends on; no figure moves, resizes, lifts or changes z; when the step ends every figure returns in the same frame to its state before the step — in combat the controlled figure and the foes are undimmed and the companions keep their existing listener dim

#### Scenario: Selectable figures carry arrow markers
- **WHEN** the step renders with three candidates among five standing figures
- **THEN** exactly the three candidate figures carry an arrow marker in their formation marker slot, directly above their plate; the focused marker is a larger filled arrow and an unfocused one an outlined arrow, each showing the digit of its item in the frame's server order when that digit is 1–9; an AREA member already selected adds a check mark; a non-candidate figure carries no marker

#### Scenario: A group position lights the whole group
- **WHEN** the step focuses the `all-enemies` group position with three standing foes
- **THEN** all three foes are lit with the focused arrow and the focused highlight together, every party figure is dimmed, and the prompt and the announcement name 全體敵人 and its size 3

#### Scenario: The focus highlight follows the motion level
- **WHEN** the step focuses a foe at `full`, at `reduced`, and at `off`, and when the operating system requests reduced motion
- **THEN** at `full` the lit figure carries a highlight ring that pulses in a steady loop; at `reduced`, at `off` and under the reduced-motion request it carries a static brighter ring and an underline under its arrow with no animation; in every case the focused arrow's filled shape distinguishes the focus without relying on brightness

#### Scenario: The focused target is announced
- **WHEN** the step opens on a foe, the focus moves to an ally, to a listed fled foe, to the `all-allies` group position, and to the AREA confirm position with two members selected
- **THEN** a polite live region inside the card announces, in order, exactly `目標：<foe name>，敵方`, `目標：<ally name>，我方`, `目標：<foe name>，敵方，場外` (a fled participant still listed), `目標：全體我方，共 <n> 名` and `施展：已選 2 名`; a selected member appends `，已選`, the confirm position with a chosen shorthand reads `施展：<group label>，共 <n> 名` and with nothing chosen `施展：尚未選擇目標`, a SELF step reads `目標：自己`, and when two candidates share a display name each member announcement appends the participant's session token in full-width parentheses (`（e2）`); it announces only focus and selection changes, never a dim or pulse change

#### Scenario: A candidate without a figure is named, not cued elsewhere
- **WHEN** the step focuses a listed candidate that no stage figure draws (a fled participant)
- **THEN** no stage figure is lit, every stage figure is dimmed, and the prompt and the announcement name the target with 場外; no other surface carries a cue

#### Scenario: Tooltips and the step coexist
- **WHEN** a plate's condition tooltip is open and the step starts, and during the step the pointer rests on a plate's glyph
- **THEN** starting the step closes the tooltip and moves keyboard focus that was inside the plates group to `#action-dock`, and during the step hovering a glyph opens its tooltip without moving the target focus or taking a target's pointer action

#### Scenario: Fallen looks never read as a target-step dim
- **WHEN** a step dims a standing foe while a defeated foe and a downed companion stand beside it
- **THEN** the dimmed foe keeps its colour, pose and opacity and carries no mark or fallen text, while the defeated foe keeps its collapse, seal and 已擊破 and the companion its kneel and 倒地, so every pair differs by shape and text, not by brightness alone

#### Scenario: Pointer hit areas exist only during the step
- **WHEN** the step is open, and after it ends
- **THEN** during the step each candidate figure has one hit area over its figure box and its arrow marker takes a pointer, and no other part of either portrait anchor does; after the step no hit area, marker or pointer-taking element remains

#### Scenario: A reload or reconnect renders the step at rest
- **WHEN** the client mounts, reloads or reconnects, or a panel replacement commits, while the current frame is a stage target step
- **THEN** the collapsed prompt, the dim, the lit set and the markers render in their final state in the commit's frame with no entrance or fade, and at `full` only the steady focus loop runs

## MODIFIED Requirements

### Requirement: The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces
The WebClient SHALL render as a full-bleed stage filling the viewport, layered: the scene backdrop, the portrait anchors, the HUD islands, the bottom band, and the command line topmost among persistent ones. HUD surfaces SHALL be placed by named stage anchors — `vitals`, `map`, `actor-left`, `actor-right`, `band-message`, `band-command`, `choices`, `presence`, `plates`, and `command-line` — and SHALL NOT sit inside a page-scrolling container that can push a required surface out of view.

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
- **THEN** the `actor-left` anchor carries the controlled character's stage actor — the current roster character's portrait, or the possessed companion's while the possession banner is available — with the committed party's companion stage actors lined up behind it as "Companion standing portraits line up behind the controlled character in the actor-left anchor" defines, each with the truthful placeholder when no image exists; in combat these figures stand at the boxes "Combat figures stand in a shared-scale formation" sets

#### Scenario: The actor-right anchor's content follows the committed mode
- **WHEN** the committed mode is `dialogue` with an available `dialogue` panel whose host identity does not already join to a committed party or controlled lineup figure, and later `combat` with at least one foe active or while a round that ended the fight still plays as "Combat beats are choreographed on the stage at the motion level" defines, and later any other state
- **THEN** the `actor-right` anchor carries the dialogue host's stage actor in the first state, every active foe at the boxes that "Combat figures stand in a shared-scale formation" sets in the second, and no content in every other state; in combat the portrait anchors span the stage so formation boxes are stage coordinates, and no figure enters the dead-centre gap that requirement keeps clear; every stage actor follows "Stage actors present the player and the dialogue host with a speaking state"

#### Scenario: The portrait anchors are non-interactive art
- **WHEN** any stage actor renders
- **THEN** the portrait anchors carry no focusable element and intercept no pointer events, except the hit areas over selectable figures during the stage target step, and they MAY sit behind the HUD islands, the `choices` anchor, and the command-line row

#### Scenario: The choices anchor is bounded by the stage box
- **WHEN** dialogue mode renders the choice content, taller than the available span allows
- **THEN** the `choices` anchor renders only in dialogue mode, while an exploration card is open, and in combat mode — where it holds the combat command card, whose horizontal placement, width, top-anchored placement and height "The combat command card stands at the stage's dead centre" sets — and otherwise it is horizontally centred on the stage box, at most `min(560px, 40%)` of the stage width wide; in every mode it stands above the portrait anchors, its content vertically centred in and bounded by the part of the stage box between the top band and the scene caption row that stands on the command-line row so it never meets the scene caption or the expanded command line, scrolling internally when its content is taller than that span allows, and it never grows into the top band, the command-line row, or the bottom band

#### Scenario: Interactive anchors never overlap at or above the reference viewport
- **WHEN** the shell renders at 1451x790, and at every larger viewport up to the chrome factor's cap
- **THEN** no interactive stage anchor (`vitals`, `map`, `band-message`, `band-command`, `choices`, `command-line`) overlaps another interactive anchor's content, and the top band's own elements neither overlap one another nor extend into the HUD island anchor region: a band element whose content is variable-width is bounded and truncated rather than sized by its content

#### Scenario: Only transient popovers may enter the band region
- **WHEN** a transient popover is opened from a top-band element, and when a surface that permanently occupies vertical space is proposed for the band
- **THEN** the transient popover MAY overlay the island anchors while open, provided it does not change the band's own rendered box and closes on Escape and on outside activation, and a surface that permanently occupies vertical space is not introduced into the band this way

#### Scenario: The plates layer is a named stage layer
- **WHEN** combat renders its formation
- **THEN** the `plates` layer is a stage-sized, non-scrolling layer above the portrait anchors and below the HUD islands, the band, the `choices` anchor and the command line, holding only the figure plates

### Requirement: The combat command card stands at the stage's dead centre
While the committed mode is `combat`, the client SHALL present the same `#action-dock` element as one 264px × S wide card in the stage's `choices` anchor, framed like the other choice cards, centred on the stage's horizontal centre in every combat state, inside the dead-centre gap the combat formation keeps clear; the band's command region SHALL collapse.

#### Scenario: The card is at dead centre with a fixed width
- **WHEN** combat renders at 1451x790 and at 1600x900 for parties of one, three and five figures against one, four, eight and the maximum (16 minus the party count) foes
- **THEN** `#action-dock` lies inside the `choices` anchor, its horizontal centre is the stage's horizontal centre (±1px), its width is 264px × S (±1px: 264 and 291.1), and it is the same in every case

#### Scenario: The card never covers the formation
- **WHEN** combat renders any of those cases, including during the entry into combat and while a foe joins or leaves
- **THEN** the card intersects no figure box (at rest or at the farthest point of a beat gesture), no figure plate and no marker slot, because every one of them stands outside the card's columns

#### Scenario: The width and height follow the stated rules
- **WHEN** combat renders at 1451x790 and at 1600x900
- **THEN** the card's top is the `choices` anchor's top and its height is the smaller of 400px × S and the anchor's span (from the top band's inset to 8px × S above the scene caption row), so the card is 400px tall at 1451x790 (anchor 58–472 → 414px) and 441.1px at 1600x900

#### Scenario: The card keeps the stage's other surfaces clear
- **WHEN** combat renders at 1451x790 and at 1600x900 with the command line expanded
- **THEN** the card lies inside the stage box below the top band and intersects no `vitals`, band, or command-line anchor, and the vitals dock stays visible

#### Scenario: No frame resizes the card
- **WHEN** the player moves at 1451x790 from the combat root through Skills, a category, a group, a skill frame, a master's 威力 scale step and the target step, and separately opens the Forfeit confirmation
- **THEN** the card's rendered box is identical (±1px) in every frame except the stage target step, where it collapses to the target prompt that "The stage target step presents the targets on the stage figures" defines at the same centre, width and top; the row region scrolls inside the card keeping the focused row in view, and the detail strip and the shortcut legend stay at the card's foot

#### Scenario: Every frame lays out in one narrow column
- **WHEN** the combat root, a category, a group, a skill frame, a master's scale step, a SINGLE target frame, an AREA target frame and the Forfeit confirmation render in the 264px × S card
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

### Requirement: Combat figures stand in a shared-scale formation
While the committed mode is `combat`, or while a round that ended the fight still plays, the stage SHALL place the controlled figure, every drawn companion and every foe that has not fled, fallen ones included (up to 16 minus the party count, in presenter order), at the boxes that "Combat formation geometry is one pure shared-scale function" returns. Every figure on both sides SHALL be drawn at one scale at every moment; exploration and dialogue SHALL keep their standing positions.

#### Scenario: Every active foe stands
- **WHEN** a combat snapshot commits one, three, five, eight and fifteen foes that have not fled, some of them knocked out or defeated, with a solo player at 1451x790
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

#### Scenario: Foes take the listener dim during the stage target step
- **WHEN** the stage target step is active with two foes standing and the focus on the front foe
- **THEN** the other foe's stage actor carries the same listener dim as a non-speaking figure in dialogue and the focused foe's does not; a fallen foe keeps its fallen treatment whether lit or not; outside the stage target step no standing foe is dimmed

#### Scenario: Only the step's hit areas take a pointer
- **WHEN** the stage target step is open, and after it ends
- **THEN** during the step each candidate figure has one hit area over its figure box that takes a pointer, and nothing else in the portrait anchors does; after the step no hit area remains

### Requirement: Companion standing portraits line up behind the controlled character in the actor-left anchor
The `actor-left` anchor SHALL render the currently controlled character's standing portrait as the group's rightmost figure with highest baseline z, and SHALL render each companion in committed `party.slots` order to its left, forming an overlapping horizontal row outside combat; in combat they stand at the formation's boxes. Each figure SHALL reuse StageActor rendering and stay non-interactive decorative art: no focusable element, and no pointer events except the stage target step's hit areas.

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

#### Scenario: The party takes the listener dim during the stage target step
- **WHEN** the stage target step is active for a skill whose candidates include the controlled figure and one companion, with the focus on that companion
- **THEN** that companion's stage actor is lit (`data-speaking="true"`) and every other party figure, the controlled figure included, carries the listener dim; no figure moves, lifts, resizes or changes z for the step, and when the step ends every figure returns to the state it had before the step (in combat the controlled figure undimmed and the companions in their existing listener dim)
