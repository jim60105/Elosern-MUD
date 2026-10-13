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
- **WHEN** the shell renders at 1451x790 and the player moves through the exploration scene overview, a person's verb card, the waiting frame, an empty pane host, the deepest combat frame, and a dialogue exchange with four picks
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
- **WHEN** the focused element belongs to a surface that the incoming mode hides, including a scene-overview chip or a person's verb card when the incoming mode is dialogue
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

### Requirement: The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance
The action dock SHALL carry one shortcut-legend strip at the bottom of its content column, below the scrolling region, in combat mode (never in creation mode, and never visibly in dialogue mode, where the strip is hidden with the collapsed command region). The legend SHALL render exactly once as visible content and SHALL be the only element carrying the legend's test hook; no root command list or pane SHALL carry a second copy.

#### Scenario: The legend matches the reference dock hint
- **WHEN** the legend strip renders
- **THEN** it matches `docs/design/elosern-redesign/index.html`'s dock hint in wording and structure: the text `數字鍵 1–9 ‧ ` followed by an `<kbd>` element naming `Enter` and the verb `執行`, the separator `‧`, and an `<kbd>` element naming `Esc` and the verb `返回`; the legend renders with the reference's `<kbd>` treatment (monospace face, `--ink-780` ground, 2px bottom border); and the dock carries no dialogue-mode legend variant

#### Scenario: The legend never lies
- **WHEN** a key, gesture, or affordance is named in the legend, or when a named affordance's behaviour changes
- **THEN** the legend names no key, gesture, or affordance this client does not implement or that no longer behaves as named, and advertises no implemented affordance the reference's legend does not name; when a named affordance's behaviour changes (for example, a control that used to open a surface and now only moves focus into an always-present one), the legend's wording is updated in the same change that alters the behaviour

#### Scenario: Digits pick and confirm the frame's first nine entries
- **WHEN** the dock owns keyboard focus (the key target is not editable) and the player presses `1`–`9`
- **THEN** the press moves the current dock frame's focus onto its first nine entries (1-indexed, rendered order; a frame's `back` row takes the slot of its rendered position) — except in the exploration screen, where the presence rail owns the digits as `webclient-presence-rail` defines: they pick its visible entries, never the overview's footer chips or the rows of its waiting and suggestions frames, and exits belong to the separate compass and activates the entry through the same confirm path `Enter` uses — a disabled entry shows its explanation and submits nothing, an in-flight entry stays locked, and a held repeat is suppressed; the slots address the frame's rendered entries, disabled ones included

#### Scenario: Digits outside the dock's claim fall through
- **WHEN** dialogue mode holds — or a digit's entry does not exist (a frame with fewer rendered entries, dialogue mode, or the pre-session empty stack)
- **THEN** in dialogue mode neither the dock's entries nor the keyboard router claims any digit: the digits `1`–`N` belong to the dialogue choice list while it holds focus, which handles them itself as "Dialogue choices appear centred over the stage after the line is fully read" defines; and an unclaimed digit falls through to the text / command-history path

#### Scenario: The legend renders once
- **WHEN** the dock renders in combat mode and later changes to exploration or dialogue
- **THEN** combat carries exactly one legend strip and no duplicate; exploration renders no legend element and dialogue keeps its strip hidden with the command region

#### Scenario: The legend matches the reference wording and kbd structure
- **WHEN** the dock renders its legend strip in combat mode
- **THEN** the legend reads `數字鍵 1–9 ‧ Enter 執行 ‧ Esc 返回` with `Enter` and `Esc` rendered as
  styled `<kbd>` elements and no other key named

#### Scenario: A digit picks its row
- **WHEN** the presence rail holds two people and one object beside a compass with three exit targets, and the player presses `2`, then after Escape presses `3`
- **THEN** `2` opens the second person's verb card once and `3` submits the object's `explore.look` once; compass targets and footer chips occupy no digit slot

#### Scenario: A digit beyond the frame's rows is unclaimed
- **WHEN** the current dock frame has fewer rendered entries than the pressed digit and the command
  field is not focused
- **THEN** the digit is not claimed, the frame's focus is unchanged, and nothing submits; in the exploration screen the presence rail instead claims every digit while it is on the stage, so a digit past its entries does nothing and none falls through to the footer

#### Scenario: Digits address the caption's picks while the dialogue variant presents
- **WHEN** the dialogue choice list shows four picks with focus on the list, the command region is
  collapsed, and the player presses `4` and `5`
