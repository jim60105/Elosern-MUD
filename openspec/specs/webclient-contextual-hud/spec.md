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
The WebClient SHALL render as a full-bleed stage filling the viewport, layered bottom-up: the scene backdrop, the portrait anchors, the HUD islands, the bottom band, and the command line topmost among the persistent surfaces. HUD surfaces SHALL be placed by named stage anchors — `vitals`, `map`, `actor-left`, `actor-right`, `band-message`, `band-command`, `choices`, and `command-line` — and SHALL NOT sit inside a page-scrolling container that can push a required surface out of view.

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
- **WHEN** the shell renders at 1451x790 and the player moves through the exploration scene overview, a target's verb popover, the waiting frame, an empty pane host, the deepest combat frame, and a dialogue exchange with four picks
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
- **THEN** the `actor-left` anchor carries the controlled character's stage actor — the current roster character's portrait, or the possessed companion's while the possession banner is available — with the committed party's companion stage actors lined up behind it as "Companion standing portraits line up behind the controlled character in the actor-left anchor" defines, each with the truthful placeholder when no image exists

#### Scenario: The actor-right anchor's content follows the committed mode
- **WHEN** the committed mode is `dialogue` with an available `dialogue` panel whose host identity does not already join to a committed party or controlled lineup figure, and later `combat` with at least one foe active or while a round that ended the fight still plays as "Combat beats are choreographed on the stage at the motion level" defines, and later any other state
- **THEN** the `actor-right` anchor carries the dialogue host's stage actor in the first state, the foe line-up that "Foes stand opposite the player during combat" defines in the second, and no content in every other state; the foe line-up MAY extend leftward beyond the anchor's own box, within the bounds that requirement sets, and SHALL NOT cross the stage's horizontal centre, which the companion line-up's figures also never cross; every stage actor follows "Stage actors present the player and the dialogue host with a speaking state"

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

### Requirement: Surface visibility is gated by the committed game mode
The shell SHALL expose the committed mode on the stage root as `data-elosern-mode`, and surface visibility SHALL be derived from that single attribute. A surface hidden for the current mode SHALL be removed from rendering with `display:none` — never dimmed, never merely visually hidden — so it leaves the accessibility tree and the tab order, excepting only the two hold states defined in the scenarios below. The matrix SHALL be:

```text
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
```

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

### Requirement: The scene backdrop renders the art payload truthfully behind the stage
The stage backdrop SHALL render the committed `art` panel's scene: the same-origin image with cover-style cropping when the scene status is `done`; the previously rendered image visibly dimmed and labelled `目前場景圖片生成中` when the scene is pending and a prior image exists; and the mode's gradient stage otherwise — for a missing, failed, or invalid asset, a pending scene with no prior image, or an unavailable `art` panel.

#### Scenario: The backdrop never lies about the scene
- **WHEN** any scene renders on the backdrop
- **THEN** the backdrop presents no invented image as authoritative and no stale image as current

#### Scenario: A bundled sample is captioned inside one status badge
- **WHEN** a bundled decorative sample accompanies a missing, pending, or unavailable fallback
- **THEN** it appears only with a visible caption distinguishing it from an actual scene image, while retaining the authoritative missing/pending/unavailable label; the sample caption and that label share one status badge, so the stage shows at most one status badge at a time, and the badge shows no raw placeholder kind code and no error-styled (dashed seal-red) frame; samples never enter the art catalog or change its status, and disappear when an actual or labelled prior scene renders

#### Scenario: Portrait samples stay labelled and subordinate
- **WHEN** a decorative portrait sample renders, an available committed player-roster portrait exists, or a portrait image fails to load
- **THEN** the sample is labelled separately from the current subject, the available committed player-roster portrait takes precedence, and a load failure returns to an explicitly labelled sample instead of attributing that sample to the player

#### Scenario: The combat hold never holds scene identity
- **WHEN** the combat hold of "Surface visibility is gated by the committed game mode" is playing
- **THEN** the backdrop MAY keep presenting the combat gradient stage (and the combat sample wash where a degraded scene carries one), yet it does not hold the pre-terminal scene's identity: a newer committed scene image, pending state, or truthful degradation follows the rules above beneath the held decoration at its commit, and the scene caption row names the newly committed scene, never the held combat one

#### Scenario: All required labels exist as text outside the bitmap
- **WHEN** any scene renders
- **THEN** the scene label, its alternative text, and any truthful placeholder label are rendered as text outside the bitmap, so no required information exists only inside an image; the gradient stage differs per mode (exploration, dialogue, combat) and carries an inset vignette

#### Scenario: Backdrop captions never meet the band or dock
- **WHEN** the backdrop's own floating caption elements — the status badge, the `目前場景圖片生成中` pending notice, the scene label and alternative-text captions, and the full-view control — render at 1451x790 and at every larger viewport up to the chrome cap
- **THEN** none of them overlaps the bottom band's, the action dock's, or the command line's rendered content, extending the sibling stage requirement's general anchor non-overlap invariant to these backdrop-internal captions, which sit outside the named stage anchors but are absolutely positioned within the same full-bleed stage

#### Scenario: The caption row stands only for a real scene image
- **WHEN** a `done` scene image or the dimmed prior image of a pending scene is on the stage, and when the scene is missing, failed, invalid, or unavailable
- **THEN** the scene caption row renders only in the first case and not in the second, whose truthful label the status badge already states; within the row the alternative text is omitted when it is identical to the scene label, and the full-view control is an icon button whose accessible name is `開啟場景全圖`

#### Scenario: The caption row sits centred on the stage's lower edge
- **WHEN** the scene label, the alternative text, the pending notice, and the full-view control render, with or without the foe line-up standing in combat
- **THEN** they render as one caption row on the stage box's lower edge, standing just above the command-line row docked on the band's top edge, centred in the open stage between the `actor-left` and `actor-right` anchor boxes — or, while the foe line-up stands in combat, between the `actor-left` anchor box and the line-up's leftmost foe, until a leaving line-up has faded — so no portrait anchor (which paints above the backdrop), no foe, and no other HUD surface covers any part of it in any mode

#### Scenario: The caption row stays one line tall
- **WHEN** the row is too narrow for both the alternative text and the label, or a label or alternative text is longer than the row
- **THEN** the alternative text gives way before the scene label, the long text ends in an ellipsis on screen while its full text stays in the DOM, the row stays one line tall, and the dialogue choice list stops above the row

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
  command line's rendered bounding box at 1451x790 or at any larger viewport up to the chrome cap

#### Scenario: The scene label, alt text, and full-view control clear the dock at both viewports
- **WHEN** the scene label, alternative-text caption, pending notice, or full-view control render above
  the band
- **THEN** each one's rendered bounding box stays above the bottom band's top edge and above the
  command-line row, at 1451x790 and at every larger viewport up to the chrome cap

#### Scenario: The scene caption stands on the stage floor between the portraits
- **WHEN** the scene label, alternative text, and full-view control render with the command line expanded
  at 1451x790 and at every larger viewport up to the chrome cap
- **THEN** their caption row's bottom edge lies at most 16px above the command-line row's top edge, the
  row is horizontally centred between the `actor-left` and `actor-right` anchor boxes (±1.5px), and each
  part lies between those boxes with no other surface painted over it

#### Scenario: The scene caption clears the foe line-up
- **WHEN** a combat snapshot commits one, two, and three active foes with the command line expanded at
  1451x790 and at every larger viewport up to the chrome cap
- **THEN** the caption row lies between the `actor-left` anchor box and the leftmost foe's box, horizontally
  centred between them (±1.5px), with no foe painted over any of its parts

### Requirement: The message window presents the current response one page at a time in the band's message region
The narrative SHALL render as a message window filling the bottom band's message region — the left two thirds of the band, or the whole band in dialogue mode, at the band's fixed height — drawn with the reference's caption panel treatment. The window SHALL never grow into the stage or change size with its content, SHALL present exactly one page of the current response at a time in every mode, and SHALL NOT present earlier responses.

#### Scenario: The window wears the reference caption panel chrome
- **WHEN** the message window renders
- **THEN** it is drawn with the reference's caption panel treatment: charcoal panel fill, a hairline border, shared radius and restrained shadow

#### Scenario: Paging follows the narrative and combat contracts
- **WHEN** the window presents the current response, including while that response carries a combat round the client presents
- **THEN** pages follow `webclient-input-narrative` and are revealed as its typing requirement defines — or, for a presented combat round, as that round's beat pages followed by the response's remaining lines, as `webclient-combat-menu` "A combat round plays beat by beat" defines — and earlier responses are not presented: they remain readable in the full-log surface

#### Scenario: The clear layer is the one paging exception
- **WHEN** a new response replaces the previous one
- **THEN** the previous page MAY remain only as an opaque layer over the new page that fades out within the clear duration of the client's motion level (at most 150ms, and none at `off`), carries no focusable element, and is outside the accessibility tree and pointer hit-testing from the moment the new response starts

#### Scenario: Page typography is bounded at the reference size
- **WHEN** page text renders at the 1451x790 reference size and the default prose scale
- **THEN** it is set in the bundled monospace reading face — the same Jim Mono TC family the monospace type role ships — at 18px, scales once with the desktop chrome factor and with the client's prose scale, and holds at most 42 CJK characters per line in every mode, including the whole-band width of dialogue mode

#### Scenario: The control strip carries the marker and the log control
- **WHEN** any page renders
- **THEN** the window's lower edge keeps a control strip in which no page text renders, holding a page marker and, at its right end, a labelled `日誌` control beside the command-line toggle

#### Scenario: The marker names the page state decoratively
- **WHEN** the on-screen page is fully shown, typing, or a combat round plays by itself
- **THEN** the marker renders only while the page is fully shown and is absent while it types and while a combat round plays by itself; when rendered it reads `▼` while the current response has further pages and `■` on its last page; it is decorative (hidden from assistive technology) and blinks only through the client's motion tokens, so reduced motion stops the blink

#### Scenario: An oversize page scrolls without growing the window
- **WHEN** a page is taller than the window's text area
- **THEN** it scrolls inside the text area; it is never truncated and never grows the window

#### Scenario: The log control and scroll-up open the full log
- **WHEN** the player activates the `日誌` control, or scrolls up over a page that has nothing left to scroll up
- **THEN** the full-log surface opens in one action; its content, markup renderer, focus trap, Escape close, focus restore to the opening control, and opening at its latest line are unchanged

#### Scenario: The window carries no reading chrome beyond the plate
- **WHEN** the window renders in any mode
- **THEN** it renders no unread indicator, no jump-to-latest control, and no head row other than the dialogue name plate; in creation mode the window, its marker, and the `日誌` control are hidden with the message region

#### Scenario: The dialogue name plate names the host truthfully
- **WHEN** the committed mode is `dialogue` and the committed `dialogue` panel is available
- **THEN** the window carries a name plate above its text area, naming the host with the panel's `display_name` plus ` ‧ 羈絆 <stage>` only when `bond_stage` is non-null; below the plate the text area presents the current response's pages — the session line as the narrative delivered it, paged and typed like any response, with no separate reply box, no rows, no avatar, and no text removed or rewritten from the narrative lines; the window carries no choice, free-dialogue, or exit row: those are the dialogue choice list's

#### Scenario: A transient panel shows no plate, and reader state drives the choice list
- **WHEN** mode is `dialogue` but the panel is unavailable (the transient window between a clear seam and its commit)
- **THEN** the window renders no name plate, and the window makes known to the shell, from its own reader state and never from narrative prose, whether the current response's last page is on screen, fully shown, with no pending action mark — the moment the dialogue choice list waits for

#### Scenario: The window keeps the message region's box
- **WHEN** the current response holds more text than one page and new lines keep arriving
- **THEN** the window keeps the message region's box — the band's height and two thirds of its
  width, or the whole band in dialogue mode — and never expands into the stage

#### Scenario: One page of the current response is shown
- **WHEN** the log holds three responses and the latest one fills two pages
- **THEN** the window shows only the first page of the latest response, and once the clear transition
  has finished no line of the two earlier responses is rendered in the window

#### Scenario: The page measure is bounded at the reference size
- **WHEN** the stage renders at 1451x790 with the default prose scale and a long prose response, in exploration mode and in dialogue mode with the panel transiently unavailable
- **THEN** the page text's computed font size is 18px (±0.5px) in the bundled monospace reading face and no rendered text line holds more
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
- **WHEN** mode `dialogue` commits with host `灰婆婆`, `bond_stage` `親睦`, and a greeting long enough for two pages at 1451x790
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
The surfaces placed in the stage's island anchors SHALL render as floating HUD islands: a translucent panel fill, a backdrop blur, a hairline border, the shared corner radius, and the shared drop shadow, each island a separate box separated by the anchor's gap — never a single boxed column card and never an opaque `<aside>` stacked in a layout column. No reference panel and no portrait anchor content SHALL be placed in either island anchor.

#### Scenario: The vitals anchor is one dock
- **WHEN** the shell renders the stage box's lower left
- **THEN** it is the vitals dock that "The vitals dock stands at the stage's lower-left above the band" defines: it carries the condition icon row and the vitals bars as one dock, and carries neither a character head card nor a portrait catalog strip nor a party quickbar

#### Scenario: The map anchor stacks its islands in one order
- **WHEN** the shell renders the `map` anchor
- **THEN** it carries, in this order, the place card, the minimap island, the objective line, the combat participant frame while it is mounted, and the title ballot menu while it is mounted, each present only while its own requirement renders it

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
- **THEN** exploration renders the place card, the minimap island, the objective line, and the title ballot menu in that order in the `map` anchor, and combat renders the place card above the participant frame there with no minimap and no objective line

#### Scenario: The island stack carries its amendments
- **WHEN** the `place-card-relocation` and `vitals-bar-redesign` amendments apply to this requirement
- **THEN** the party quickbar is removed with this change

### Requirement: The vitals island is shown only in combat or while a vital or a condition needs attention
The HUD SHALL show the vitals dock, comprising the condition icon row and vitals bars, only while at least one of these holds for the committed state: the committed mode is `combat`; the derived low-HP presentation state is true; any `status.resources` vital (hp, mp, sp) carries a numeric `current` below its numeric `maximum`; or `status.conditions` carries an entry whose `severity` is `warning`, `harmful`, or `critical` and whose `provenance.kind` is `non_equipment`, `mixed`, or `unknown`.

#### Scenario: Benign or unreadable entries never reveal the dock
- **WHEN** a beneficial or informational condition (including a passive skill-owned combat modifier), or an entry with a missing or unknown severity, is committed at full vitals
- **THEN** it does not independently reveal the dock, and missing or malformed required provenance is rejected under the status protocol contract rather than interpreted as an equipment exemption

#### Scenario: An equipment-only condition never reveals the dock on its own
- **WHEN** a proven equipment-only condition is committed at full vitals outside combat
- **THEN** it does not independently reveal the dock, regardless of adverse severity

#### Scenario: A visible dock renders every condition
- **WHEN** the dock is visible
- **THEN** its condition icons render every committed condition, regardless of severity or provenance

#### Scenario: A false rule hides the dock completely
- **WHEN** the committed revision turns the rule false
- **THEN** from that moment the dock leaves the accessibility tree, the tab order, and pointer hit-testing, and once its exit transition has finished it is `display:none` and contributes no visible box; the dock enters and leaves with the existing fade and 12px slide at the client's motion level, and at `off` it shows and hides in the same frame as the commit

#### Scenario: The rule is derived client-side from committed data only
- **WHEN** the dock's visibility rule is evaluated
- **THEN** it is derived client-side from the committed mode and status panel, including server-authored condition provenance, and never uses narrative text, action-result predictions, local equipment inference, an extra server request, or a timer; a vital absent from the payload or carrying non-numeric fields does not count as below its maximum

