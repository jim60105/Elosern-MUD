## MODIFIED Requirements

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
| command-line toggle (⌨, message region's bottom-right) | visible | visible | visible | hidden |
| command line (row on the message region's top edge) | while expanded | while expanded | while expanded | hidden |
| scene backdrop | visible (exploration stage) | visible (combat stage) | visible (unchanged art) | visible |

While the committed mode is `dialogue` the scene backdrop SHALL keep rendering its committed
exploration art truthfully — the reference's dialogue focus is carried by the dialogue box
itself, not by mutating the backdrop. Per-surface requirements that name their own visible-mode
sets SHALL stay consistent with this matrix. A cell that names a data rule instead of `visible` means
the surface is shown in that mode only while its own requirement's rule holds for the committed state,
and is otherwise hidden the same way (`display:none`, or not rendered at all where that requirement
says so). The command line's `while expanded` cell is such a rule: its own requirement defines when the
row is expanded, and a collapsed row is hidden with `display:none` exactly like a mode-hidden surface.
When a mode change, a committed revision that turns a surface's data rule false, or a collapse of the
command line hides the surface that currently holds focus, the shell SHALL move focus to the action
dock before the surface is removed, using the existing focus-restore path. A mode change into creation
SHALL also collapse the command line, so leaving creation never reveals an expanded row.

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
- **THEN** the place card, the narrative caption, the command-line toggle, the `vitals` and `map` anchors with every island in them, the player standing portrait, and the command line are absent, and the action dock renders the creation form across the whole bottom band

#### Scenario: Dialogue mode keeps the cockpit visible
- **WHEN** the committed mode changes from exploration to dialogue
- **THEN** the place card, narrative caption, minimap, player standing portrait, action dock, and command-line toggle all
  remain rendered, the command line keeps its expanded or collapsed state, the objective line is hidden with `display:none` because only exploration shows it, the vitals and party islands keep following the same data rules as in
  exploration, the action dock keeps its regular exploration form
  with every ordinary root affordance present, and only the narrative presentation changes

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

### Requirement: The map, settings, and help surfaces are reachable from the live client
The map, settings and help surfaces SHALL each be reachable from the running client by a labelled
control, not only from the component showcase. The minimap island SHALL carry a labelled control that
opens the map surface, rendered as a sibling of its map canvas rather than as a wrapper around its
actionable nodes; the island's non-interactive body MAY additionally open the same surface on pointer
click, which SHALL NOT replace or wrap the labelled control. The top navigation bar's labelled 設定
control and the 說明 control in its tool group SHALL open the settings and help surfaces, in every mode
that renders the top navigation bar, whether the command line is expanded or collapsed.

The map surface SHALL render the committed `local_map` payload through the same component the minimap
island renders, and SHALL re-render its available and unavailable branches whenever that read model is
replaced, so a superseded payload never leaves a stale map or a stale reason on screen; when a newly
committed payload resolves to the other layout variant, the surface follows the resolved value with no
control of its own. It SHALL open fitted, showing the whole drawing inside its body, and SHALL offer
exactly the view affordances the full-map fit-view requirement of the local-map capability defines —
wheel and `+` / `-` zoom within that requirement's bounds, labelled 放大 and 縮小 buttons, drag-pan, a
labelled 置中 button that recentres the current node, and a `?` disclosure button named 圖例 that opens
the state legend in a popover — and it SHALL name those gestures in words in its guide row. Those
affordances change only the view of the drawing: none of them SHALL change the committed payload, the
resolved layout variant, or any geometry the surface declares, and none SHALL be persisted. It SHALL
render no bearing, compass angle, distance, or coordinate figure, on any layer, and no zoom level,
scale ratio, or other figure describing the view.

The map surface's body SHALL carry the redesign draft's map-canvas framing (the radial-gradient dark
terrain background painted as pure CSS inside a rounded ink border), and SHALL NOT fabricate terrain
geometry the payload does not claim.

The help surface SHALL render the client's own control reference — the keys this client binds, the dock's
navigation model and the close paths — from a single client-owned source, and SHALL
state how the game's own help output is reached. It SHALL name no key binding
or control the client does not implement, SHALL describe `/` and the ⌨ toggle as expanding the command
line and Escape and a successful send as collapsing it, and SHALL NOT render authored game-help content for which
no committed panel exists, and SHALL NOT stand a placeholder in for it.

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

## ADDED Requirements

### Requirement: The command line is a collapsible row docked on the message region's top edge
The client's text control SHALL render as a single bar filling the stage's `command-line` anchor,
containing — in this order — a prompt chevron, the command input field with its send control, a hint
cluster, and the command-history controls. The bar SHALL carry no quick-word chip, no control that only
writes a fixed command word into the field, and no overlay or drawer opener: those openers live in the
top navigation bar's tool group. The `command-line` anchor SHALL be one row 44px tall docked to the top
edge of the bottom band's message region: its lower edge SHALL coincide with the band's upper edge, it
SHALL extend from the left HUD island column's right edge to the message region's right edge, and it
SHALL overlay the lowest strip of the stage box, never the band and never the message text.

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
moved to the action dock before the row is hidden, on exactly two paths: Escape in the input field, and
a send the field accepts (the field clears). Activating the ⌨ toggle while the row is expanded SHALL
collapse it and leave focus on the toggle. A send the field rejects — offline, mutations locked, or a
mutation in flight — SHALL leave the row expanded with the typed text and focus in the field. Losing
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
- **WHEN** the command line is expanded at 1280x720 and at 1920x1080
- **THEN** the row is 44px tall (±1px), its lower edge sits on the bottom band's upper edge, its horizontal extent runs from the left HUD column's right edge to the message region's right edge, its rendered box intersects no HUD island anchor, band region, or other interactive stage anchor, and the input field, its send control, and the history controls are all rendered

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
- **WHEN** the command line is collapsed and the player activates a free-form dialogue entry (the dock's free-form row or the dialogue variant's free-dialogue row)
- **THEN** the row expands, focus moves into the input field, and no action is dispatched until the player sends

#### Scenario: No opener or chip is rendered in the bar
- **WHEN** the bar renders expanded in exploration, combat, or dialogue mode
- **THEN** no quick-word chip, letter badge, chip cluster, or overlay or drawer opener (技能系譜, 圖鑑, 稱號冊, 設定, 說明, 角色肖像圖庫) is present in the bar

#### Scenario: The expanded state is never restored from storage
- **WHEN** the player expands the command line and reloads the page
- **THEN** the reloaded shell renders the command line collapsed

## REMOVED Requirements

### Requirement: The command line is a permanently present bar in the stage's command-line anchor
**Reason**: The AVG stage design (§5.5) makes the command line collapsed by default and moves its overlay utility controls to the top navigation bar. The subject changes from a permanently present bar to a collapsible row, so the requirement is replaced instead of modified.
**Migration**: "The command line is a collapsible row docked on the message region's top edge" states the row, its geometry, and its expand and collapse paths. The utility controls, including the 角色肖像圖庫 control, are stated by the desktop-shell requirement "The top navigation bar carries the tool group". Tests annotated with the old ID re-anchor to the new IDs.