- **THEN** the `4` press activates pick four through the same dispatch entry, the `5` press is handled
  by neither the list nor the keyboard router and falls through, and the hidden dock's focus and frame
  are unchanged

### Requirement: A breadcrumb derived from the router names the player's position at depth

The dock SHALL render a breadcrumb line whenever the router's menu stack is deeper than its root frame, and SHALL hide it entirely at the root frame. The breadcrumb SHALL name the parent frame and the current frame, with the current frame visually distinguished, and SHALL carry a back control. Activating the back control SHALL perform exactly the same operation the Escape key performs — it SHALL pop exactly one menu level and SHALL NOT dispatch any action.

#### Scenario: The verb popover names its target once
- **WHEN** a person's verb card is open over the stage
- **THEN** the breadcrumb does not render, because the card is client-local and pushes no router frame, and the person is named once, by the message window's speaker line; the card's `✕ 返回` row and Escape are its back paths, and every submenu keeps the breadcrumb

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
- **WHEN** a person's verb card's `✕ 返回` row is the card's active row
- **THEN** it carries the card's active-row treatment, and Enter or a click on the row closes the card without popping a router level and returns focus to the rail entry that opened it

#### Scenario: The breadcrumb tracks a target frame's own name
- **WHEN** the player opens a frame scoped to one target
- **THEN** the breadcrumb's current segment is that target's server-authored display name
- **WHEN** the player opens an interact target's verb card from the presence rail
- **THEN** the message window's speaker line names that target's server-authored display name, no breadcrumb is rendered, and the command region states no name

#### Scenario: The breadcrumb cannot drift from the router
- **WHEN** a panel replacement pops or replaces the current frame
- **THEN** the breadcrumb's depth and labels match the router's frame stack in the same render, with no interval in which they describe a frame the router has already left

### Requirement: Dock panes render a per-kind vocabulary from backed fields only

The dock's row region SHALL render the current frame in a form chosen for what that frame contains, using one shared row renderer for every form so the focused marker, the disabled marker and its `（無法使用）` suffix, the accessible disabled association, and the row identity attribute are defined in exactly one place.

#### Scenario: The form set is fixed
- **WHEN** the row region selects a form
- **THEN** the forms are: footer chips for the scene overview beside the exit compass; the waiting cards; suggestion cards for the suggestions frame; and the combat forms specified elsewhere in this capability

#### Scenario: Exploration frames never regress to grids or nav lists
- **WHEN** any exploration frame renders
- **THEN** it renders no exit-outlet grid and no navigation-row list: exits are targets of the separate compass, and a host's conversation topics are the dialogue surface's choices, never a dock frame

#### Scenario: An enabled exit chip names direction by glyph and destination by text
- **WHEN** the compass aims an enabled angled exit
- **THEN** its pip marks the bearing and the shared readout names the committed destination with its octant glyph, without repeating a direction-word label

#### Scenario: Direction glyphs come only from the canonical table
- **WHEN** an exit label falls outside the fixed client-side table of canonical direction words
- **THEN** no direction is guessed from the label: a usable map bearing supplies its octant glyph, otherwise it becomes a portal whose fallback text is the verbatim label

#### Scenario: An unknown destination falls back without doubling labels
- **WHEN** an enabled exit's destination is absent from the committed local map
- **THEN** the readout uses the exit's own label once and invents no destination name

#### Scenario: A disabled exit chip keeps its own label and marker
- **WHEN** a compass target is disabled
- **THEN** its hollow dashed marker remains visible and aimable, and the readout shows `無法通行` with the unchanged server-authored reason instead of promising a destination

#### Scenario: Exit chip focus and disabled reasons stay honest
- **WHEN** the compass aims an exit or explains a disabled target
- **THEN** shape and fill mark its aim, the shared polite live readout exposes the unchanged disabled reason, a disabled target submits nothing, and an enabled activation keeps the move payload unchanged

#### Scenario: Chips and rows render only backed fields
- **WHEN** any chip or row renders
- **THEN** it renders only fields the committed payload carries: its server-authored name and, where its form has one, an optional sub-line composed of such fields; none renders a statistics line, a portrait, or any other element for which the payload has no field — where the design draft shows such an element it is absent rather than emptied or mocked

#### Scenario: Icons are decorative and key-selected
- **WHEN** a chip or row shows an icon or glyph
- **THEN** it is decorative, hidden from assistive technology, always accompanies a real text label, and is selected only from stable server-authored keys or the direction table — never from free text such as a display name