#### Scenario: Mode gates and panel availability outrank the data rule
- **WHEN** the mode is dialogue or creation with depleted resources or independently adverse conditions, the `status` panel is unavailable (including in combat), or the mode leaves dialogue
- **THEN** the existing visibility matrix keeps the dock hidden in dialogue and creation, an unavailable `status` panel renders no dock, and leaving dialogue reapplies the data rule to the then-committed state

#### Scenario: The hidden dock keeps trailing-bar memory
- **WHEN** the dock has been hidden and the first committed revision lowers a vital from full
- **THEN** the dock shows with the trailing bar lagging from the previously committed ratio exactly as an always-visible dock would

#### Scenario: Hiding the dock rescues focus per its trigger
- **WHEN** a committed revision turns the rule false while focus is inside the dock, or a mode change hides it
- **THEN** focus moves to the action dock before hiding through the existing focus-restore path, and mode changes retain their existing mode-specific focus home

#### Scenario: Full health outside combat hides the island
- **WHEN** the committed mode is exploration, every committed vital's `current` equals its `maximum`, and `status.conditions` is empty
- **THEN** the vitals dock is absent from the accessibility tree and tab order, and after any exit transition it is hidden with `display:none` and no bars, numerals, icons, or low-HP marker visible

#### Scenario: A vital below its maximum shows the island
- **WHEN** a committed revision in exploration carries `mp` at 40 of 60 with no condition
- **THEN** the dock renders every vital's icon, label, and on-track `current / maximum` numerals

#### Scenario: A condition shows the island at full health
- **WHEN** an exploration revision carries full vitals and a harmful condition with non-equipment provenance
- **THEN** the dock renders its bars and condition icon

#### Scenario: A beneficial-only condition keeps the island hidden at full health
- **WHEN** an exploration revision carries full vitals and only beneficial conditions, including a passive skill-owned combat-modifier row
- **THEN** the dock stays hidden with `display:none`, none of its condition icons is visible or focusable, and no enter transition plays

#### Scenario: Visible island renders every condition chip
- **WHEN** the dock is visible because a vital is below its maximum and committed conditions include beneficial, informational, and equipment-only adverse entries
- **THEN** its row renders every entry without changing severity or removing equipment-origin icons

#### Scenario: Combat always shows the island
- **WHEN** available status commits in combat with every vital full and no condition or only equipment-only conditions
- **THEN** the vitals dock renders

#### Scenario: The first hit from full health keeps its trailing bar
- **WHEN** the dock is hidden at full health with only equipment-only adverse conditions and the next same-epoch committed revision lowers `hp`
- **THEN** the dock renders, hp fill shows the new ratio, and the trailing bar starts from the previously committed full ratio

#### Scenario: Focus is rescued before the island hides
- **WHEN** focus is inside the dock outside combat with full vitals and a revision removes the final independently adverse condition, leaving only beneficial or equipment-only adverse entries
- **THEN** focus moves to the action dock before the dock is hidden, with no focus lost to the document body

#### Scenario: Every adverse severity respects the equipment exemption
- **WHEN** separate exploration fixtures have full resources and only a proven equipment-origin warning, harmful, or critical condition
- **THEN** each fixture keeps the dock hidden while its original severity and condition remain available in status

#### Scenario: Mixed and independent sources retain attention
- **WHEN** full-health exploration has an equipment-only condition plus an independent adverse condition, or one adverse condition with mixed provenance
- **THEN** the dock is visible and displays all conditions, including the equipment-only row

#### Scenario: Unknown origin is not an equipment exemption
- **WHEN** full-health exploration carries an adverse condition with valid unknown provenance
- **THEN** the dock reveals without inventing an equipment source

#### Scenario: Equip and unequip follow accepted canonical updates
- **WHEN** synthetic equipment induces a threshold warning at full resources, a committed equip update arrives, and a later committed unequip update removes the equipment-dependent warning
- **THEN** both revisions keep the dock hidden, condition membership and source detail match each accepted revision, and an independent same-definition buff would continue to reveal the dock after unequip

#### Scenario: Same-code warning changes provenance on a state commit
- **WHEN** full-health exploration has an equipment-dependent threshold warning and a later committed stored-state change makes the same warning match independently
- **THEN** the dock reveals on that accepted revision although condition code and severity are unchanged, and the replacement provenance reports its independent or mixed source

#### Scenario: Stale updates cannot restore old attention
- **WHEN** an accepted status revision changes a warning from mixed to equipment-only and an older revision or retired-epoch message arrives
- **THEN** the old message is discarded and cannot restore the old provenance or reveal the hidden dock

#### Scenario: Dialogue and creation keep their existing gates
- **WHEN** mode is dialogue or creation with available depleted resources and an independent critical condition
- **THEN** the vitals dock remains hidden through the mode gate, and returning to exploration reveals it from the committed data without a new attention request

#### Scenario: Unavailable status does not fabricate attention
- **WHEN** status commits its unavailable form in exploration or combat after previously carrying independent adverse conditions
- **THEN** no vitals dock, old condition icon, or fabricated resource is rendered, while other registered presentation remains usable

### Requirement: Vitals read as one numeral readout over three thin trailing-bar lines
Each of hp, mp, and sp SHALL render as one thin trailing-bar line, the three laid almost edge to edge — parted by a hairline seam, in hp, mp, sp order from the top — under one numeral readout row that states, in the same order, each gauge's icon and its `current / maximum` numerals — or, for hp while a combat round plays, the displayed value that `webclient-combat-menu` "A combat round plays beat by beat" defines.

#### Scenario: Icons, labels, and numerals carry the readings
- **WHEN** the readout renders
- **THEN** the icons are three distinct shapes in their gauge's hue, so the readings are told apart without colour; each gauge's Traditional Chinese label (生命, 魔力, 耐力) is its reading's accessible name and is not rendered as visible text; the 危險 low marker renders with the hp reading; the current value leads in the brightest paper ink at tabular figures and the maximum recedes a step, every value in a contrast that keeps it legible over the dock, so no vital state is conveyed by the coloured fill alone

#### Scenario: The three lines fan out as one instrument
- **WHEN** the three lines render
- **THEN** they do not read as square boxes: each tapers to a point at its far end and runs a little shorter than the one above it, so the set fans out rather than ending on one hard edge; the readout and the three lines together occupy well under half the previous vitals island's row block; and the sp fill carries a non-colour texture distinguishing it from the hp and mp fills

#### Scenario: The trailing bar is decorative and truthful
- **WHEN** the trailing bar renders
- **THEN** it is decorative — hidden from the accessibility tree, carrying no accessible name, and conveying nothing the numerals do not already carry on the same revision; it renders no value that was not a previously displayed ratio of that same gauge, where a displayed ratio comes only from the committed `status` or from a committed beat's `hp_after` during a round's playback; it is not interpolated or extrapolated from narrative text or an action result

#### Scenario: The trailing bar's motion is token-gated
- **WHEN** the epoch changes, the reduced-motion block applies, or the motion level is `full`
- **THEN** the bar resets to the current ratio when the epoch changes, so no trail is drawn across a reconnect; its motion is token-gated so the reduced-motion block disables it; and at `full` it starts following a drop 300ms after the fill moves

#### Scenario: A low vital is marked twice
- **WHEN** a vital falls to or below the client's display threshold
- **THEN** it is marked by both a recolour and an explicit text marker, never by the recolour alone

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
The client SHALL derive a low-HP presentation state from the committed `status.resources.hp` ratio alone, against a single display-only threshold, and SHALL expose it on the stage root through the shell's existing low-HP hook so the stage renders its red vignette and the hp fill renders its pulse.

#### Scenario: No server field expresses low health
- **WHEN** the client evaluates or exposes the low-HP state
- **THEN** the threshold is a presentation constant: no server field, trait, or condition expresses "low health", and the client requests none, invents none on the wire, and never treats the derived state as canonical

#### Scenario: The state is never load-bearing
- **WHEN** any hp value renders
- **THEN** the numerals and the low text marker convey the same information at every value, so a viewer who perceives neither the vignette nor the pulse loses nothing

#### Scenario: An unavailable panel is not low HP by default
- **WHEN** the `status` panel is unavailable
- **THEN** the state is false rather than true by default

#### Scenario: The stage hook's motion is token-gated
- **WHEN** the reduced-motion block applies while the state is true
- **THEN** the pulse and the vignette transition are token-gated so the block disables the motion while the marker and the numerals still apply

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
The active conditions SHALL NOT render as a chipped island with a background window, header, or border. Each entry in `status.conditions` SHALL instead render as a standalone small icon in a row directly above the vitals readout, carrying only its per-severity shape glyph. The row SHALL carry no panel fill, no backdrop blur, and no `狀態` label.

#### Scenario: Severity glyphs carry direction without colour
- **WHEN** condition icons render
- **THEN** the five severities each map to a distinct glyph so no two are separated by colour alone, with the beneficial and harmful directions readable from the glyph itself

#### Scenario: Detail lives in the tooltip, not the icon
- **WHEN** an icon is hovered or keyboard focus reaches it, and when the pointer leaves, focus blurs, or Escape is pressed
- **THEN** the condition's readable name — its label, or its code only when no label is supplied — its remaining duration, and every derived modifier are not shown on the icon but appear in a tooltip opened by hover or focus and closed on pointer leave, blur, or Escape

#### Scenario: The tooltip names modifiers in the stat vocabulary
- **WHEN** the tooltip states a condition's content
- **THEN** it states the full label, the duration when the payload supplies one, and every derived modifier the payload provides, each modifier named in the game's stat vocabulary (for example 攻擊, 敏捷, 防禦, 準度, 每回合行動, 魔力消耗) rather than by its raw adjustment key, with its value verbatim — no sign, unit or digit added or dropped — and a key outside that vocabulary is named by the neutral 其他修正 and keeps its value

#### Scenario: Assistive technology reads the icon itself
- **WHEN** a condition icon renders with no pointer available
- **THEN** the icon carries the tooltip's content as its accessible name, so the information is reachable by assistive technology without the pointer

#### Scenario: The tooltip never counts down
- **WHEN** a tooltip states a duration
- **THEN** it states the payload's `remaining_seconds` value as committed; the client runs no countdown and does not re-render the tooltip between commits

#### Scenario: Overflow and emptiness stay honest
- **WHEN** more conditions are committed than the row's width fits, and when the condition list is empty
- **THEN** icons are bounded to the row's width and the remainder stays reachable in one action through a trailing `+N` icon stating how many are hidden, which discloses the hidden conditions as the same tooltip content for each; an empty list renders no icon row at all — no placeholder, no `無條件` text — consistent with the contextual-hiding rule that an absent surface is not a dimmed or emptied surface

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
The minimap SHALL render as a bounded HUD island in the `map` anchor, below the place card and above the objective line, carrying the committed `local_map` payload's title, sharing the anchor's content-column width with the place card so the two read as one column. On the coordinate lattice — selected exactly by the coordinate-bearing layers (`grid`, `wilderness`) — it SHALL state the renderer's axis convention as orientation marks in its header; on the radial graph variant it SHALL omit them.

#### Scenario: Omitted marks never assert an undrawn axis
- **WHEN** the resolved layout variant is the radial graph
- **THEN** the island omits the orientation marks rather than assert an axis the presentation does not draw (a radial graph draws no axis)

#### Scenario: The worded marks and the drawn axis travel together
- **WHEN** the island draws its lattice
- **THEN** those marks and the axis cross the lattice draws are ONE claim stated twice — once in words, once as geometry — so the two travel together: a map surface draws the axis cross only where that same surface states the axis convention in words, and the island's marks are what license the axis its lattice draws; the island therefore draws the axis cross through the `current` node on the coordinate lattice and draws none on the radial graph, and a surface that states no orientation marks — the full-map surface as it stands — draws no axis at all

#### Scenario: The header follows the redesign draft's treatment
- **WHEN** the island renders on the coordinate lattice
- **THEN** it states the orientation marks following the redesign draft's header treatment — the letterspaced title style and the `北↑ 東→` marks the draft's lattice header draws

#### Scenario: Decoration states nothing in words
- **WHEN** the lattice draws its coordinate dot field and its knowledge-edge vignette
- **THEN** they are decoration that states nothing in words and are not read as a position, a bearing, a distance, or a terrain claim: the dot field pictures the coordinate cell step the lattice already claims, and the vignette pictures the limit of what the payload knows

#### Scenario: The readout states the current cell's world coordinates alone
- **WHEN** the island renders on a coordinate-bearing layer
- **THEN** it states the `current` node's own coordinates as a two-integer figure — the payload `x` and `y` exactly as committed, with no unit, delta, or derived quantity — as the entire content of its readout line, so the island's position statement is the drawing convention plus the current cell's world coordinates and nothing else

#### Scenario: The readout never restates what other surfaces own
- **WHEN** the readout line renders
- **THEN** it does not restate the current node's place name, its visibility state, or a movement destination: the place name belongs to the stage's place card, which stands directly above this island in the same column, and a minimap shows the current position by definition

#### Scenario: Node names stay available without island selection state
- **WHEN** the player hovers or selects, or a remembered node renders
- **THEN** the readout is not driven by hover or by selection and the island keeps no hovered-node or selected-node state; a node's own name stays available as its on-canvas accessible name and, for a remembered node, as visible text on the surface its layout variant presents it on — the name drawn beside the island's edge direction marker on the coordinate lattice, and its entry in the full-map surface's remembered list on the radial graph, where the island draws no visible remembered-node list at all — with the untruncated name always available to assistive technology on the island, so no remembered place is readable by sight alone

#### Scenario: No spatial figure beyond the single coordinate pair
- **WHEN** any layer renders on the island
- **THEN** apart from that single figure the island renders no bearing angle, compass angle, distance, or other coordinate figure: coordinate readouts for non-current nodes, differences between node coordinates, and every spatial figure on the graph variant remain forbidden, because on coordinate-bearing layers node coordinates are validated world coordinates whose only permitted visual uses are relative-direction geometry and the current-node figure, and on every other layer they are renderer-local layout values that carry no spatial meaning at all

#### Scenario: Octant words exist only in the markers' text alternative
- **WHEN** the island exposes its edge direction markers to assistive technology
- **THEN** the one direction statement the island MAY make in words is the octant name an edge direction marker already draws — one of `北`, `東北`, `東`, `東南`, `南`, `西南`, `西`, `西北` — and only on the island's assistive-technology text alternative for those markers, where it names the bearing the drawing already asserts to a reader who cannot see it; a numeric angle, a degree figure, and a distance remain forbidden everywhere

#### Scenario: No layout control exists to persist
- **WHEN** either layout variant renders on the island or the full-map surface
- **THEN** neither presents any map layout control — no segmented switch, button, menu item, or other affordance selecting between the coordinate lattice and the radial graph — because the layout is resolved once from the committed payload's `layer` in the render model and both surfaces consume that one value, so there is nothing for a control to change; no layout choice is persisted in a client-local preference or any storage, and nothing about layout selection travels to the server, because no selection exists to persist

#### Scenario: The single full-map affordance wears no chrome
- **WHEN** the full-map surface the island opens is reachable
- **THEN** the island presents no control for a surface the application does not mount — a full-map affordance exists only once that surface is reachable — and otherwise exactly ONE full-map affordance with no visible button chrome: no labelled control, icon button, or other visible trigger occupies the island's header or any other part of the island, because the island itself is the affordance

#### Scenario: The affordance is a real full-bleed button
- **WHEN** the full-map affordance renders
- **THEN** it is a real `<button>` element spanning the island's whole box, transparent and layered beneath the island's visual content so the button element contains no focusable descendant, carrying 展開全地圖 as its accessible name and opening the full-map surface through the platform's own Enter/Space button behaviour rather than a key handler on a non-button element; its focus-visible indication delineates the whole island rather than a small region of it

#### Scenario: Every activation path opens the map exactly once
- **WHEN** the player clicks anywhere on the island's non-interactive body
- **THEN** the full-map surface still opens as a pointer convenience, provided the click did not originate in an interactive descendant, and every activation path opens the surface exactly once

