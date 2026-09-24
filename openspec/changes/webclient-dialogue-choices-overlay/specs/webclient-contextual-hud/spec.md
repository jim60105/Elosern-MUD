## MODIFIED Requirements

### Requirement: The WebClient renders a full-bleed cinematic stage with anchored HUD surfaces
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
SHALL be `min(62vh, 680px)` tall but never taller than the stage box, SHALL be inset 6% of the stage
width from its own side, and SHALL never cover the band. The `actor-left` anchor SHALL carry the
player's stage actor — the current roster character's portrait, resolved exactly as the stage
portrait was before this requirement, with the truthful placeholder when no image exists — in
exploration, dialogue, and combat mode. The `actor-right` anchor SHALL carry the dialogue host's stage
actor while the committed mode is `dialogue` and the committed `dialogue` panel is available, and SHALL
carry no content in every other state. Both stage actors follow "Stage actors present the player and the
dialogue host with a speaking state". The portrait anchors are non-interactive art: they SHALL carry no
focusable element and SHALL NOT intercept pointer events, and they MAY sit behind the HUD islands, the
`choices` anchor, and the command-line row.

The `choices` anchor SHALL render only in dialogue mode. It SHALL be horizontally centred on the stage
box, at most `min(560px, 40%)` of the stage width wide, vertically centred in the stage box and bounded
by it, above the portrait anchors; when its content is taller than the stage box allows it SHALL
scroll internally, and it SHALL NOT grow into the top band or the bottom band.

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

#### Scenario: The choice list sits over the stage between the portraits
- **WHEN** the dialogue choice list renders four picks and its three trailing rows at 1920x1080 and at 1280x720 with the vitals island, the minimap, and the party island present
- **THEN** the `choices` anchor is horizontally centred on the stage box (±1px), lies entirely inside the stage box, intersects no `place`, `vitals`, `map`, band, or command-line anchor, and every row is reachable, scrolling inside the anchor at 1280x720 if needed

### Requirement: Surface visibility is gated by the committed game mode
The shell SHALL expose the committed mode on the stage root as `data-elosern-mode`, and surface
visibility SHALL be derived from that single attribute. A surface hidden for the current mode SHALL be
removed from rendering with `display:none` — never dimmed, never merely visually hidden — so it leaves
the accessibility tree and the tab order. The matrix SHALL be:

| Surface | exploration | combat | dialogue | creation |
|---|---|---|---|---|
| place card (location, world time) | visible | visible | visible | hidden |
| message window (band message region) | visible | visible | visible (whole band width, paged, name plate) | hidden |
| dialogue choice list (`choices` anchor, centred over the stage) | not rendered | not rendered | once the current response's last page is fully shown, while no action is in flight | not rendered |
| vitals island (vitals/conditions) | by the vitals rule | visible | by the vitals rule | hidden |
| minimap island | visible | **hidden** | visible | hidden |
| party quickbar island | while the party is non-empty | while the party is non-empty | while the party is non-empty | hidden |
| objective line (under the minimap) | visible | hidden | hidden | hidden |
| player standing portrait (`actor-left`) | visible | visible | visible (dimmed while the host speaks) | hidden |
| dialogue host standing portrait (`actor-right`) | not rendered | not rendered | while the `dialogue` panel is available (dimmed while the player speaks) | not rendered |
| action dock (band command region) | visible | visible | **hidden** (command region collapsed) | visible (creation form, full band width) |
| command-line toggle (⌨, message region's bottom-right) | visible | visible | visible | hidden |
| log control (日誌, beside the command-line toggle) | visible | visible | visible | hidden |
| command line (row on the message region's top edge) | while expanded | while expanded | while expanded | hidden |
| scene backdrop | visible (exploration stage) | visible (combat stage) | visible (unchanged art) | visible |

While the committed mode is `dialogue` the scene backdrop SHALL keep rendering its committed
exploration art truthfully — the dialogue's focus is carried by the stage actors, the name plate, and
the message window, and the choice list, not by mutating the backdrop. Per-surface requirements that name their own visible-mode
sets SHALL stay consistent with this matrix. A cell that names a data rule instead of `visible` means
the surface is shown in that mode only while its own requirement's rule holds for the committed state,
and is otherwise hidden the same way (`display:none`, or not rendered at all where that requirement
says so). The command line's `while expanded` cell is such a rule: its own requirement defines when the
row is expanded, and a collapsed row is hidden with `display:none` exactly like a mode-hidden surface.
Each playing mode has one focus home: the action dock in exploration, combat, and creation mode, and
the message window's focus target in dialogue mode, as "The command region collapses in dialogue mode
and the message window spans the band" defines. When a mode change, a committed revision that turns a
surface's data rule false, or a collapse of the command line hides the surface that currently holds
focus, the shell SHALL move focus to the focus home of the mode being entered or kept before the
surface is removed, using the existing focus-restore path. A mode change into creation SHALL also
collapse the command line, so leaving creation never reveals an expanded row.

#### Scenario: The minimap disappears in combat
- **WHEN** the committed mode changes from exploration to combat
- **THEN** the minimap island is absent from the DOM layout and from the tab order, and it is not merely dimmed

#### Scenario: The minimap returns on leaving combat
- **WHEN** the committed mode changes from combat back to exploration
- **THEN** the minimap island renders again with the committed `local_map` payload

#### Scenario: Focus is rescued before its surface is hidden
- **WHEN** the focused element belongs to a surface that the incoming mode hides, including a scene-overview chip when the incoming mode is dialogue
- **THEN** focus is moved to the incoming mode's focus home before the surface is removed, and no focus is lost to the document body

#### Scenario: Creation mode presents only the creation surfaces
- **WHEN** the committed mode is creation
- **THEN** the place card, the message window, the command-line toggle, the log control, the `vitals` and `map` anchors with every island in them, the player standing portrait, and the command line are absent, and the action dock renders the creation form across the whole bottom band

#### Scenario: Dialogue mode keeps the cockpit visible
- **WHEN** the committed mode changes from exploration to dialogue with an available `dialogue` panel
- **THEN** the place card, message window, minimap, player standing portrait, command-line toggle, and log control all
  remain rendered, the dialogue host's standing portrait is rendered in `actor-right`, the command line keeps its expanded or collapsed state, the objective line is hidden with `display:none` because only exploration shows it, the vitals and party islands keep following the same data rules as in
  exploration, the action dock is hidden with `display:none` together with the band's command region while the message window spans the whole band with the host's name plate, and the `#action-dock` element is not removed from the document

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

### Requirement: The message window presents the current response one page at a time in the band's message region
The narrative SHALL render as a message window that fills the bottom band's message region — the left
two thirds of the band, or the whole band in dialogue mode, at the band's fixed height — drawn with the
reference's caption panel
treatment: charcoal panel fill, a hairline border, shared radius and restrained shadow. The window
SHALL never grow into the stage and SHALL never change size with its content. In every mode, dialogue
included, the window SHALL present exactly one page of the current response at a time, paged as
`webclient-input-narrative` defines and revealed as its typing requirement defines, and SHALL NOT
present earlier responses: they remain readable in the full-log surface. Page text SHALL be set in the
serif reading face at 28px at the 1920x1080 reference size and the default prose scale, SHALL scale
with the viewport height and with the client's prose scale, and SHALL hold at most 42 CJK characters
per line in every mode, including the whole-band width of dialogue mode.

The window's lower edge SHALL keep a control strip in which no page text renders. The strip SHALL
hold a page marker and, at its right end, a labelled `日誌` control beside the command-line toggle.
The page marker SHALL render only while the page on screen is fully shown, and SHALL be absent while
the page is typing. When rendered, it SHALL read `▼` while the current response has further pages and
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
` · 羈絆 <stage>` only when `bond_stage` is non-null; the window's text area below the plate SHALL
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
- **THEN** the window shows only the first page of the latest response, and no line of the two
  earlier responses is rendered in the window

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
- **THEN** the window spans the whole band, shows the name plate `灰婆婆 · 羈絆 親睦`, types page 1 with no marker until it is fully shown, shows `▼`, advances on Enter on the page surface to page 2, and shows `■` once page 2 is fully shown, with no choice row inside the window at any point

#### Scenario: An unbonded host's plate names only the host
- **WHEN** mode `dialogue` commits with `bond_stage` `null`
- **THEN** the name plate reads the host's `display_name` alone and carries no `羈絆` text

#### Scenario: A transiently unavailable panel shows no plate
- **WHEN** mode is `dialogue` but the committed panel is the unavailable form
- **THEN** no name plate renders and the window shows the current response's pages with their page marker

### Requirement: The dock's shortcut legend names only real keyboard behaviour and renders as one visible instance
The action dock SHALL carry one shortcut-legend strip at the bottom of its content column, below the
scrolling region, in exploration and combat mode (never in creation mode, and never visibly in
dialogue mode, where the strip is hidden with the collapsed command region), matching
`docs/design/elosern-redesign/index.html`'s dock hint in wording and structure: the text
`數字鍵 1–9 · ` followed by an `<kbd>` element naming `Enter`
and the verb `執行`, the separator `·`, and an `<kbd>` element naming `Esc` and the verb `返回`.
The legend renders
with the reference's `<kbd>` treatment (monospace face, `--ink-780` ground, 2px bottom border).
The legend SHALL render exactly once as visible content and SHALL be the only element carrying the
legend's test hook; no tab bar SHALL carry a second copy. The dock SHALL NOT carry a dialogue-mode
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
  legend strip, no tab bar or pane renders a duplicate copy, and in dialogue mode the strip is hidden
  with the command region and no other element shows a legend

#### Scenario: The legend matches the reference wording and kbd structure
- **WHEN** the dock renders its legend strip in exploration or combat mode
- **THEN** the legend reads `數字鍵 1–9 · Enter 執行 · Esc 返回` with `Enter` and `Esc` rendered as
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

### Requirement: The command region collapses in dialogue mode and the message window spans the band
While the committed mode is `dialogue`, the bottom band's command region SHALL be collapsed: it and
the action dock inside it SHALL be hidden with `display:none`, and the message region SHALL span the
band's whole width at the band's fixed height. The dock SHALL stay the same mounted `#action-dock`
element, its router SHALL keep the exploration scene overview as its only frame (the reset on entering
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
- **THEN** the band's command region and the `#action-dock` element are hidden with `display:none`, the message region spans the band's whole width at 300px (±1px) height, focus is on the message window's page surface while the greeting is read, and focus moves to the dialogue choice list when the greeting's last page is fully shown

#### Scenario: Leaving dialogue restores the overview without a remount
- **WHEN** the player activates the exit row and the commit returns the mode to `exploration`
- **THEN** the same `#action-dock` element is rendered in the command region at the scene overview with no popover open, and focus is on the action dock

#### Scenario: Keys never drive the hidden dock
- **WHEN** the mode is dialogue, focus is on the document body, and the player presses ArrowRight, Enter, and Escape
- **THEN** none of the keys is claimed by the dock router, the router's focused key and depth are unchanged, and no `ui_action` is emitted

#### Scenario: Slash still opens the command line in dialogue
- **WHEN** the mode is dialogue, no editable control is focused, and the player presses `/`
- **THEN** the command line expands and focus moves into its input field with no literal `/` inserted

#### Scenario: Movement stays reachable during a conversation
- **WHEN** a dialogue session is live and the player activates an adjacent minimap node
- **THEN** the move dispatches exactly as in exploration mode, the movement settlement clears the session through the existing seam, the committed mode returns to `exploration`, and the command region renders the new room's overview

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
narrative, the dialogue variant, or the dock frame.

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

## ADDED Requirements

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
SHALL activate the focused row; digit `1`–`N` SHALL activate pick N directly; a held key's auto-repeat
SHALL NOT activate. Every key the list handles SHALL be consumed by it and SHALL NOT reach the keyboard
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

## REMOVED Requirements

### Requirement: The feed presents the dialogue variant from the committed panel
**Reason**: The AVG stage design (`docs/superpowers/specs/2026-09-23-webclient-avg-stage-redesign-design.md` §8.2) pages the session line like any response and moves the choices out of the message window, centred over the stage, after the last page is read. The unpaged variant that rendered the reply box and rows inside the window is deleted, so the requirement's subject no longer exists.
**Migration**: "Dialogue choices appear centred over the stage after the line is fully read" (this capability) owns the pick, free-dialogue, exit, and new move rows and their dispatch. "The message window presents the current response one page at a time in the band's message region" owns the name plate and the paged line. Tests annotated with the old ID re-anchor to the choices requirement.