#### Scenario: The verb popover heads with its target
- **WHEN** a person's verb card renders over the stage
- **THEN** the message window's speaker line names the person it is scoped to, taken from the committed panel's server-authored display name, while the card lists that person's rows

#### Scenario: The disabled contract holds in every form
- **WHEN** a disabled entry renders in any row or chip form
- **THEN** it keeps the existing disabled contract: it remains focusable by arrow keys and by pointer, keeps its accessible disabled state and its server-authored explanation, and submits nothing

#### Scenario: A move row names where it goes
- **WHEN** the compass aims an enabled exit whose destination node is present in the committed local map
- **THEN** the shared readout shows that node's display name with the target's angled or portal glyph, and activation submits the unchanged move payload

#### Scenario: A non-canonical exit keeps its own name
- **WHEN** an exit has no usable map bearing and its label is outside the canonical direction table
- **THEN** it becomes a portal, keeps its own label as the destination-name fallback, and no direction is guessed from that label

#### Scenario: An unknown destination falls back to the exit's own label
- **WHEN** an enabled canonical-direction target has no destination node in the committed local map
- **THEN** the readout shows its octant glyph and its own label as the fallback text, without inventing a node name

#### Scenario: A disabled exit never loses its disabled marker to a known destination
- **WHEN** a disabled exit's destination node is present in the committed map
- **THEN** its target remains visibly disabled and its readout shows the server reason in the warn tone, never replacing that explanation with the destination name

#### Scenario: A focused move row is not double-marked
- **WHEN** a compass target is aimed
- **THEN** its aim wedge, pip or bead treatment, and knob carry the aim, and no legacy chip-focus glyph is added beside its readout glyph

#### Scenario: The move frame has no companion panel
- **WHEN** the exploration root renders with any overview chip focused
- **THEN** the compass occupies the left side and the shared readout and overview occupy the right column; no exit-outlet grid or detail aside renders

#### Scenario: A row renders only backed fields
- **WHEN** the presence rail renders a look-only entry for a present entity
- **THEN** the entry shows the entity's display name and its initial, and shows no statistics line, because the exploration payload carries no such field; a face crop shows only when the committed panel names a portrait the art catalog resolves

#### Scenario: A target-affordance frame names its target
- **WHEN** the player opens an interact target's verb card
- **THEN** the message window names that target as the speaker above the page while the card lists the target's server-authored rows

#### Scenario: A disabled row in any pane stays readable
- **WHEN** a disabled row or chip is focused in any form, by arrow key or by pointer
- **THEN** it keeps focus, exposes its accessible disabled state and its server-authored explanation, and no action is submitted

### Requirement: The action dock fills the band's command region at a fixed size
The action dock SHALL fill the bottom band's command region — the right third of the band, or the whole band in creation mode — at the band's fixed height, and SHALL NOT be a floating panel placed elsewhere on the stage. Its box SHALL be the command region's box in exploration, combat, and creation mode and for every frame, and no surface outside the band SHALL be positioned from the frame the dock currently carries.

#### Scenario: No frame moves or resizes the dock
- **WHEN** the dock carries the scene overview (with or without a person's verb card open over the stage), the waiting frame, the combat frames, the skill master-detail, the destructive confirmation, or an empty pane host
- **THEN** no frame widens, heightens, shortens, or moves its box

#### Scenario: Dialogue hides the dock with the region
- **WHEN** the committed mode is dialogue
- **THEN** the command region is collapsed and the dock is hidden with `display:none` together with it, as "The command region collapses in dialogue mode and the message window spans the band" states; it is not rendered anywhere else in that mode

#### Scenario: Fixed chrome surrounds one scrolling region
- **WHEN** the dock's content column lays out
- **THEN** it is laid out as fixed chrome — the combat root's vertical command list in combat mode and no bar in exploration mode, an optional breadcrumb line, and the shortcut-legend strip at the bottom in combat only — around one remaining region that holds the current frame's rows or chips, and that region is the surface's only scrolling area, so no dock content is ever pushed outside the command region

#### Scenario: Popovers and wide frames stay inside the region
- **WHEN** a person's verb card renders, or a frame's content does not fit the region's width
- **THEN** the card renders centred over the stage in the `choices` anchor, outside the command region, scrolling inside its own card when its rows exceed it, while the command region keeps its box, and the wide frame wraps or collapses its own columns inside the region, never overflowing it horizontally

#### Scenario: One dock element persists across every mode
- **WHEN** the committed mode changes, including into or out of dialogue
- **THEN** the panel is the same single `#action-dock` element in every mode, carrying its existing tab index, its `data-mode` attribute and its role as the documented focus forwarding target, with the compass owning exploration-root focus and the active row container owning other dock frames, and it is not remounted

#### Scenario: The presentation stays readable beyond colour
- **WHEN** the command region and its band render
- **THEN** the command region uses the current charcoal-and-gold presentation, the band that contains it paints the reference's band chrome, and selected actions remain distinguishable by text and shape as well as their gold or warm-red emphasis

#### Scenario: The command region is the band's right third
- **WHEN** the shell renders in exploration mode at 1451x790 and at 2560x1440
- **THEN** the `#action-dock` element lies inside the band's command region, the region's left edge is at two thirds of the stage width and its right edge at the stage's right edge (each ±1px), and the dock covers neither the message region nor the command line

#### Scenario: No frame resizes the command region
- **WHEN** the dock moves at 1451x790 from the scene overview to a person's verb card over the stage, to the waiting frame, and, in combat, to the deepest skill target frame
- **THEN** the command region's rendered box is identical (±1px) in all four states, the band's height is unchanged, and the verb card lies centred over the stage above the band

#### Scenario: An overflowing frame scrolls inside the panel
- **WHEN** the current frame holds more rows than the dock's row region can display
- **THEN** the row region scrolls internally, the dock's chrome (the combat root list, the breadcrumb,
  and the combat-only legend strip) stays fixed, and no row or chip is rendered outside the command region

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
- **THEN** on entering, focus moves to the message window's page surface before the region is hidden; on leaving, focus moves to the exit compass once the region is rendered again