#### Scenario: The island root never becomes a button
- **WHEN** the island's content changes
- **THEN** the island root gains no button role or tab-stop of its own — the full-bleed button, not the root, is the keyboard path — and `role="button"` on the island root is forbidden outright: a `role="button"` element must contain no focusable descendant and must not flatten a composite surface into one accessible name, and the island is a composite surface whose content the root would swallow; the full-bleed button remains the island's only tab stop whatever its content becomes — a remembered place's presentation is not a tab stop, on either layout variant, and is readable without being focusable — and the minimap's existing per-node movement submission is unchanged

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
In combat mode the root SHALL render one vertical icon-and-label command list with a neutral inline Skills count equal to the committed descriptor count, omitted at zero. The active root SHALL be the only listbox/tab stop and expose its focused row by active descendant. No other mode SHALL render this combat root.

#### Scenario: The root preserves the resolver's contract
- **WHEN** the combat root renders
- **THEN** it preserves the existing resolver item order, identities, availability and confirmation routes, and glyphs retain the existing concept mapping

#### Scenario: Deeper frames keep one active row container
- **WHEN** the player opens a frame deeper than the combat root
- **THEN** the root list is replaced by the current frame, the existing breadcrumb/back path remains, and only one active row container exists

#### Scenario: Vertical arrows traverse and wrap; horizontal arrows rest
- **WHEN** the player presses Up/Down at the combat root, and separately Left/Right
- **THEN** Up/Down traverse and wrap in rendered order, and Left/Right are no-ops at root

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
The action dock SHALL carry one shortcut-legend strip at the bottom of its content column, below the scrolling region, in exploration and combat mode (never in creation mode, and never visibly in dialogue mode, where the strip is hidden with the collapsed command region). The legend SHALL render exactly once as visible content and SHALL be the only element carrying the legend's test hook; no root command list or pane SHALL carry a second copy.

#### Scenario: The legend matches the reference dock hint
- **WHEN** the legend strip renders
- **THEN** it matches `docs/design/elosern-redesign/index.html`'s dock hint in wording and structure: the text `數字鍵 1–9 ‧ ` followed by an `<kbd>` element naming `Enter` and the verb `執行`, the separator `‧`, and an `<kbd>` element naming `Esc` and the verb `返回`; the legend renders with the reference's `<kbd>` treatment (monospace face, `--ink-780` ground, 2px bottom border); and the dock carries no dialogue-mode legend variant

#### Scenario: The legend never lies
- **WHEN** a key, gesture, or affordance is named in the legend, or when a named affordance's behaviour changes
- **THEN** the legend names no key, gesture, or affordance this client does not implement or that no longer behaves as named, and advertises no implemented affordance the reference's legend does not name; when a named affordance's behaviour changes (for example, a control that used to open a surface and now only moves focus into an always-present one), the legend's wording is updated in the same change that alters the behaviour

#### Scenario: Digits pick and confirm the frame's first nine entries
- **WHEN** the dock owns keyboard focus (the key target is not editable) and the player presses `1`–`9`
- **THEN** the press moves the current dock frame's focus onto its first nine entries (1-indexed, rendered order — for the scene overview, its first nine chips in reading order: exits, then people, then objects, then the footer; a frame's `back` row takes the slot of its rendered position) and activates the entry through the same confirm path `Enter` uses — a disabled entry shows its explanation and submits nothing, an in-flight entry stays locked, and a held repeat is suppressed; the slots address the frame's rendered entries, disabled ones included

#### Scenario: Digits outside the dock's claim fall through
- **WHEN** dialogue mode holds — or a digit's entry does not exist (a frame with fewer rendered entries, dialogue mode, or the pre-session empty stack)
- **THEN** in dialogue mode neither the dock's entries nor the keyboard router claims any digit: the digits `1`–`N` belong to the dialogue choice list while it holds focus, which handles them itself as "Dialogue choices appear centred over the stage after the line is fully read" defines; and an unclaimed digit falls through to the text / command-history path

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

The dock SHALL render a breadcrumb line whenever the router's menu stack is deeper than its root frame, and SHALL hide it entirely at the root frame. The breadcrumb SHALL name the parent frame and the current frame, with the current frame visually distinguished, and SHALL carry a back control. Activating the back control SHALL perform exactly the same operation the Escape key performs — it SHALL pop exactly one menu level and SHALL NOT dispatch any action.

#### Scenario: The verb popover names its target once
- **WHEN** a target's verb popover (the scene overview's person-target frame) is current
- **THEN** the breadcrumb does not render and the target is stated exactly once, because the popover's own heading already names the target; the popover's `back` row, Escape, and a pointer press outside the popover card remain its back paths, and every other submenu keeps the breadcrumb

#### Scenario: The breadcrumb cannot disagree with Escape
- **WHEN** the breadcrumb's contents and visibility are computed
- **THEN** they are derived from the keyboard router's own frame stack and depth, published through the committed view in the same pass as the frame's rows; the client maintains no second navigation state — no local pane selection, no locally accumulated crumb stack — so the breadcrumb can never disagree with what Escape will do

#### Scenario: Frame labels come from the frames themselves
- **WHEN** a frame's breadcrumb label is rendered, including a frame scoped to one target
- **THEN** the label comes from the frame itself, and for a frame scoped to one target it is the target's server-authored display name

#### Scenario: The `back` row owns the focus treatment
- **WHEN** any frame renders and its `back` item takes focus
- **THEN** every frame's `back` item renders as a row of that frame, so a focused `back` item carries the same focused treatment as any other row (a background fill and border change together), and the breadcrumb's back control carries no focus state of its own that mirrors the router's focus

#### Scenario: Back activation pops exactly one level
- **WHEN** the player activates the back row with Enter or the pointer, or activates the breadcrumb's back control
- **THEN** exactly one level pops, the parent frame's previously focused entry is restored, and no action is dispatched

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

The dock's row region SHALL render the current frame in a form chosen for what that frame contains, using one shared row renderer for every form so the focused marker, the disabled marker and its `（無法使用）` suffix, the accessible disabled association, and the row identity attribute are defined in exactly one place.

#### Scenario: The form set is fixed
- **WHEN** the row region selects a form
- **THEN** the forms are: exit, person, object, and footer chips for the scene overview; the verb popover's rows under a target head; the waiting cards; suggestion cards for the suggestions frame; and the combat forms specified elsewhere in this capability

#### Scenario: Exploration frames never regress to grids or nav lists
- **WHEN** any exploration frame renders
- **THEN** it renders no exit-outlet grid and no navigation-row list: exits are chips of the scene overview, and a host's conversation topics are the dialogue surface's choices, never a dock frame

#### Scenario: An enabled exit chip names direction by glyph and destination by text
- **WHEN** an exit chip is enabled
- **THEN** it renders the exit's direction as a leading glyph and its primary text is the destination's display name — never a repetition of the direction word or the exit's own label once a glyph already carries that meaning

#### Scenario: Direction glyphs come only from the canonical table
- **WHEN** an exit label falls outside the fixed client-side table of canonical direction words
- **THEN** the glyph is resolved from that table, and an out-of-table label renders verbatim as the chip's primary text (there being no glyph to carry it) rather than being mapped to a guessed direction

#### Scenario: An unknown destination falls back without doubling labels
- **WHEN** the destination's display name — resolved by matching the exit's server-authored destination node against the committed local-map nodes — finds that node absent from the committed lattice
- **THEN** an enabled canonical-direction chip falls back to its own exit label as its primary text rather than rendering blank, and never renders both the destination name and the exit's own label at once

#### Scenario: A disabled exit chip keeps its own label and marker
- **WHEN** an exit chip is disabled
- **THEN** it always renders its own exit label as its primary text, never the destination name, followed by the shared disabled marker

#### Scenario: Exit chip focus and disabled reasons stay honest
- **WHEN** an exit chip is focused, or a disabled chip's explanation is sought
- **THEN** the focused state is conveyed by the chip's background and border fill together with no additional focus-only glyph beside its persistent direction glyph; the disabled chip's server-authored explanation remains reachable by assistive technology directly from the chip and is shown in the overview's reason strip while the chip is focused; and the submitted move payload is unchanged

#### Scenario: Chips and rows render only backed fields
- **WHEN** any chip or row renders
- **THEN** it renders only fields the committed payload carries: its server-authored name and, where its form has one, an optional sub-line composed of such fields; none renders a statistics line, a portrait, or any other element for which the payload has no field — where the design draft shows such an element it is absent rather than emptied or mocked

#### Scenario: Icons are decorative and key-selected
- **WHEN** a chip or row shows an icon or glyph
- **THEN** it is decorative, hidden from assistive technology, always accompanies a real text label, and is selected only from stable server-authored keys or the direction table — never from free text such as a display name

#### Scenario: The verb popover heads with its target
- **WHEN** a target's verb popover renders
- **THEN** it renders a head naming the target it is scoped to, taken from the frame's own server-authored display name, above that target's rows

#### Scenario: The disabled contract holds in every form
- **WHEN** a disabled entry renders in any row or chip form
- **THEN** it keeps the existing disabled contract: it remains focusable by arrow keys and by pointer, keeps its accessible disabled state and its server-authored explanation, and submits nothing

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
- **THEN** it is display-only: it is not a row container, not part of the dock's composite widget, and not a second tab stop — target selection happens in the dock's target frame

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
- **THEN** it exposes that participant's portrait reference as a data attribute for tests and for the beat presentation; it shows its display name above its decorative hit-point gauge and distinguishes acting or focused-target presentation with a non-colour cue; names ellipsize within their plate while retaining full DOM text; and its gauge is a slim track centred under the figure on the scene caption's baseline, above the command-line row, filled to that foe's current hit points (the displayed value while a combat round plays) over its maximum, with a trailing bar that follows a drop after the vitals' trail delay so the damage shows as a gap

#### Scenario: The line-up is decorative art
- **WHEN** the line-up renders
- **THEN** it is hidden from assistive technology, carries no focusable element, intercepts no pointer events, and states no tokens, hit-point numerals, or participant states, which remain the participant frame's

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
In combat, opening Skills SHALL present the committed skill categories as a bounded frame of category entries, each carrying its server-authored label and the count of its own skill descriptors. Opening a category SHALL present that category's sub-groups as a frame when the category carries more than one sub-group, and SHALL open the skill frame directly when it carries exactly one — so no menu level ever offers a single choice.

#### Scenario: The skill frame lists descriptors beside a detail region
- **WHEN** a skill frame renders
- **THEN** it lists that group's descriptors in the server's order, each row carrying the skill's label and its resource cost, beside a detail region naming the focused skill, its description, its cost, its target requirement and, when it is unavailable, its server-authored reason

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
The client's reference surfaces SHALL render in a wide workspace 12px below the top navigation's bottom edge, 16px inside each side of the viewport, and one command-line row height plus 12px above the viewport bottom, so only the band's lowest control strip stays exposed beneath it. A fine border and a fully opaque charcoal ink panel SHALL distinguish the workspace from the stage.

#### Scenario: The workspace covers the stage and keeps the modal lifecycle
- **WHEN** a reference drawer opens
- **THEN** the workspace covers the stage, the bottom band, and the command-line row whether or not that row is expanded, and the existing modal drawer lifecycle and shared motion tokens are retained over a dimmed scrim covering the whole viewport behind the drawer

#### Scenario: The workspace body and art column
- **WHEN** a reference drawer renders between its header and optional footer
- **THEN** a decorative art column MAY accompany the scrolling content body, and only the content body scrolls

#### Scenario: The shared reference-surface head
- **WHEN** a reference drawer renders its head
- **THEN** it is the shared reference-surface header: the title in the serif heading face at the shared workspace scale with slight tracking, and the subtitle as the small muted line beside it; every reference drawer declares one leading head icon (a decorative, `aria-hidden` glyph from the shared glyph registry rendered before its title); and the drawer's close control carries an accessible name (e.g. an `aria-label`) but MAY be rendered icon-only, with no visible text node — "labelled" in this requirement means an accessible name, not necessarily visible text

#### Scenario: One drawer, focus-trapped and restorative
- **WHEN** a second drawer is opened while one is open, or the open drawer is closed by Escape, its labelled close control, or the scrim
- **THEN** at most one drawer is open at any time and opening a second closes the first; while open the drawer traps keyboard focus, so no surface behind it is reachable by sequential navigation; every close path restores focus to the control that opened it; and an open drawer registers itself as an open surface so the stage recession this capability already requires applies without a second mechanism

#### Scenario: The skill-book drawer states its counts honestly
- **WHEN** the skill-book drawer renders while the `character` panel is available, and when it is unavailable
- **THEN** the head carries a subtitle stating its owner's active and passive skill counts (`主動 {n} ‧ 被動 {m}`, computed from that same payload `SkillBook` renders); when the panel is unavailable the subtitle is empty, matching the drawer's existing degrade-without-inventing-data contract

#### Scenario: Skill use is graphical and practice retitles the head
- **WHEN** the skill-book drawer offers skill use, and while the declared-practice sub-screen replaces the book body
- **THEN** the drawer provides discoverable graphical skill-use and practice affordances under the `webclient-skillbook-casting` contract, without requiring a cast-syntax footer or memorized skill/target keys, and the prescribed static `施放入口：cast <技法>[@威力]=<代號>` footer is removed; while the practice sub-screen is up the head title reads 修煉 and book-use guidance is absent

#### Scenario: Book use hands the modal focus owner over
- **WHEN** the player explicitly transfers from book use to dock-owned casting
- **THEN** the modal book closes and focus transfers to that flow without leaving a drawer trap active, while ordinary drawer close paths retain their existing opener restoration

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
- **THEN** its head carries a leading skill glyph and a `主動 {n} ‧ 被動 {m}` subtitle matching the panel's active/passive row counts, its title renders exactly once, and graphical use/practice are discoverable without the old cast-syntax footer

#### Scenario: Book use transfers the modal focus owner
- **WHEN** the player deliberately activates book use and its authoritative flow is ready
- **THEN** the book closes, its scrim/trap retires, and focus moves to the sole dock-owned casting flow without a behind-drawer control becoming interactive

### Requirement: Reference drawers present no router frame and never host a dock row region
No reference drawer SHALL present a keyboard router frame. Opening any reference drawer SHALL push no frame, switch no sub-dock, and record no drawer-hosted service surface; an opener that is itself a top-navigation entry MAY first return the dock to its root frame exactly as every top-navigation entry does, and the drawer open SHALL add nothing to the stack after that. The client SHALL NOT maintain a second frame stack, a second focus model, or a second set of menu keys for a drawer.

#### Scenario: Every drawer opener pushes nothing
- **WHEN** the 背包 ‧ 裝備 drawer opens from the top navigation's 背包 entry, the 商店 drawer from a merchant's `navigate` affordance row, or the 任務 drawer from the top navigation's 任務 entry or from a guild clerk's `navigate` affordance row
- **THEN** the opening pushes no frame, switches no sub-dock, and records no drawer-hosted service surface

#### Scenario: No drawer body hosts dock chrome
- **WHEN** any reference drawer body renders in any state
- **THEN** it renders neither the dock's row renderer (`dock-menu`) nor its detail pane (`dock-detail`)

#### Scenario: Closing leaves the router alone and returns focus
- **WHEN** a reference drawer closes — by Escape, its close control, or the scrim
- **THEN** the router is left alone, no menu level is popped, and focus is restored to the control that opened it

#### Scenario: Drawer rows stay keyboard reachable
- **WHEN** a committed row inside a reference drawer takes the keyboard
- **THEN** it remains reachable without a hosted router frame

#### Scenario: Lost payloads close their drawers
- **WHEN** a drawer's backing payload is absent, the committed mode changes so it is no longer available, the presentation epoch resets, or the transport is lost
- **THEN** the drawer is openable only while its backing payload is present, every open drawer closes, and every local selection, quantity and confirmation state inside it is discarded

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
The bag workspace SHALL use shared chrome for the `背包 ‧ 裝備` title, local inventory SVG icon, close control, and wallet subtitle formatted as integer copper from the committed available character panel. The wallet SHALL additionally render exactly once in the body as the single row of a `金錢` section.

