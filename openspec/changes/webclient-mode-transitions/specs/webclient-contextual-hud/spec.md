## MODIFIED Requirements

### Requirement: The command region collapses in dialogue mode and the message window spans the band
While the committed mode is `dialogue`, the bottom band's command region SHALL be collapsed and the
message region SHALL span the band's whole width at the band's fixed height from the commit's frame. The
collapsed region and the action dock inside it SHALL leave the accessibility tree, the tab order, and
pointer hit-testing from the commit's frame; the region SHALL then slide out to the right and fade over
the panel duration of the client's motion level, drawn over the widened message region, and SHALL be
`visibility: hidden` once that slide ends, so it contributes nothing visible. Leaving dialogue SHALL
bring the region back into reach in the commit's frame and slide it back in from the right. At
`reduced` the region only fades, within 150ms, and at `off` it hides and returns in the commit's frame. The dock SHALL stay the same mounted `#action-dock`
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

### Requirement: Surface visibility is gated by the committed game mode
The shell SHALL expose the committed mode on the stage root as `data-elosern-mode`, and surface
visibility SHALL be derived from that single attribute. A surface hidden for the current mode SHALL be
removed from rendering with `display:none` — never dimmed, never merely visually hidden — so it leaves
the accessibility tree and the tab order. The one exception is the band's command region in dialogue
mode, which animates out as "The command region collapses in dialogue mode and the message window spans
the band" defines: it leaves the accessibility tree, the tab order, and pointer hit-testing at the
commit, and is `visibility: hidden` once its slide ends. The matrix SHALL be:

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
| action dock (band command region) | visible | visible | **hidden** (command region collapsed: inert at commit, slides out, then `visibility: hidden`) | visible (creation form, full band width) |
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

## ADDED Requirements

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
its first frame, and the dock is focusable from the first frame of its return. The flash, the veil, and
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