#### Scenario: The router claims only the slash in dialogue
- **WHEN** the mode is `dialogue`
- **THEN** the keyboard router claims only `/` (the command-line opener); every other key is unclaimed by the dock router, so no key moves the hidden dock's focus, pushes or pops a frame, or activates a hidden entry; the keys the dialogue choice list handles never reach the router, and Enter and Space on the focused page surface keep their reading meaning

#### Scenario: Entering dialogue collapses the command region
- **WHEN** the player activates 交談 on a host's verb card at 1451x790 and the commit makes the mode `dialogue`
- **THEN** from the commit's frame the band's command region and the `#action-dock` element are out of the accessibility tree and the tab order, the message region spans the band's whole width at 220px (±1px) height, the region is `visibility: hidden` once its slide ends, focus is on the message window's page surface while the greeting is read, and focus moves to the dialogue choice list when the greeting's last page is fully shown

#### Scenario: Leaving dialogue restores the overview without a remount
- **WHEN** the player activates the exit row and the commit returns the mode to `exploration`
- **THEN** the same `#action-dock` element is back in the accessibility tree in the commit's frame, slides back into the command region at the scene overview with no card open, and focus is on the exit compass

#### Scenario: Keys never drive the hidden dock
- **WHEN** the mode is dialogue, focus is on the document body, and the player presses ArrowRight, Enter, and Escape
- **THEN** none of the keys is claimed by the dock router, the router's focused key and depth are unchanged, and no `ui_action` is emitted

#### Scenario: Slash still opens the command line in dialogue
- **WHEN** the mode is dialogue, no editable control is focused, and the player presses `/`
- **THEN** the command line expands and focus moves into its input field with no literal `/` inserted

#### Scenario: Movement stays reachable during a conversation
- **WHEN** a dialogue session is live and the player activates an adjacent minimap node
- **THEN** the move dispatches exactly as in exploration mode, the movement settlement clears the session through the existing seam, the committed mode returns to `exploration`, and the command region renders the new room's overview

### Requirement: The bottom band separates material and focus without obscuring controls
The fixed bottom band SHALL provide a continuous ink-and-gold reading surface with a decorative stage seam and aligned message-control and shortcut rows. Page text, command rows and cards SHALL never paint over these reserved controls. Only the active control SHALL carry the strongest focus treatment; the command field SHALL expose one clear focus frame.

#### Scenario: Popover text is isolated
- **WHEN** a person's verb card opens over the stage with populated scene chips in the command panel
- **THEN** no stage or chip text shows through the card, the person is named once by the speaker line, and the inert command panel's chips cannot activate

#### Scenario: Dense command content is bounded
- **WHEN** a frame contains more rows than fit
- **THEN** its own row region scrolls while the legend and message controls remain visible on one baseline

#### Scenario: Motion is reduced
- **WHEN** the player changes command frames with reduced motion or off
- **THEN** reduced uses no 3D rotation or wipe and off commits immediately without losing focus