#### Scenario: The available body keeps its authoritative sections
- **WHEN** the bag body renders with available payloads
- **THEN** it presents an `裝備` section carrying the read-only equipment doll, an `物品` section whose heading carries the shipped listing size above the bounded responsive grid, a `金錢` section carrying the same committed wallet, and a reserved non-interactive detail column driven by the existing hover/focus selection

#### Scenario: The listing never claims completeness
- **WHEN** the shipped inventory nears or reaches the server row ceiling
- **THEN** the listing remains bounded by that ceiling and states it in words when reached, and no shipped count claims to be the player's untruncated holdings

#### Scenario: Registered rows render only their presentation
- **WHEN** a registered row's non-null `presentation` renders
- **THEN** it selects one local inline SVG by `icon_key`, an item-kind label, rarity label, bounded summary, and non-colour-only rarity treatment, and its tile shows committed held count and a non-colour equipped marker

#### Scenario: A null presentation stays neutral
- **WHEN** a row carries a null presentation
- **THEN** it renders only the neutral unknown-item SVG and visible unknown marker, and the browser derives no type, icon, rarity, summary, or mechanics from item key or display name

#### Scenario: One inspector serves pointer and keyboard
- **WHEN** the grid renders its tiles
- **THEN** it uses native keyboard-focusable buttons and one non-focusable inspector shared by pointer hover and keyboard focus; both inspection paths expose identical committed name, kind, rarity, count, equipped state, and summary; and the focused tile references the stable inspector through `aria-describedby`

#### Scenario: Tiles follow only their action descriptor
- **WHEN** a tile is inspect-only, unknown, disabled, an enabled usable item, or enabled equipment
- **THEN** inspect-only and unknown tiles dispatch nothing; disabled tiles remain keyboard reachable, expose `aria-disabled`, and show the committed reason on activation without dispatch; enabled usable items open a labelled, focus-trapped inventory-use confirmation; and enabled equipment dispatches its toggle immediately

#### Scenario: Selection state is client-local and resets
- **WHEN** the panel is replaced, the drawer closes, the mode or epoch changes, or the transport is lost
- **THEN** selection and dialog state — client-local — reset

#### Scenario: The bag infers no mechanics or tools
- **WHEN** the bag renders
- **THEN** it renders or infers no numeric item statistics, recovery amounts, conditions, effects, consumable flags, slots, set bonuses, comparisons, sorting, filtering, search, drag, or drop behavior, and renders no static sort/filter/search pill

#### Scenario: Availability degrades section by section
- **WHEN** services v3 inventory is available in combat, when services commits its unavailable form or inventory is absent, or when inventory is available but character is unavailable
- **THEN** the drawer remains available from its combat affordance while inventory is available; on unavailable services or absent inventory it renders only the registered reason and fabricates no wallet, equipment, row, count, action, or dialog; and with inventory available but character unavailable the grid remains available, the doll renders its registered unavailable state, and no wallet subtitle, wallet body value, or zero balance is invented

#### Scenario: Bag transitions use the motion tokens
- **WHEN** inspector, confirmation, or warning state changes under reduced motion
- **THEN** all transitions use existing motion tokens so reduced motion makes them effectively instant

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
The equipment presentation SHALL be built from the committed `character` panel's equipment rows, each of which carries a slot, an item key and a display name and nothing more. The section SHALL be introduced by the bag's small tracked section heading `裝備` carrying the right-aligned tag `真值 ‧ 偽裝不影響`, and SHALL NOT be introduced by a standalone `裝備人偶` title.

#### Scenario: The doll lays out as the redesign's equipment row
- **WHEN** the equipment section renders
- **THEN** the doll lays out as the redesign's equipment row: a compact two-column square slot grid beside a 裝備描述 column that lists the committed rows grouped under their slot labels

#### Scenario: Four named positions, fixed slot SVGs
- **WHEN** the square grid renders
- **THEN** the doll renders the server's three singleton slots and one accessory summary as four named positions; the main-hand, armor, and accessory-summary positions each render a fixed local SVG selected by its server-authored slot role; the off-hand position is the iconless position; and the doll selects no item icon from an item key or display name

#### Scenario: Empty and occupied singleton slots
- **WHEN** a singleton slot carries no row, or carries rows
- **THEN** an empty singleton slot renders a visible named empty state with a dashed outline; an occupied one renders its visible slot label in the grid and its committed display name in the 裝備描述 column

#### Scenario: Duplicate, accessory, and unknown rows are never lost
- **WHEN** committed rows carry more than one row for a recognised singleton slot, repeatable accessories, a slot key outside the recognised set, or no equipment at all
- **THEN** the square position consumes only the first row of a duplicated singleton slot and every further row for that slot renders as a labelled overflow row; the accessory summary renders its visible label and committed item count while every repeatable accessory row renders in the 裝備描述 column's accessory group; an unrecognised slot key renders as a labelled fallback row rather than being discarded, so no row the payload sends is lost; and with no equipment at all the doll renders only its visible empty statement

#### Scenario: The doll states true values only
- **WHEN** the doll renders equipped items
- **THEN** it renders no item statistic, attack or defence value, rarity, item icon, summary, or comparison against another item — the equipment rows carry none of those — and equipment is presented as true values that a disguise does not affect, which the section tag states exactly

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
The character-status drawer SHALL present the committed `status` panel's resources and its complete condition roster in every mode, because that panel is available in every mode. It SHALL present the committed `character` panel's true traits, guild standing, and persona background, and SHALL mark each of those sections with the registry-owned reason when the `character` panel is unavailable — as it is outside exploration mode — rather than hiding the drawer or inventing a value.

#### Scenario: Equipment and wallet belong to the inventory drawer
- **WHEN** the character-status drawer renders
- **THEN** equipment and wallet presentation, which belong exclusively to the inventory drawer, do not render in character status

#### Scenario: Conditions pair a glyph with every backed value
- **WHEN** the condition roster renders a committed condition
- **THEN** the condition pairs a non-colour severity glyph with its label and every numeric or derived-modifier value the payload provides

#### Scenario: A disguise compares, never substitutes
- **WHEN** a disguise is active
- **THEN** the drawer renders the displayed values beside the true trait rows they describe, distinctly labelled, together with the statement that a disguise affects display, registration and identification only and that combat always resolves against true values; a displayed value never replaces a true trait row

#### Scenario: The 親密狀態 disclosure is preserved in place
- **WHEN** the committed `character` panel's `intimate` field is present, and when it is `null` or the panel is unavailable
- **THEN** the drawer renders the collapsed-by-default 親密狀態 disclosure widget — added by the archived intimate-status change — immediately after the 偽裝 (disguise) section and before the 背景 (persona) section, and no change removes it, reorders it, or alters its disclosure widget, content, or collapsed default; like the persona area it spans the full row of the section grid; with `intimate` null or the panel unavailable the section is absent from the DOM, exactly as the merged main spec requires; this change removes only the equipment and wallet sections

#### Scenario: Every section names itself in the shared treatment
- **WHEN** any of the drawer's sections renders (vitals, traits, conditions, guild counters, disguise, intimate status, persona)
- **THEN** each carries a labelled, small-caps section heading naming what it presents, using the same heading treatment the HUD's other islands use

#### Scenario: Value rows render as bordered card tiles
- **WHEN** the vitals, traits, or guild-counter sections render their values
- **THEN** each value is its own bordered card tile in an auto-fill grid of equal-width tracks rather than a plain text row, each tile only as tall as its own content, with the tile's label at the left and its `current`/`current / maximum` value in the shared numeral treatment at the right; a tile carrying more than two breakdown chips spans its grid's full row so its chips wrap in one wide line; and no value not already present in the committed payload (such as an effective-vs-base delta) is invented to fill the tile

#### Scenario: Sections size themselves independently
- **WHEN** the section grid renders
- **THEN** the sections are content-sized cards in an auto-fit grid of equal-width tracks in their DOM order, with the persona area, the intimate disclosure, and a panel-wide unavailable reason spanning the full row, so no section's height depends on another's

#### Scenario: The hero names only supplied values
- **WHEN** the drawer body opens
- **THEN** it opens with a hero naming the committed character — the `status` panel's actor name, its composed full title (`status` actor `full_title`), and the `character` panel's guild rank, each rendered only when the payload supplies a non-blank value and omitted — never guessed — otherwise; the name and title therefore stay in every mode, and the rank is absent while the `character` panel is unavailable

#### Scenario: The hero carries the openers, the header carries the title
- **WHEN** the hero renders
- **THEN** it carries the drawer's existing secondary openers (技能書, and 同伴 ‧ 隊伍 while the party panel is available) in one wrapping action row, with their existing behavior, and the body does not repeat the drawer title the shared header already renders

#### Scenario: The roster renders as coloured pills with nothing dropped
- **WHEN** the condition roster renders
- **THEN** it renders as a wrapped row of rounded pill badges, one per condition, each carrying that condition's label, its visible severity word, its non-colour severity glyph, and its duration/modifier text — the same content the roster shows today, none of it dropped — coloured per severity using the same severity-to-colour mapping the capped status-island condition chips use elsewhere in the HUD; these presentation rules apply identically whether a section is fully populated or marked with a registry-owned unavailable reason

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
Across every drawer, the player's wallet SHALL be rendered exactly once per opening of the inventory drawer — once in its shared header subtitle and once as the single row of its `金錢` body section, both read from the committed available panel that owns the value — and nowhere else in the drawer layer.

#### Scenario: No other drawer or body element carries a balance
- **WHEN** the shop, the lore reference, the character-status drawer, or any other body element of the inventory drawer renders
- **THEN** none of them renders a balance of its own

#### Scenario: An unreadable wallet renders nothing rather than zero
- **WHEN** a drawer's available character panel does not carry a committed non-negative integer wallet
- **THEN** it renders no balance at all rather than a zero

#### Scenario: The body row is gated with the inventory section
- **WHEN** the bag's inventory section availability changes
- **THEN** the `金錢` body row is additionally gated on the bag's available inventory section, because it renders only inside the bag's three-section stack and the two renderings must never disagree

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
Every affordance inside a drawer SHALL emit exactly the server-authored action identifier and payload its descriptor carries, through the client's single dispatch entry, and SHALL be governed by the same in-flight, epoch and revision gates as the same action issued from the dock.

#### Scenario: Disabled and locked affordances submit nothing
- **WHEN** an affordance inside a drawer is disabled, or mutations are locked — a submission in flight, an unaccepted revision, or a lost transport
- **THEN** a disabled affordance remains readable for its server-authored reason and submits nothing, and while mutations are locked every drawer affordance is locked with them

#### Scenario: Destructive actions confirm; quantity forms keep server bounds
- **WHEN** a destructive service action is issued from a drawer, or a quantity form inside a drawer is filled
- **THEN** the destructive action sits behind an explicit confirmation step that names what it does, with a cancel path that submits nothing, and the quantity form keeps the server-advertised minimum and maximum and permits no value outside them

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
The client's text control SHALL render as a single bar filling the stage's `command-line` anchor, containing — in this order — a prompt chevron, the command input field with its send control, a hint cluster, and the command-history controls. The bar SHALL carry no quick-word chip, no control that only writes a fixed command word into the field, and no overlay or drawer opener: those openers live in the top navigation bar's tool group.

#### Scenario: The anchor is a 44px row on the message region's top edge
- **WHEN** the `command-line` anchor renders in any mode
- **THEN** it is one row 44px tall docked to the top edge of the bottom band's message region: its lower edge coincides with the band's upper edge, it extends from the left HUD island column's right edge to the right edge of the band's left two thirds in every mode — so in dialogue mode, where the message region spans the whole band, it stops short of the dialogue host's portrait — and it overlays the lowest strip of the stage box, never the band and never the message text

#### Scenario: The line is collapsed by default and never persisted
- **WHEN** the shell mounts, and when the player expands and reloads
- **THEN** the command line starts collapsed on every mount, its expanded state is client-local and never persisted, and no stored presentation state can open it or keep it open

#### Scenario: Collapsed hides the row but keeps the field's state
- **WHEN** the row is collapsed
- **THEN** it is hidden with `display:none`, so the bar and its input field leave the layout, the accessibility tree, and the tab order, while the input field stays in the DOM with its preserved identifier and keeps any unsent draft and history-walk state

#### Scenario: The ⌨ toggle reports the row's state
- **WHEN** the message region renders in any mode
- **THEN** it carries, at its bottom-right corner, a labelled ⌨ toggle control that reports the row's state through `aria-expanded` and names the row through `aria-controls`; the toggle is rendered in every mode that renders the message region, never covers the message text (the text's scroll region keeps its last line clear of the toggle), and is unaffected by the committed narrative, the dialogue choice list, or the dock frame

#### Scenario: Exactly three paths expand the line
- **WHEN** the player presses `/` while no editable control is focused, activates the ⌨ toggle while the row is collapsed, or borrows the line for free-form dialogue
- **THEN** the command line expands and focus moves into its input field only after the row is rendered, on exactly these three paths

#### Scenario: Exactly two paths collapse the line
- **WHEN** Escape is pressed in the input field, or a send the field accepts clears it
- **THEN** the line collapses on exactly these two paths, with focus moved to the current mode's focus home (the action dock, or in dialogue mode the dialogue choice list while it is rendered and the message window's page surface otherwise) before the row is hidden

#### Scenario: Toggle-close keeps focus; rejected sends stay open
- **WHEN** the ⌨ toggle is activated while the row is expanded, or a send is rejected — offline, mutations locked, a mutation in flight, or, for a borrowed free-form send, a presentation phase other than active
- **THEN** the toggle collapses the row and leaves focus on the toggle, and a rejected send leaves the row expanded with the typed text and focus in the field

#### Scenario: Losing focus never collapses the row
- **WHEN** the field loses focus by any other means (a pointer activation elsewhere, a drawer or overlay opening)
- **THEN** the row does not collapse

#### Scenario: The expanded bar keeps its clearances and drops only hints
- **WHEN** the bar is expanded at 1451x790 or at any larger viewport up to the chrome cap, and when horizontal space is insufficient
- **THEN** the expanded bar does not overlap the action dock, the narrative caption, the bottom band, or any HUD island anchor; the hint cluster is dropped first; and the input field, its send control, and the history controls are never dropped (the command line and its toggle are absent from the layout in creation mode, per the visibility matrix)

#### Scenario: The field is one action away
- **WHEN** the shell mounts in exploration mode
- **THEN** the command-line row is hidden with `display:none`, the input field is present in the DOM but outside the tab order, the ⌨ toggle is rendered at the message region's bottom-right with `aria-expanded="false"`, and pressing `/` or activating the toggle once renders the row and puts focus in the input field

#### Scenario: The expanded row keeps its geometry at the minimum viewport
- **WHEN** the command line is expanded at the 1451x790 reference viewport and at 2560x1440, in exploration mode and in dialogue mode
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
The hint cluster SHALL name only behaviour the client implements. It SHALL state the command-history recall keys and the Tab-completion affordance — matching the draft's `↑↓ 歷史 ‧ Tab 補全`. No surface of the command line SHALL name a key, gesture or affordance that has no implementation behind it.

#### Scenario: Tab completes against the deduplicated candidate set
- **WHEN** the player presses Tab inside the input field
- **THEN** completion behaves as named: the current draft is completed against the client's candidate set (session command history and the committed exploration panel's exit names and interact-target display names, deduplicated)

#### Scenario: Unique, ambiguous, and unmatched drafts
- **WHEN** exactly one candidate matches, several match, or none matches
- **THEN** with one match the field holds the full completion with the caret at its end; with several the field holds the longest common prefix and successive Tab presses cycle the matching candidates, with Shift+Tab reversing the cycle; and a draft that matches no candidate leaves the field untouched

#### Scenario: Tab never steals focus and the cycle resets honestly
- **WHEN** Tab is pressed, the draft text is edited manually, or the committed candidate sources change
- **THEN** Tab never moves focus away from the field at all (the release path is Escape, which the dock's shortcut legend names); the completion cycle resets when the draft text is edited manually; and a change to the committed candidate sources drops any in-flight cycle

#### Scenario: History controls share the keys' walk
- **WHEN** the history controls are used
- **THEN** they are labelled controls that drive the same history-walk state the recall keys drive — one walk reached by two input paths — and they never submit

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
A full-screen overlay SHALL render as one shared surface laid over the stage, carrying the shared reference-surface header naming the surface and a labelled close control, with its body as its only scrolling region. While an overlay is open it SHALL trap keyboard focus, so no surface behind it is reachable by sequential navigation. It SHALL close on Escape and on activation of its close control, and both paths SHALL restore focus to the control that opened it.

#### Scenario: Utility overlays share the reference workspace bounds
- **WHEN** a utility overlay renders
- **THEN** it uses the same opaque reference workspace as the reference drawers: 12px below the top navigation's bottom edge, 16px inside each side of the viewport, and one command-line row height plus 12px above the viewport bottom, so the workspace covers the stage, the bottom band, and the command-line row whether or not that row is expanded, and only the band's lowest control strip stays exposed beneath it

#### Scenario: The scrim recesses and absorbs but never closes
- **WHEN** an overlay is open
- **THEN** a scrim covers everything below the top navigation behind the overlay, recessing that exposed strip, and absorbs pointer activation without closing the overlay, so no command control behind the overlay is reachable by pointer; the scrim starts at the top navigation's bottom edge and does not cover it, so the navigation stays operable and activating another overlay or drawer trigger replaces the open overlay as below; and the mode-owned creation workspace is excluded from these utility-frame bounds

#### Scenario: The shared focus trap is reused
- **WHEN** an overlay implements its focus trap
- **THEN** it uses the shared focus trap the client already owns rather than a second implementation

#### Scenario: One overlay replaces another and inherits its opener
- **WHEN** an overlay is open and a second overlay opens
- **THEN** at most one overlay is open at any time, opening a second closes the first, and the opener recorded for the replacement is the control that opened it, so closing restores focus to the most recent trigger, never to the trigger of the closed overlay

#### Scenario: Overlays and drawers never coexist
- **WHEN** an overlay would open while a reference drawer is open, or vice versa
- **THEN** opening either closes the other, so at most one focus-trapped surface exists at any moment, and an open overlay registers itself as an open surface so the stage recession this capability already requires applies without a second mechanism

#### Scenario: Escape resolves topmost-first through one order
- **WHEN** Escape is pressed with several dismissable levels present
- **THEN** it is resolved by a single precedence order, topmost first — a popover open inside the open overlay, then the open overlay, then an open drawer, then the focused command field, then the dock's current menu level — with each level consuming the key and stopping

#### Scenario: An overlay's popover takes Escape first
- **WHEN** a popover is open inside an overlay, and later no such popover is open
- **THEN** Escape closes the popover without closing the overlay, keeping focus inside the overlay, and the next Escape closes the overlay; while no such popover is open, Escape closes the overlay directly

#### Scenario: Client resets close every overlay
- **WHEN** the mode changes into creation, the presentation epoch resets, or the transport is lost
- **THEN** each closes every open overlay, and the mode-driven character-creation surface is not part of this single-open stack, because it is not opened by the player and a utility control must never dismiss it

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
The map, settings and help surfaces SHALL each be reachable from the running client by a labelled control, not only from the component showcase.

#### Scenario: Live triggers open each surface
- **WHEN** the client renders the minimap island and the top navigation bar
- **THEN** the minimap island carries a labelled control that opens the map surface, rendered as a sibling of its map canvas rather than as a wrapper around its actionable nodes — the island's non-interactive body MAY additionally open the same surface on pointer click, which never replaces or wraps the labelled control — and the top navigation bar's labelled 設定 control and the 說明 control in its tool group open the settings and help surfaces, in every mode that renders the top navigation bar, whether the command line is expanded or collapsed

#### Scenario: The map surface tracks read-model replacement
- **WHEN** the committed `local_map` read model is replaced
- **THEN** the map surface renders the payload through the same component the minimap island renders and re-renders its available and unavailable branches whenever that read model is replaced, so a superseded payload never leaves a stale map or a stale reason on screen; when a newly committed payload resolves to the other layout variant, the surface follows the resolved value with no control of its own

#### Scenario: The map opens fitted with exactly its view affordances
- **WHEN** the map surface opens
- **THEN** it opens fitted, showing the whole drawing inside its body, and offers exactly the view affordances the full-map fit-view requirement of the local-map capability defines — wheel and `+` / `-` zoom within that requirement's bounds, labelled 放大 and 縮小 buttons, drag-pan, a labelled 置中 button that recentres the current node, and a `?` disclosure button named 圖例 that opens the state legend in a popover — naming those gestures in words in its guide row

#### Scenario: View affordances change nothing committed
- **WHEN** any map view affordance is used
- **THEN** it changes only the view of the drawing: none changes the committed payload, the resolved layout variant, or any geometry the surface declares, and none is persisted

#### Scenario: The map states no figures
- **WHEN** the map surface renders on any layer
- **THEN** it renders no bearing, compass angle, distance, or coordinate figure, and no zoom level, scale ratio, or other figure describing the view

#### Scenario: The canvas framing is pure CSS
- **WHEN** the map surface's body renders
- **THEN** it carries the redesign draft's map-canvas framing (the radial-gradient dark terrain background painted as pure CSS inside a rounded ink border) and fabricates no terrain geometry the payload does not claim

#### Scenario: The help surface is the client's own truth
- **WHEN** the help surface renders
- **THEN** it renders the client's own control reference — the keys this client binds, the dock's navigation model and the close paths — from a single client-owned source, and states how the game's own help output is reached; it names no key binding or control the client does not implement, describes `/` and the ⌨ toggle as expanding the command line and Escape and a successful send as collapsing it, renders no authored game-help content for which no committed panel exists, and stands no placeholder in for it

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
The client SHALL expose a narrative prose scale with three steps — `A−` 16px, `A` 18px, and `A+` 20px at the 1451x790 reference scale, multiplied once by the desktop chrome factor — selectable from the settings surface, whose current step is marked by an indicator that does not rely on colour alone. The scale SHALL apply to narrative and dialogue prose only and SHALL NOT alter HUD, dock, drawer, overlay or any other interface text.

#### Scenario: A− is the reading floor
- **WHEN** the `A−` step renders at the reference scale
- **THEN** it renders the prose the client shows at exactly 16 CSS px, and no step renders it smaller

#### Scenario: The scale touches only prose
- **WHEN** any prose scale step is selected
- **THEN** it governs the message window's page text, the complete-log surface's lines, the prompt line and the settings surface's reading sample, which previews the page text — and the stage's measured anchor geometry is unaffected at the reference viewport or any larger one

#### Scenario: Settings are client-local and dispatch nothing
- **WHEN** any setting the surface offers changes
- **THEN** it is client-local presentation state; no settings control dispatches an action — the client's action allowlist carries exactly one `options.*` action, the suggestions dismissal, and this capability adds none

#### Scenario: Settings apply immediately and persist versioned
- **WHEN** a setting changes
- **THEN** it is applied immediately to the presentation it governs — the document's presentation tokens for the prose scale, the motion level, the text-to-HTML toggle and the colourblind palette, and the message window for the reading preferences and the motion level — and is persisted through the client's versioned, presentation-only browser store as a harmless display preference

#### Scenario: Reload re-applies; store reset restores defaults
- **WHEN** the client loads, or the presentation store resets
- **THEN** each setting is re-applied at load, and reset to its default — fully applied, never half-applied — whenever that store resets

#### Scenario: A legacy stored scale loads as the default step
- **WHEN** a stored prose-scale value matches none of the re-stepped values
- **THEN** it loads as the default `A` step rather than as a clamped legacy multiplier

#### Scenario: The motion level follows its own requirement
- **WHEN** a motion level is stored, and when none is stored
- **THEN** the motion level follows "The motion level is a client-local preference that governs every client animation": a stored level overrides the operating system's reduced-motion preference, which continues to apply while no level is stored

#### Scenario: No inert control is offered
- **WHEN** the settings surface enumerates its controls
- **THEN** it offers no control it does not implement

#### Scenario: The prose scale moves prose and nothing else
- **WHEN** the player selects the largest prose scale
- **THEN** the message window's page text, the complete-log surface's lines, the prompt line and the settings surface's reading sample render at 20px at the reference scale, every other HUD, dock and overlay label is unchanged, and no stage anchor's rendered box intersects another's at 1451x790

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
Committed narrative lines SHALL render with the reference draft's semantic presentation: a line of committed `sys` kind SHALL render in the sans face at the reference's secondary size and colour with a leading `◈` seal-colour marker contributed by the line's own class, not by invented text; emphasis inside prose lines SHALL render in the reference's gold accent; plain prose lines SHALL render in the bundled monospace reading face, the face the message window's page text uses.

#### Scenario: Classes mount only from committed kinds
- **WHEN** markup classes are mounted at render time
- **THEN** the existing markup pipeline mounts them from committed line kinds only — the tokenizer, the player-echo divider lines, and the box-drawing art path are unchanged, and no markup class is mounted for a kind the store does not carry

#### Scenario: Each retained line is tokenized exactly once
- **WHEN** a retained server, system, or error line renders on any surface
- **THEN** the markup pipeline has run exactly once for that line, when the line is retained; every surface that renders the line renders from that one token stream, never from a second tokenization or a second markup path; and a player input line never enters the pipeline

#### Scenario: Fragments keep the whole line's classes
- **WHEN** paging splits a line into fragments
- **THEN** a fragment renders with the same kind class, and the same box-drawing class where it applies, as the whole line would, and only the first fragment of a `sys` line shows the leading `◈` marker

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
- **THEN** it renders as plain prose in the monospace reading face without the sys marker

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
  line render in the monospace reading face with the emphasis still gold in whichever fragment holds it

### Requirement: The party drawer presents compbig rows and the fixed follow rules
The 同伴 ‧ 隊伍 drawer SHALL render on the shared reference drawer contract with the sub-count `N / 4`, one compbig row per committed party slot (initial-letter/gold avatar with the same portrait fallback, display name, bond stage line, HP bar with numerals, the joined 參戰 token when the companion fights, and a 請其離隊 control), and one 空位 row stating the invite rule in stage-name words.

#### Scenario: The empty slot never shows the raw threshold
- **WHEN** the 空位 row states the invite rule
- **THEN** it names the rule in stage-name words — the raw affinity threshold number is not shown

#### Scenario: The invite control dispatches the exact existing payload
- **WHEN** the 空位 row's `邀請當前 NPC…` control is activated
- **THEN** it dispatches `explore.party_invite` with the exact existing payload `{npc_id: <the committed invite-capable interact target's identity>, message: ""}` — the fixed empty message, since the drawer invents no freeform invitation input — under the existing dispatch and confirmation contract

#### Scenario: The invite control never fabricates a target
- **WHEN** the committed exploration context names an invite-capable interact target, and when it does not
- **THEN** the control is enabled only in the first case and otherwise disabled with its rule line as the reason — it never fabricates a target

#### Scenario: Leaving dispatches under the same contract
- **WHEN** the player activates 請其離隊
- **THEN** it dispatches `explore.party_leave` for that identity under the same contract

#### Scenario: The section closes with the reference's fixed rules
- **WHEN** the drawer closes the party section
- **THEN** it states three fixed follow-rule statements matching the reference draft verbatim, and renders no companion detail control that has no backing read model

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
The HUD SHALL carry the objective tracker as one line in the stage's `map` anchor, directly beneath the minimap island, while the committed mode is exploration and the committed `objectives` panel is available with a non-empty `rows` list; it SHALL be hidden with `display:none` in combat and dialogue mode and SHALL render nothing when `rows` is empty, when the panel is unavailable, or in creation mode. The line SHALL have one fixed row height whatever the payload holds.

#### Scenario: The line's contents follow one fixed order
- **WHEN** the tracker line renders
- **THEN** it carries, in order: a `目標` label; a stage box for the first row of `objectives.rows` showing a completion check when that row's `stage_progress >= objective_quantity` and an empty box otherwise; that first row's `objective_line`, truncated on one line with an overflow indicator while its full text stays the line's accessible text and tooltip; a mono-gold slot carrying `stage_progress / objective_quantity` when the first row's `objective_quantity` is greater than one and its `+reward_copper` when `objective_quantity` is one and `reward_copper` is non-null, and carrying nothing otherwise; and, when more than one row is committed, a mono-gold `+N` count where `N` is the number of further rows

#### Scenario: Later rows and deadlines belong to the quest drawer
- **WHEN** rows after the first, or any row's `deadline_line`, exist
- **THEN** they are not rendered on the stage; the quest drawer presents them

#### Scenario: The tracker is display-only and never invents
- **WHEN** the tracker renders
- **THEN** it renders no accept, abandon, turn-in, or tracking control and dispatches no action, and presents no objective prose the panel does not carry and no invented optional or previous-stage rows

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
The skill-book drawer SHALL offer a 修煉 affordance on each active skill row the committed `character` panel supports, and activating it SHALL replace the book body with a practice sub-screen inside the same drawer: the drawer title becomes 修煉, the body lists the panel's active skills for selection, and one bounded-duration control starts the practice.

#### Scenario: The browser computes nothing about practice
- **WHEN** the practice sub-screen renders and submits
- **THEN** the browser computes nothing about eligibility, duration outcome, or progression: every row state comes from the committed panel, the duration control reuses the waiting surface's bounded hours form, and confirmation submits exactly one `explore.practice` with the selected `skill` and the converted whole `seconds` through the shared dispatch/confirmation lock

#### Scenario: In-flight submissions lock the control
- **WHEN** a submission is in flight or its declared presentation revision is pending
- **THEN** the control is disabled

#### Scenario: The result line is escaped and local
- **WHEN** a server-authored result line (success summary or rejection message) arrives
- **THEN** it renders as escaped text inside the sub-screen and nowhere else

#### Scenario: Closing restores the book, not the footer
- **WHEN** the sub-screen closes
- **THEN** the book body, the original drawer title, and the book's graphical use/practice guidance are restored without restoring the removed cast-syntax footer

#### Scenario: Casting leaves practice intact
- **WHEN** the player casts
- **THEN** casting does not replace or bypass this practice workflow

#### Scenario: Practice dispatches one server-trusted intent
- **WHEN** the player opens 修煉 from an active skill row, selects the skill, enters `2` hours, and confirms
- **THEN** exactly one `ui_action` is submitted, `explore.practice` with that `skill` and `seconds: 7200`, and the drawer controls stay locked until the result revision is adopted

#### Scenario: The result line is the server's
- **WHEN** a practice result arrives
- **THEN** its Traditional Chinese summary or rejection message renders verbatim as escaped text in the sub-screen, with no client-computed progression, elapsed-time, or eligibility claim

#### Scenario: The practice screen is gated by committed data only
- **WHEN** the `character` panel is unavailable or a row carries no practice support
- **THEN** no 修煉 affordance renders for that row and no practice state is invented

#### Scenario: Closing the practice screen restores the book
- **WHEN** the player closes the practice sub-screen
- **THEN** the drawer shows the skill book again with its original title and graphical use/practice guidance, no cast-syntax footer and no second drawer

### Requirement: The reference surfaces have no permanently visible home and are reached from the top navigation or the dock
The skill book, the bag and equipment, the shop, the quest board, the lore reference and the character status SHALL each render in exactly one place — its drawer — and SHALL NOT be present in the DOM while that drawer is closed. The stage SHALL carry no permanently visible column of reference panels.

#### Scenario: Every reference surface is reachable in two actions
- **WHEN** a player seeks a reference surface from the top navigation bar or the dock's root frame
- **THEN** each drawer is opened either by the dock frame that owns its surface, or by a single labelled control inside a drawer that already presents the same read model, or by a surface this capability names elsewhere as an opener for it, and no reference surface requires more than two actions to reach

#### Scenario: Opening a drawer disturbs no dock contract
- **WHEN** a drawer opens
- **THEN** no dock root item, menu frame, menu key, or the meaning of Escape changes

#### Scenario: No reference surface is mounted while the drawers are closed
- **WHEN** the stage renders in exploration mode with every drawer closed
- **THEN** no skill book, bag, shop, quest board, lore reference or character-status element exists in the DOM or in the tab order, and no reference column is rendered

#### Scenario: Every reference surface is reachable from the dock
- **WHEN** the player starts at the dock's root frame or the top navigation bar
- **THEN** each of the six reference surfaces is reached in at most two actions, and the narrative caption stays in the bottom band's message region

#### Scenario: An emptied right-hand stack costs nothing
- **WHEN** the stage renders at 1451x790 and 2560x1440 with every drawer closed
- **THEN** the top-right `map` anchor renders no reference panel, contributes no visible box and no tab stop, and no interactive stage anchor's rendered box intersects another's

### Requirement: The action dock fills the band's command region at a fixed size
The action dock SHALL fill the bottom band's command region — the right third of the band, or the whole band in creation mode — at the band's fixed height, and SHALL NOT be a floating panel placed elsewhere on the stage. Its box SHALL be the command region's box in exploration, combat, and creation mode and for every frame, and no surface outside the band SHALL be positioned from the frame the dock currently carries.

#### Scenario: No frame moves or resizes the dock
- **WHEN** the dock carries the scene overview, a target's verb popover, the waiting frame, the combat frames, the skill master-detail, the destructive confirmation, or an empty pane host
- **THEN** no frame widens, heightens, shortens, or moves its box

#### Scenario: Dialogue hides the dock with the region
- **WHEN** the committed mode is dialogue
- **THEN** the command region is collapsed and the dock is hidden with `display:none` together with it, as "The command region collapses in dialogue mode and the message window spans the band" states; it is not rendered anywhere else in that mode

#### Scenario: Fixed chrome surrounds one scrolling region
- **WHEN** the dock's content column lays out
- **THEN** it is laid out as fixed chrome — the combat root's vertical command list in combat mode and no bar in exploration mode, an optional breadcrumb line, and the shortcut-legend strip at the bottom — around one remaining region that holds the current frame's rows or chips, and that region is the surface's only scrolling area, so no dock content is ever pushed outside the command region

#### Scenario: Popovers and wide frames stay inside the region
- **WHEN** a target's verb popover renders, or a frame's content does not fit the region's width
- **THEN** the popover renders as a card laid over the region's visible box, inside the command region, scrolling inside its own card when its rows exceed it, and the wide frame wraps or collapses its own columns inside the region, never overflowing it horizontally

#### Scenario: One dock element persists across every mode
- **WHEN** the committed mode changes, including into or out of dialogue
- **THEN** the panel is the same single `#action-dock` element in every mode, carrying its existing tab index, its `data-mode` attribute and its role as the documented focus home of every mode except dialogue, and it is not remounted

#### Scenario: The presentation stays readable beyond colour
- **WHEN** the command region and its band render
- **THEN** the command region uses the current charcoal-and-gold presentation, the band that contains it paints the reference's band chrome, and selected actions remain distinguishable by text and shape as well as their gold or warm-red emphasis

#### Scenario: The command region is the band's right third
- **WHEN** the shell renders in exploration mode at 1451x790 and at 2560x1440
- **THEN** the `#action-dock` element lies inside the band's command region, the region's left edge is at two thirds of the stage width and its right edge at the stage's right edge (each ±1px), and the dock covers neither the message region nor the command line

#### Scenario: No frame resizes the command region
- **WHEN** the dock moves at 1451x790 from the scene overview to a target's verb popover, to the waiting frame, and, in combat, to the deepest skill target frame
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
- **WHEN** the shell renders at 1451x790 with the deepest combat frame open
- **THEN** the dock's rendered box stays within the command region, no dock content overflows the
  region horizontally, and the frame's confirm control is reachable by scrolling the row region
  without being clipped

#### Scenario: The band's background matches the reference's shadowed gradient
- **WHEN** the bottom band renders in any mode
- **THEN** the band element paints a background gradient and a box-shadow, its top edge is the
  seam's fine gold line drawn by the band's own decoration, and the `#action-dock` content column
  itself paints no background, border, or shadow

### Requirement: The place card names the current location and the world time
The stage SHALL carry a place card as the first island of its `map` anchor, at the stage box's top-right corner directly below the top band and directly above the minimap island, while the committed mode is exploration or combat, and SHALL NOT render it in creation mode or settled dialogue mode. The card SHALL state the current location as its heading and the world date/time beneath it, and SHALL be the only surface on the stage or in the top band that states either value.

#### Scenario: Dialogue entry leaves only inert exit paint
- **WHEN** the mode live-enters dialogue
- **THEN** the card MAY retain only the inert exit paint permitted by "Surface visibility is gated by the committed game mode", outside the accessibility tree and tab order from commit, and becomes `display:none` when the anchor's fade ends

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
- **WHEN** the card renders
- **THEN** it carries no control, no tab stop, and no dispatch

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

### Requirement: Text speed and auto-advance are client-local reading preferences the settings surface owns
The settings surface's reading section SHALL offer a text-speed control with the four steps `慢` (`slow`), `標準` (`normal`), `快` (`fast`), and `瞬間` (`instant`), and an auto-advance toggle (`自動翻頁`). The text speed SHALL default to `normal` and auto-advance SHALL default to off.

#### Scenario: The speed step is marked without colour
- **WHEN** a text-speed step is current
- **THEN** it is marked by an indicator that does not rely on colour alone and is exposed as the pressed state of its button

#### Scenario: The control names the motion override
- **WHEN** the text-speed control renders
- **THEN** it says that the `減少` and `關閉` motion levels show pages at once, because an effective motion level other than `full` overrides the chosen speed as `webclient-input-narrative` defines

#### Scenario: Both preferences follow the settings rules
- **WHEN** either reading preference changes
- **THEN** it follows the settings rules of "Narrative prose scale is a client-local preference the settings surface owns": client-local, dispatching nothing, applied to the message window immediately, persisted through the versioned presentation-only browser store, re-applied at load, and reset to its defaults when that store resets

#### Scenario: An out-of-range stored value falls back
- **WHEN** a stored value lies outside the defined steps
- **THEN** it is discarded and the default applies

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
When a dock pane's row region uses a fixed column count for keyboard row/col geometry, that fixed count SHALL govern only which cell each row occupies. Changing a row's rendered width SHALL NOT change which row occupies which cell.

#### Scenario: Pane forms own their own layout
- **WHEN** a pane form (the combat skill list, the target tokens, the scale chips) lays out its rows
- **THEN** this requirement prescribes not how wide a column or row renders: each form uses its own styles, and whether a form fills the pane's width or leaves width empty is a visual decision of that form

#### Scenario: Rows never overflow the pane horizontally
- **WHEN** the pane's available width is narrower than the rows' natural width
- **THEN** whatever the form, every row renders inside the pane's box without horizontal overflow: the rows wrap or compress, and long content wraps within its row

#### Scenario: The scene overview is not a fixed-column pane
- **WHEN** the scene overview renders its chips
- **THEN** they wrap by width under the section geometry the exploration dock requirement defines — the scene overview is not a fixed-column pane

#### Scenario: A narrow command region keeps every row inside the pane
- **WHEN** a combat skill, target, or scale pane renders in the command region at the 1451x790 reference viewport
- **THEN** every row lies inside the pane's right edge, the pane shows no horizontal overflow, and a long label wraps within its row

#### Scenario: Rendered width never changes the keyboard cell mapping
- **WHEN** the player presses ArrowRight in a pane whose keyboard geometry fixes two columns
- **THEN** focus reaches the row that the fixed column count places in the second column, whatever width each row renders at

### Requirement: The command region collapses in dialogue mode and the message window spans the band
While the committed mode is `dialogue`, the bottom band's command region SHALL be collapsed and the message region SHALL span the band's whole width at the band's fixed height from the commit's frame. The collapsed region and the action dock inside it SHALL leave the accessibility tree, the tab order, and pointer hit-testing from the commit's frame.

#### Scenario: The region slides out and back with the motion level
- **WHEN** the mode enters dialogue, and later leaves it, at each motion level
- **THEN** the region slides out to the right and fades over the panel duration of the client's motion level, drawn over the widened message region, and is `visibility: hidden` once that slide ends, contributing nothing visible; leaving dialogue brings it back into reach in the commit's frame and slides it back in from the right; at `reduced` it only fades, within 150ms, and at `off` it hides and returns in the commit's frame

#### Scenario: The dock survives dialogue unmounted-free
- **WHEN** the mode enters and leaves dialogue
- **THEN** the dock stays the same mounted `#action-dock` element, its router keeps the exploration scene overview as its only frame (the reset on entering dialogue that `webclient-exploration-menu` defines), leaving dialogue shows that overview again with no remount, dialogue presents no dock frame, and no exploration affordance is removed from the committed `exploration` panel: movement stays reachable through the minimap and the conversation's own controls

#### Scenario: Dialogue's focus home is the choice list or the page surface
- **WHEN** the mode is dialogue
- **THEN** the shell's focus home is the dialogue choice list while it is rendered and otherwise the message window's page surface, and every path that returns focus to the focus home — the command line's Escape and accepted send, the mode-change rescue, and the return after a completed or rejected action — lands there, never on the hidden dock and never on the document body

#### Scenario: Mode boundaries move focus deliberately
- **WHEN** the mode enters dialogue with focus held inside the command region, or leaves dialogue for exploration with focus held inside the message region, inside the `choices` anchor, or on the document body
- **THEN** on entering, focus moves to the message window's page surface before the region is hidden; on leaving, focus moves to the action dock once the region is rendered again

#### Scenario: The router claims only the slash in dialogue
- **WHEN** the mode is `dialogue`
- **THEN** the keyboard router claims only `/` (the command-line opener); every other key is unclaimed by the dock router, so no key moves the hidden dock's focus, pushes or pops a frame, or activates a hidden entry; the keys the dialogue choice list handles never reach the router, and Enter and Space on the focused page surface keep their reading meaning

#### Scenario: Entering dialogue collapses the command region
- **WHEN** the player activates 交談 in a host's verb popover at 1451x790 and the commit makes the mode `dialogue`
- **THEN** from the commit's frame the band's command region and the `#action-dock` element are out of the accessibility tree and the tab order, the message region spans the band's whole width at 220px (±1px) height, the region is `visibility: hidden` once its slide ends, focus is on the message window's page surface while the greeting is read, and focus moves to the dialogue choice list when the greeting's last page is fully shown

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
Each standing portrait on the stage SHALL be rendered by one stage-actor component. The controlled figure and companions in `actor-left` SHALL follow the companion-lineup rule. The dialogue host SHALL render once: when its committed identity joins to a committed party slot or controlled lineup figure, its existing lineup StageActor is the host and no duplicate renders in `actor-right`.

#### Scenario: The host actor presents its catalog entry truthfully
- **WHEN** a non-party host's stage actor renders in `actor-right`
- **THEN** it presents the committed `art` panel's `portrait_catalog` entry named by `dialogue.host.portrait_ref` — the complete image bottom-aligned with contain fit, and a grounded silhouette with host identity and authoritative availability when the entry is a placeholder; when `portrait_ref` is null or names no catalog entry it renders the truthful placeholder: the display name's initial and display name, never a stock or guessed image; and the client constructs no catalog key from host identity or any other field

#### Scenario: Foes follow the same presentation rule
- **WHEN** a foe's stage actor renders
- **THEN** it presents its committed catalog entry under the same complete-image, grounded-silhouette and display-name-placeholder rule

#### Scenario: Speaking follows dispatch state, never prose
- **WHEN** the committed mode is dialogue and the available host renders
- **THEN** stage actors carry a speaking state — the speaker at full brightness, listeners dimmed to 60% through the shared dim token; the host speaks except while an `explore.talk_scripted` or `explore.talk_freeform` action submitted by the player is in flight (from dispatch until its result is handled and declared presentation revision accepted, or until rejection), when the player speaks; the state derives from dispatch state, committed mode and panel availability, never prose

#### Scenario: Companions listen unless they are the host
- **WHEN** a companion's identity does, or does not, match the active host
- **THEN** companions remain listeners unless their identity matches that active host; a speaking companion temporarily receives the highest z without moving, then restores baseline z

#### Scenario: Nothing dims outside dialogue
- **WHEN** the mode is outside dialogue, or its panel is unavailable
- **THEN** the controlled figure remains lit and foes are never dimmed

#### Scenario: The speaking cue is never colour-only or disruptive
- **WHEN** a speaking state is active
- **THEN** the dim is not the only speaking cue — the name plate names the host and each actor exposes its speaking data attribute; actors remain decorative, with no focusable element; motion owns transitions; and no other dialogue behavior changes: the name plate, pagination, choices, focus, keyboard paths and non-party host mode-transition motion retain their contracts

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
While the committed mode is `dialogue` and the committed `dialogue` panel is available, the client SHALL present the conversation's choices as one choice list in the stage's `choices` anchor, and nowhere else. The list SHALL render only while the message window reports that the current response's last page is on screen, fully shown, with no pending action mark, and while no action the player dispatched is in flight.

#### Scenario: Any unread or in-flight moment hides the list
- **WHEN** a page is still typing, a further page is not yet read, or a pick or free-form speech awaits its reply
- **THEN** the list is not rendered

#### Scenario: The rows follow the payload exactly
- **WHEN** the choice list renders
- **THEN** its rows are, in order: one pick row per `dialogue.choices` entry in payload order, each carrying the digit badge of its 1-based position and its bounded label; a `⌨ 自由對話` row; a `↦ 移動…` row; and a `✕ 結束對話` row — and it renders no row the panel does not back, no reason tag, and no disabled pick

#### Scenario: Picks and exits dispatch their exact intents
- **WHEN** the player activates a pick row, or an enabled exit row
- **THEN** a pick dispatches `explore.talk_scripted` with `{npc_id: host.identity, keyword_id}` through the single dispatch entry, and an enabled exit row dispatches the same `explore.move` payload the overview's exit chip dispatches

#### Scenario: The free-form and exit rows dispatch nothing themselves
- **WHEN** the player activates `⌨ 自由對話`, or `✕ 結束對話`
- **THEN** `⌨ 自由對話` expands the command line and focuses its field through the free-form borrow path, bound to the host, and dispatches nothing itself; `✕ 結束對話` dispatches `explore.dialogue_leave` with `{npc_id: host.identity}` and nothing else

#### Scenario: The move row borrows the scene overview's exits
- **WHEN** the player activates `↦ 移動…`
- **THEN** it dispatches nothing and replaces the rows with the exit rows of the committed exploration scene overview, in its order, each carrying the exit's direction glyph and, while enabled, the destination's display name under the scene overview's exit-chip rules, ending with a back row; a disabled exit row stays focusable with its server-authored reason and dispatches nothing

#### Scenario: The exit rows return to the choices
- **WHEN** Escape or the back row is activated in the exit rows, or the committed room has no exits
- **THEN** the choice rows return with the `↦ 移動…` row focused, and a room without exits still shows the back row alone

#### Scenario: One composite, one tab stop, full keyboard
- **WHEN** the choice list holds focus
- **THEN** it is one keyboard composite and one tab stop: DOM focus rests on the list container, which names its focused row through an active-descendant reference; ArrowUp and ArrowDown move to the previous and next row, wrapping; Home and End move to the first and last row; Enter and Space activate the focused row; while the choice rows are shown, digit `1`–`N` activates pick N directly; and a held key's auto-repeat does not activate

#### Scenario: The active row is shown by shape and fill
- **WHEN** the list holds focus on its rows, including a disabled exit row
- **THEN** the active row is shown by shape and fill — a leading `▸` and the dock's muted-gold fill — never by colour alone, and an active disabled exit row keeps a quiet treatment that promises no action

#### Scenario: Handled keys stop at the list
- **WHEN** the list handles a key, and when `/` or an unhandled key is pressed
- **THEN** every key the list handles is consumed by it and does not reach the keyboard router or the page surface, while `/` and every key the list does not handle passes on unchanged

#### Scenario: Focus arrives, leaves, and never dangles
- **WHEN** the list appears while focus is on the message window, inside the message region, or on the document body, and when an activation is about to dispatch
- **THEN** focus moves to the list with its first row focused, and before an activation dispatches focus moves to the message window's page surface, so the list's removal never leaves focus on a removed element or the document body; a pointer activation of a row focuses that row and activates it through the same path as Enter

#### Scenario: Activations obey the dispatch lock once each
- **WHEN** a mutation is in flight or awaiting its declared presentation revision, and when key and pointer input combine
- **THEN** every activation is suppressed exactly like a dock entry, and no combination of key and pointer input emits more than one request per deliberate activation

#### Scenario: The list derives only from committed panels
- **WHEN** the list's rows and presence are computed
- **THEN** rows derive from the committed `dialogue` and `exploration` panels alone and depend on no dock frame or router descriptor, and presence derives from the window's reader state and the dispatch state, never from narrative prose

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
The client SHALL have exactly three motion levels: `full`, `reduced`, and `off`. The settings surface SHALL offer them as one `動態效果` control with the three buttons `完整`, `減少`, and `關閉`. The pressed button SHALL be the effective level, marked by an indicator that does not rely on colour alone. Selecting a button SHALL store that level.

#### Scenario: The effective level follows the store, then the operating system
- **WHEN** a level is stored, and when none is stored
- **THEN** the effective level is the stored level when one is stored; while none is stored it is `reduced` when the operating system requests reduced motion and `full` otherwise, and it follows a change of the operating system's preference without a reload

#### Scenario: An invalid stored level is discarded
- **WHEN** a stored value is not one of the three levels
- **THEN** it is discarded, as if nothing were stored

#### Scenario: The level applies document-wide at once
- **WHEN** the effective level changes
- **THEN** it is applied to the whole document at once, the moment it changes, and every client animation and transition reads it through the client's motion tokens

#### Scenario: Each level's behaviour is fixed
- **WHEN** the effective level is `full`, `reduced`, or `off`
- **THEN** `full` plays every animation and transition the client defines; `reduced` plays no translation, no shake, no flash, and no looping animation (pulses, blinking, spinners), its stage and mode transitions play only as opacity fades of at most 150ms, every other transition — drawers and control feedback included — is instant, and message pages appear in full at once; `off` makes every visual change instant, fades included

#### Scenario: Tokens own every duration
- **WHEN** any animation or transition declares a duration, delay, or travel distance
- **THEN** it comes from the client's motion tokens and no component declares a literal duration

#### Scenario: The level never withholds information
- **WHEN** a transition plays at any level
- **THEN** at every level each transition ends in the same rendered state, and every state it conveys is also conveyed without motion

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
The client SHALL apply every committed change to its state and to the document immediately; motion SHALL only decide how the view moves between two committed states. A transition SHALL NOT delay a committed value, a mode or visibility attribute, the accessibility tree, or the tab order beyond the moment the change commits, and SHALL NOT delay the player's ability to act beyond its own duration at the current motion level.

#### Scenario: An interrupted transition runs toward the newer state
- **WHEN** a transition is interrupted by a newer committed change
- **THEN** it runs toward the newer state and does not first finish the older one

#### Scenario: Stepped presentation follows three rules
- **WHEN** presentation plays in steps — message pages, and a combat round's beats as `webclient-combat-menu` "A combat round plays beat by beat" defines
- **THEN** steps play in the order their data committed, and a step never reorders, drops, or alters committed data; a player click or press that advances the presentation shows the current step's end state at once — for a playing combat round it shows the whole round's end state; a new player action shows every queued step's end state, a playing combat round's included, before its own response starts; and nothing is lost: every stepped text stays in the full log

#### Scenario: Stepped pauses come from the tokens
- **WHEN** a stepped presentation waits for a pause
- **THEN** the pause comes from the motion tokens, read by the client's script from the same tokens the styles use, and resolves to zero at `off`; revealing text follows the reader's text speed

#### Scenario: Only a playing round holds input
- **WHEN** a combat round is playing
- **THEN** it is the one presentation that holds the player's input: it keeps the command panel locked until it ends, and the player can end it at once with a click or press on the message window or a typed command

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
The stage SHALL animate the committed changes below, taking every duration and distance from the client's motion tokens, so they follow the effective motion level of "The motion level is a client-local preference that governs every client animation". No transition SHALL delay a committed value or the player's input beyond its own duration, as "Presentation timing never gates committed state or input" requires.

#### Scenario: A new scene image crossfades above the previous one
- **WHEN** a new scene image commits
- **THEN** it crossfades from the previous image to the new one over the scene duration (500ms at `full`); the new image starts its fade only once it is decoded; until then the previous image stays visible with the dimmed treatment the backdrop already uses for a prior image, so the fade never passes through an empty frame and a previous scene is never presented undimmed as the current one; the new image fades in above the previous one and the pair does not dip through the stage behind them mid-fade; and the scene label, the alternative text, and the placeholder update at commit

#### Scenario: A new location label slides in
- **WHEN** a new location label commits, and when the world time alone changes
- **THEN** the place card's heading slides in from the left and fades in while the previous heading fades out, and a world-time-only change does not animate

#### Scenario: A new current node pans the minimap
- **WHEN** a new current map node commits, and when the previous current node is absent from the new placement
- **THEN** the minimap pans: the drawing starts where the previous current node stood on screen and eases to its committed placement, and the current-node marker travels the step from the node the player left to the new current node, so a move reads even when the drawing itself does not shift; an absent previous node shows the new placement at once; and the full-map surface does not pan

#### Scenario: A new response clears the message window
- **WHEN** a new response commits
- **THEN** the message window clears as "The message window presents the current response one page at a time in the band's message region" allows: the previous page fades out over the clear duration (150ms at `full` and at `reduced`) while the new page starts at once and surfaces beneath it within the same duration, so the two pages never read through each other

#### Scenario: A new portrait source crossfades
- **WHEN** a stage actor's portrait source changes (a new image URL, or a switch between an image and a placeholder), or the speaking state changes
- **THEN** the source crossfades over the portrait duration (400ms at `full`), and the speaking change eases the dim

#### Scenario: The vitals dock rises and sinks
- **WHEN** the vitals dock — the condition icon row and the vitals bars as one surface — shows or hides
- **THEN** it fades in while rising 12px into its bottom-anchored resting position (entering from 12px below it, so it reads as rising out of the band's edge), and fades out while sinking 12px back toward the band when it hides

#### Scenario: Reduced and off compress every transition
- **WHEN** any transition above plays at `reduced`, and at `off`
- **THEN** at `reduced` it plays as an opacity fade of at most 150ms with no slide, no pan, and no marker travel, and the dim changes instantly; at `off` it renders its final state in the commit's frame

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
Every stage element that animates out — a crossfading image or portrait, a previous place-card heading, the message window's clearing layer, the vitals island, and every later leaving element the client animates — SHALL leave the accessibility tree, the tab order, and pointer hit-testing at the moment the change that removes it commits, and SHALL stay out of reach until it is removed or re-enters.

#### Scenario: Focus never lands on a leaving element
- **WHEN** focus would move onto a leaving element, or already sits inside one about to leave
- **THEN** focus never moves onto it, and the client moves focus to its current focus home before the element leaves, so focus never falls to the document body

#### Scenario: Entering and re-entering elements are in reach
- **WHEN** an element is entering, or re-enters while it is still leaving
- **THEN** an entering element MAY receive focus from its first frame, and a re-entering element is in reach again from that moment

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
The stage SHALL animate live mode changes, taking every duration, delay, and distance from the client's motion tokens, so they follow the effective motion level of "The motion level is a client-local preference that governs every client animation".

#### Scenario: Dialogue entry and exit animate as reverses
- **WHEN** the mode changes exploration → dialogue, and dialogue → exploration
- **THEN** entering: the command region slides out to the right over the panel duration (250ms at `full`) while the message window spans the band from the commit's frame, the dialogue host's stage actor slides in from the right and fades in over the actor duration (350ms at `full`), the name plate fades in, and the greeting pages and types as `webclient-input-narrative` defines; leaving: the reverse — the host's stage actor slides out to the right and fades, the name plate fades out, the message window returns to two thirds of the band in the commit's frame, and the command region slides back in

#### Scenario: Combat entry flashes; exit plays no flash
- **WHEN** the mode changes exploration → combat, and combat → exploration
- **THEN** entering: a white flash lasting the flash duration (120ms at `full`) plays once over the stage and under every island, the combat veil fades in, and the command region's content flips to the combat root; leaving: the veil fades out and the content flips back, and no flash plays

#### Scenario: Choice rows stagger in
- **WHEN** the dialogue choice list appears, or rows are swapped in by `↦ 移動…` or by its return
- **THEN** each row fades in and rises into place, delayed by the stagger step (40ms at `full`) times its position, and the list's card fades in; swapped rows stagger the same way

#### Scenario: Only live changes animate
- **WHEN** the client mounts, reconnects, or a resync commits the same mode
- **THEN** none of these transitions plays

#### Scenario: Transitions never delay state, input, or scroll
- **WHEN** any mode transition plays
- **THEN** every leaving element is out of reach as "A leaving element is out of reach while it animates out" requires; no transition delays a committed value or the player's input beyond its own duration — the choice list takes focus and handles keys and pointer from its first frame, and the dock is focusable from the first frame of its return; and the mode change scrolls nothing — a surface that slides past the stage's edge is clipped without widening any ancestor's scrollable area, no focus move during a mode change scrolls an ancestor toward its target, and the stage never shifts sideways

#### Scenario: Decorations stay out of the tree and off the pointer
- **WHEN** the flash, the veil, or the flip plays
- **THEN** each is decorative, absent from the accessibility tree, and never intercepts a pointer

#### Scenario: Reduced and off settle every mode change
- **WHEN** a mode change plays at `reduced`, and at `off`
- **THEN** at `reduced` the slides, the flip's rotation, and the rise move nothing, the fades last at most 150ms, the flash is not visible, and the stagger is zero; at `off` every mode change renders its final state in the commit's frame

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
While a combat round plays by itself, as `webclient-combat-menu` "A combat round plays beat by beat" defines, each beat SHALL play one stage gesture once its page is fully shown, on the stage actors that the beat names and that stand on the stage (the player in `actor-left`, a foe in the foe line-up), taking every duration and distance from the client's motion tokens.

#### Scenario: Each beat kind plays its gesture
- **WHEN** a beat's page is fully shown
- **THEN** the first beat of each action: the acting stage actor steps 24px toward the stage's centre and back within 240ms; `damage`: the target's stage actor shakes 6px from side to side for 180ms with a brief flash, a decorative number naming the damage rises from it and fades over 600ms, and its displayed hit points move to the beat's `hp_after` as the gesture starts, in the vitals or the foe's gauge and in the participant frame, with the trailing bar following; `target_defeated`: a foe's stage actor fades and drops out of the line-up — the player's stage actor never leaves the stage; `roll` and `other`: no gesture

#### Scenario: Pauses and actorless beats follow the gesture
- **WHEN** a gesture finishes, or a beat names a participant with no stage actor (a party member other than the player, or a foe beyond the third)
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
Standing portraits SHALL retain their supplied image contours and align their feet or silhouette base with the stage floor. Repeated visual image captions SHALL be suppressed only on the stage; accessible identity and state SHALL remain available.

#### Scenario: Missing artwork uses the server-selected silhouette
- **WHEN** a standing portrait's artwork is missing
- **THEN** it uses the server-selected built-in silhouette — the committed attribute-selected image rendered as its own alpha mask (see `webclient-art-panel`'s reference-artwork requirement) — carrying the subject name and truthful availability state, without inventing generation or a URL

#### Scenario: Actors without a fallback identity keep the old treatment
- **WHEN** no fallback media identity is carried (e.g. a scene-kind actor)
- **THEN** the existing grounded standing-silhouette treatment applies unchanged

#### Scenario: Unavailable portrait is not generating
- **WHEN** an actor has missing or failed art
- **THEN** a grounded silhouette states the subject and missing or failed state once, and no generating shimmer runs

#### Scenario: Pending motion respects preference
- **WHEN** pending art renders at full, reduced and off motion
- **THEN** only full motion animates the silhouette; the pending label remains readable at every level

#### Scenario: The stage silhouette is attribute-selected
- **WHEN** stage actors for an adult male, adult female, child, elder, and monster character all lack artwork in one scene
- **THEN** each renders the silhouette its server-resolved fallback key selects — never one shared shape for every missing actor — with identity and truthful state labels retained

#### Scenario: Compact stage preserves labels
- **WHEN** the player silhouette, vitals and command line render at the 1451x790 reference viewport
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
Prose SHALL have readable CJK line and paragraph spacing while preserving exact narrative content, the contracted reference font size, sentence-safe paging and map alignment. Page text SHALL use a line height of 1.5 times its font size and SHALL separate consecutive narrative lines by a gap of about half a line. Page measurement SHALL match displayed typography, so no page line is clipped at any viewport or prose scale.

#### Scenario: Spacing never touches content or maps
- **WHEN** CJK spacing treatment applies to prose
- **THEN** it is presentation only (the rendered text content is unchanged) and does not apply to box-drawing map lines, whose whitespace and alignment stay exact

#### Scenario: The marker and plate align to the prose column
- **WHEN** a page and a dialogue name plate render
- **THEN** the page marker ends at the prose column's right edge, or as close to it as the control strip's own controls allow, and stays inside the control strip; and the dialogue name plate's underline starts at the name's left edge

#### Scenario: The reading rule and its motion are conditional
- **WHEN** the page surface holds keyboard focus, and when the motion level is reduced or off
- **THEN** the message window's reading rule shows only while the page surface holds keyboard focus, and decorative motion stops at the reduced and off motion levels

#### Scenario: Resize preserves complete narrative
- **WHEN** mixed CJK and Latin prose is paged, then the viewport or reader scale changes
- **THEN** all content remains reachable without clipped lines, and the marker stays within the reserved strip at the prose edge, clear of the `日誌` control

#### Scenario: Maps preserve whitespace
- **WHEN** a response contains an ASCII map between prose blocks
- **THEN** the map retains its indentation and alignment while prose receives spacing treatment

#### Scenario: The marker follows the dialogue column
- **WHEN** a dialogue page is fully shown at 1451x790
- **THEN** the marker's right edge lies within a few pixels of the left-aligned prose column's right edge, far from the band's right end

#### Scenario: Reduced motion keeps the marker still
- **WHEN** the motion level is reduced or off while a page marker is shown
- **THEN** the marker neither bobs nor fades

### Requirement: Pointer-open dialogue choices expose a local initial highlight
When an eligible dialogue choice list first opens through pointer interaction, it SHALL expose a non-activating initial highlight on its first enabled choice using the same active-descendant state as keyboard navigation. The highlight SHALL be visible even while the list does not hold focus; showing it SHALL NOT itself move focus (where focus goes when the list appears is unchanged) and SHALL NOT dispatch.

#### Scenario: The exit swap keeps an active row
- **WHEN** the list swaps to its exits, with and without an enabled exit
- **THEN** the first enabled exit is active; when no exit is enabled, the first exit stays active with its explanation reachable

#### Scenario: Opening does not answer
- **WHEN** a pointer action leads to a fully-read response with enabled choices
- **THEN** the first enabled choice is highlighted and no choice dispatch occurs until deliberate activation

#### Scenario: A disabled first exit is skipped
- **WHEN** the player opens `↦ 移動…` and the first exit is disabled while a later one is enabled
- **THEN** the first enabled exit is active and nothing is dispatched

### Requirement: Combat details follow the active command frame
The combat command window SHALL show detail for the currently highlighted root command, category, group or skill, never a stale previously selected skill. Command rows SHALL scroll inside a bounded region above the persistent legend. The Skills count SHALL remain the exact committed descriptor count rendered as neutral secondary text.

#### Scenario: Detail copy names only backed things
- **WHEN** root, category, or group detail renders
- **THEN** root detail MAY be client-local explanatory copy of what the command opens or does, never a gameplay value, and category and group detail name that row's committed label and descriptor count

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
Reference drawers and full-screen overlays SHALL present one shared header: a decorative leading glyph, the surface title, an optional subtitle, and one icon-only close control of at least 36x36px carrying an accessible name, in the same order and position on every surface. The body of every reference drawer and utility overlay SHALL be a fully opaque ink panel over a stage-dimming scrim, so no stage, band, or command-line text shows through it.

#### Scenario: The header owns nothing but appearance
- **WHEN** the shared header renders in a drawer or overlay host
- **THEN** it is presentational only: it emits a close request and owns no focus trap, Escape handling, opener record, or open-surface registration, all of which stay with the drawer or overlay host that renders it

#### Scenario: Every header glyph comes from the registry
- **WHEN** a reference drawer or utility overlay declares its header glyph
- **THEN** it comes from the same glyph registry the top navigation draws its entries from, so a surface opened from a navigation control shows that control's glyph; every reference drawer and every utility overlay declares one; no surface falls back to a generic placeholder glyph; and a surface whose body used to render its own title and close control renders them only through the shared header, so each surface carries exactly one title and one close control

#### Scenario: Opacity never rides on blur support
- **WHEN** a reference surface renders over the scrim
- **THEN** a backdrop blur MAY decorate the scrim, but opacity does not depend on `backdrop-filter` support; the recession and the scrim dim only what lies behind the panel, never the panel itself; existing modal focus, close, and restore behavior remain unchanged; and the workspace bounds remain those of the reference drawer and overlay requirements

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
A reference drawer SHALL show the current character's portrait column only when that character is the drawer's subject: the character-status, inventory, and party drawers. The skill book, shop, quest, and world-codex drawers SHALL render no art column and no stand-in illustration, so their content takes the whole workspace width. The character-status hero SHALL name the committed character and supplied title and rank without inventing missing values.

#### Scenario: The art column is bounded over plain ink
- **WHEN** a subject drawer renders its art column
- **THEN** it is bounded to `min(360px, 28%)` of the workspace width on a plain ink ground with no scene illustration behind the portrait, and the content body keeps `min-width: 0` and remains the only scrolling region

#### Scenario: The portrait frame shows exactly one state line
- **WHEN** a portrait frame renders an image or a placeholder
- **THEN** a shown image carries its alternative-text caption, and a placeholder carries only its own label — the entry's placeholder label, else `肖像生成中` for a pending entry, `肖像生成失敗` for a failed one, `肖像載入失敗` after a failed load, and otherwise `無肖像` — so it never claims a pending portrait the payload does not carry; the placeholder initial is the character's name initial

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
An available but empty drawer list — the quest book with no rows, the world codex with nothing discovered, the bag's item section with no rows, and the party with no companions — SHALL render the shared empty guidance: a decorative registry glyph, a short headline, and one line of guidance in a solid ink frame, adding no control of its own.

#### Scenario: The party keeps its invite row
- **WHEN** the party list is available and empty
- **THEN** the empty guidance sits above the unchanged 空位 row, which keeps the only invite control

#### Scenario: Unavailable is never merely empty
- **WHEN** a panel is unavailable, or a section is absent
- **THEN** an unavailable panel retains its authoritative registry reason and is not presented as merely empty, and an absent section keeps its own absence line

#### Scenario: Empty becomes unavailable
- **WHEN** an empty quest panel is replaced by an unavailable panel
- **THEN** empty guidance is replaced by the registered reason with no invented quest/action

#### Scenario: Every empty list shares one guidance form
- **WHEN** the quest book, the codex, the bag's items, or the party is available and empty
- **THEN** each renders the shared glyph, headline, and guidance card, and the empty party additionally keeps its 空位 row

### Requirement: Lineage identity and inventory rarity use backed fields
Lineage rows with the same element/style name SHALL be distinguished using their supplied root-node display names and keep progress beside that identity. Inventory rarity framing SHALL use committed presentation metadata and retain a non-colour label.

#### Scenario: The collapsed chain row lays out its identity and meter
- **WHEN** a collapsed chain row renders
- **THEN** it is about 56px tall and places its progress meter, at most 320px wide, immediately after an identity column shared by every row, followed by its percentage or 已全數見頂; the root-node subtitle is the first node's supplied `display_name_zh`, omitted when absent or equal to the label, and no name is derived from a skill key

#### Scenario: Rarity borders stay visible without colour
- **WHEN** an item's rarity frame renders
- **THEN** each rarity draws a distinct border pattern at a width where the pattern is visible (uncommon dotted and rare dashed at 2px, epic double and legendary ridge at 3px) with a faint tint, and common and unknown items remain neutral

#### Scenario: Same element has two lineages
- **WHEN** two chains share an element label but have distinct root-node display names
- **THEN** both root names are readable beside their own progress

#### Scenario: Unknown item has no rarity
- **WHEN** an inventory row has null presentation
- **THEN** no rarity or item-kind value is inferred from its key

### Requirement: Client help and finite display vocabularies are localized

The client-owned help reference, the combat detail's skill target type and element, and the party drawer's guidance SHALL read in Traditional Chinese rather than English prose or raw identifiers.

#### Scenario: Literal keys and syntax stay verbatim
- **WHEN** localized content renders literal key names or command syntax
- **THEN** key names (Enter, Esc, Tab, Space, Shift, PageUp, PageDown, Home, End, arrows, digits) and command syntax (`help`) stay verbatim, rendered as key caps and code, and protocol identifiers, payloads and user-authored content do not change

#### Scenario: The help reference groups real bindings under a truthful subtitle
- **WHEN** the help reference renders
- **THEN** its rows are grouped by where the keys act (指令列, 指令面板, 閱讀與對話), it names only bindings the client implements — including the ⌨ toggle and the dock's positional picks 1–9 (never a stale range) — and the overlay's header subtitle describes its content (按鍵、指令列與閱讀操作), never another surface's navigation

#### Scenario: Closed sets name skills; unknowns read neutrally
- **WHEN** a skill's `target_spec` or `element` renders, or an identifier falls outside either set
- **THEN** `target_spec` shows by the closed name set 無目標 / 自身 / 單一目標 / 範圍, `element` by the element registry's own name followed by 屬性 (火屬性), and an outside identifier reads 未知目標類型 or 未知屬性, never the raw key and never a guessed mechanic

#### Scenario: The party drawer uses the established term
- **WHEN** the party drawer's follow rules name affinity
- **THEN** they use the established term 羈絆

#### Scenario: Help describes real keys
- **WHEN** the help overlay opens
- **THEN** it names only implemented bindings in localized prose, lists the ⌨ toggle and the 1–9
  positional picks, and preserves literal key and command syntax

#### Scenario: An unknown skill enum reads neutrally
- **WHEN** the combat detail pane shows a skill whose target type or element is outside the known sets
- **THEN** it reads 未知目標類型 or 未知屬性 and shows no raw identifier

### Requirement: The vitals dock stands at the stage's lower-left above the band
The stage SHALL render the vitals surfaces — the condition icon row and the vitals bars — as one bottom-anchored dock in the `vitals` anchor: a left-gutter column standing on the bottom band's upper edge, inset from the stage's left edge by the stage gutter, a quarter of the viewport's width wide, and at whatever compact height its content takes. The dock SHALL be bounded above the band and SHALL scroll internally rather than grow past the band's edge.

#### Scenario: The dock's width stays viewport-relative
- **WHEN** the dock's width resolves at any viewport
- **THEN** it is a viewport-relative width, not multiplied by the chrome factor

#### Scenario: The dock never claims the upper-left corner
- **WHEN** the left column renders
- **THEN** the dock is not top-anchored and claims no stage upper-left corner: at the top of the left column the stage shows only the standing portrait line, and the condition icon row is the dock's topmost content, directly above the bars

#### Scenario: The dock may overlap the portraits' feet
- **WHEN** the dock and the `actor-left` standing portraits render together
- **THEN** the dock MAY overlap the lowest strip of the portraits (the party line's feet); the portraits keep their full standing height and the dock paints above them

#### Scenario: The dock is feathered ink on a brass spine, not a box
- **WHEN** the dock's chrome renders
- **THEN** it does not read as a rectangular box: its ground is the shared panel ink with the backdrop blur, feathered out towards its right and top edges so the scene reads through them; it is mounted on a hairline brass spine down its left side capped by the band's lozenge ornament, with a hairline brass crown fading out along its top; it carries no full border and no square corners; and every island chrome it carries comes from the shared design tokens

#### Scenario: The command line starts past the dock
- **WHEN** the command-line row docks on the same band edge
- **THEN** it begins past the dock's right edge, so the two never intersect

#### Scenario: The interim quickbar holds its place until removed
- **WHEN** the dock renders before `companion-portrait-lineup` removes the interim party quickbar
- **THEN** the quickbar island stands in the `vitals` anchor between the dock and the band

#### Scenario: The dock stands on the band's edge
- **WHEN** the shell renders in exploration mode with the vitals dock visible at 1451x790
- **THEN** the `vitals` anchor's bottom edge coincides with the bottom band's top edge (the dock's own bottom edge does too whenever no interim party quickbar stands below it), the dock's left edge sits at the stage's left gutter and its width is a quarter of the viewport's width (±1.5px), its rendered height is the compact height of the icon row, the readout, and the three lines, and the stage's upper-left corner holds no vitals surface

#### Scenario: The dock covers only the portraits' lowest strip
- **WHEN** the dock is visible and the player's standing portrait renders at 1451x790 and at 2560x1440
- **THEN** the overlap of the two rendered boxes reaches no higher than the portrait's lowest quarter, the portrait's face and torso are fully visible, and neither box moves the other

#### Scenario: The dock stays bounded at the minimum viewport
- **WHEN** the shell renders at 1451x790 with the dock visible and conditions overflowing the row
- **THEN** the dock's box stays inside the left gutter between the top band and the band's top edge, its content scrolls within that bound, and it intersects no other interactive anchor's content

### Requirement: Companion standing portraits line up behind the controlled character in the actor-left anchor
The `actor-left` anchor SHALL render the currently controlled character's standing portrait as the group's rightmost figure with highest baseline z, and SHALL render each companion in committed `party.slots` order to its left, forming an overlapping horizontal row. Each figure SHALL reuse the existing StageActor rendering and remain non-interactive decorative art: no focusable element, no pointer events.

#### Scenario: Portraits resolve through the catalog
- **WHEN** a companion portrait renders
- **THEN** it resolves from `portrait_ref` through `art.portrait_catalog`, falling back to its display name's initial-letter placeholder when null or unresolved

#### Scenario: Every figure shares one size and ground line
- **WHEN** the lineup renders any number of figures
- **THEN** every figure, including the controlled character, has the same full anchor size and ground line — no progressively smaller scale, lift ramp or depth dimming

#### Scenario: The row compresses to stay in the left half
- **WHEN** the row renders at 1451x790, 1741x948 and 2560x1440, in any mode
- **THEN** horizontal overlap compresses as necessary to keep the row inside the stage's left half, preserving a scaled left gutter; a multi-figure group MAY shift horizontally within that half; in dialogue the group compresses overlap to clear the choice list without resizing figures; zero companions render the existing solo portrait at its standard anchor position; the anchor has `overflow: visible`; and the vitals dock MAY cover the lowest strip of feet, never face or torso

#### Scenario: Visibility follows the mode
- **WHEN** the committed mode is exploration, combat, dialogue, or creation
- **THEN** the lineup is visible in exploration, combat and dialogue, and hidden in creation

#### Scenario: A speaking companion rises in z only
- **WHEN** a companion's committed dialogue host identity is the active host speaker in dialogue mode, and when speaking changes or ends
- **THEN** companions use the existing StageActor listener dim otherwise; the speaking companion temporarily receives z above every baseline figure, returning to its exact baseline z when speaking changes or ends, including across possession swaps and lineup count changes; speaking focus changes only dim and z, never position, lift or size, and remains correct at off/reduced motion; and the controlled figure retains its existing speaking and beat behavior

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

### Requirement: Possession moves the possessed companion to the group's front
While the possession banner is available, the possessed companion SHALL occupy the rightmost slot and A SHALL occupy exactly that companion's former slot, without moving the remaining companions. Release SHALL restore both original positions.

#### Scenario: Identity joins and art resolve stay committed-only
- **WHEN** the front figure's identity is joined and its art resolved
- **THEN** the committed bounded-string `status.actor.identity` (the controlled session actor, not the hybrid resource owner) joins to decimal-string-normalized integer party identities, and only committed catalog references and the roster portrait resolve; when no party row matches, the controlled front uses a truthful null-art placeholder labelled by the committed banner's host name, never A's portrait or an invented catalog key

#### Scenario: Possessing a companion moves it to the front
- **WHEN** the possession banner becomes available for the party's second companion 蕾娜 while the party has two slots
- **THEN** 蕾娜's figure renders frontmost, the player character's figure renders in the companion row, and the first companion keeps its behind position

#### Scenario: Release restores the player to the front
- **WHEN** the possession banner commits its unavailable form
- **THEN** the player character's figure returns to the front position and the released companion's figure returns to its companion-row position

#### Scenario: A possessed companion without a portrait still fronts
- **WHEN** the possession banner names a companion whose `portrait_ref` is null
- **THEN** the front figure renders the truthful initial-letter placeholder rather than the player's portrait

### Requirement: Condition detail preserves equipment provenance without hiding gameplay conditions
The dock's existing tooltip, overflow detail, and accessible condition names, and the complete character-status condition roster SHALL preserve the label, severity, supplied duration and exact modifier values of every committed condition. These surfaces SHALL disclose all equipment source labels supplied by `provenance.equipment_sources`, without guessing a label from an item key or requiring another panel.

#### Scenario: Provenance is stated as committed
- **WHEN** a condition's detail discloses its provenance
- **THEN** mixed provenance identifies that an independent source also applies, unknown provenance states neutrally that the source is unavailable, and non-equipment provenance claims no equipment source

#### Scenario: Hidden and shared instances stay readable
- **WHEN** the contextual dock is hidden with an equipment-only condition committed, or distinct committed buff instances share a code
- **THEN** equipment-only conditions remain available in the full status surface, and shared-code instances remain individually readable with their own source and duration in normal and overflow detail paths

#### Scenario: Hidden equipment condition remains inspectable
- **WHEN** full-health exploration has only a synthetic equipment-origin warning and the player opens character status
- **THEN** the dock remains hidden and the full roster contains that warning with its original severity, values, and registry-backed equipment source label

#### Scenario: Another trigger reveals equipment detail
- **WHEN** depleted resources reveal the dock while an equipment-origin adverse condition remains committed
- **THEN** its icon, tooltip, overflow detail when applicable, and accessible name retain the condition's exact data and identify its supplied equipment source

#### Scenario: Same-definition instances disclose distinct sources
- **WHEN** attached and independent buff instances share a condition code but have different durations and provenance
- **THEN** both rows remain readable and focusing or hovering either row discloses that row's source and duration, including when one or both are in overflow

#### Scenario: Independent source remains explicit for a mixed row
- **WHEN** a condition has mixed provenance naming two synthetic worn contributors
- **THEN** its detail identifies both supplied item labels and an independent source without downgrading the adverse severity

#### Scenario: Detail works when the character panel is unavailable
- **WHEN** combat reveals the dock and status supplies equipment provenance while the character panel is unavailable
- **THEN** condition detail still uses the status-supplied source labels and invents no equipment data from the unavailable panel
