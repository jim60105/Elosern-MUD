## MODIFIED Requirements

### Requirement: Required desktop surfaces remain visible and usable
The narrative SHALL occupy the visual centre of the stage as a bounded caption whose complete log is
reachable in one action, with the brand, the top-meta pill, the action dock and the command line visible at 1440x900 and
1280x720, and with each HUD island visible whenever its own contextual-HUD rule renders it (the vitals
island in combat or while a vital or a `warning`, `harmful`, or `critical` condition needs attention, the party island while the party is
non-empty). The action dock, the narrative caption, and the
command line SHALL NOT be permanently closable, and the command line's input field SHALL be present and
usable without an opening action; every other surface MAY be opened on demand and closed. The reference
surfaces — the skill book, the bag and equipment, the shop, the quest board, the lore reference, and
the character status — SHALL NOT be permanently visible: each SHALL render in a drawer anchored to the
right edge of the stage, SHALL be absent from the layout and from the tab order while that drawer is
closed, SHALL be reachable in at most two actions from the top navigation bar or from the action dock's
root frame, and SHALL be closable in one action that returns focus to the control that opened it. The shell SHALL render a top navigation bar carrying
a labelled control for each navigation-presented entry of the current mode's home surface - the character
status, quest, and inventory entries - and a labelled control for the map, settings, and help surfaces;
activating a bar control SHALL open its surface in one action and SHALL NOT push a keyboard menu frame.
The map and settings controls on the bar are additional entry points; the
map, settings and help surfaces SHALL each remain reachable from the running client by a labelled control and SHALL be closable in
one action that returns focus to that control. The foundation
SHALL target desktop only and SHALL NOT claim mobile acceptance. The shell SHALL show the game name as
its brand and SHALL show the current location, the world date/time, and the connection state in a
top-meta surface, with the connected state marked by an ok-green dot paired with a label — never a raw
mode label in place of location. The top-meta location SHALL state the best server-authored place name
the client already holds, resolved in a fixed order: the committed `local_map` panel's `current_node`
label when that panel is available, names a current node, that node is present in the panel's nodes,
and its label is a non-empty string; otherwise the committed status panel's actor location label;
otherwise the surface's own unavailable placeholder. The shell SHALL NOT compose a third string from
the two candidates, SHALL NOT derive a name from any node or room identifier, and SHALL NOT render a
raw room key while a committed panel carries the authored place name for the same room — the raw
wilderness room key is one string for the whole continent, while the map panel names the region the
player is standing in. Neither payload contract changes: the shell chooses between two labels the
server already committed at the same revision. The action dock SHALL render as the approved command surface: a
floating panel bounded to a maximum width and centred in the stage's dock anchor, whose root menu
frame renders as a tab bar of icon-and-label tabs with the open entry marked by a muted-gold fill, and
whose remaining region renders the current frame's rows. The tab bar SHALL carry a guidance hint
naming the shortcuts (direction keys to choose, Enter to confirm, Escape to return, `/` to focus the
command input). The focused row SHALL be marked by a muted-gold fill plus a leading glyph, unfocused
rows bordered, and disabled rows dimmed but focusable for their explanation. Below the root frame the
dock SHALL render a breadcrumb naming the parent and current frames with a back control, and SHALL
render each frame's rows in the form that frame calls for — an exit outlet, navigation rows, a
target's affordance rows under its name, suggestion cards, or the combat forms — beside a detail pane
that names the focused item, its availability, and the next key action wherever the frame carries one.
The stage SHALL size the action dock's band and the narrative caption's lower edge from one shared
dock-band measure that adapts to the frame the dock currently carries - the interaction workspace and
the three-card waiting frame grow it, the combat band stays shorter, and an empty pane host collapses
it in two tiers (any mode's empty host - including the ordinary non-degraded exploration root, whose
row region the tab bar alone fills - collapses to 144px, and an empty combat host overrides that to
100px) - outside combat both surfaces position from that one measure with their own fixed/viewport
offsets, while combat coordinates its feed and dock through its own shorter band plus explicit
offsets, so the narrative caption and the action dock never overlap and neither clips the
other at a supported viewport. A frame whose rows exceed the band SHALL scroll inside the pane host
while the tab bar and breadcrumb stay fixed above it. In dialogue mode the narrative caption SHALL
likewise bound its own growth so the host, the latest line, the choice rows, the free-form input and
the exit control all stay reachable at 1280x720.

#### Scenario: Standard desktop viewport contains every required surface
- **WHEN** the shell renders at 1440x900
- **THEN** the narrative caption, the brand, the top-meta surface, the top navigation bar, every HUD island its own rule renders, the action dock, and the command line with its visible input field are present without overlapping the narrative input path

#### Scenario: Minimum desktop viewport remains usable
- **WHEN** the shell renders at 1280x720
- **THEN** every required surface remains reachable and the player can read narrative, open the complete log, open the character-status drawer to inspect status, and type a command without any opening action

#### Scenario: The reference surfaces are demand-opened, not permanently visible
- **WHEN** the shell renders at 1440x900 or 1280x720 with no drawer open
- **THEN** no skill book, bag, shop, quest board, lore reference, or character-status surface is present in the layout or the tab order, and no permanently visible column of reference panels is rendered

#### Scenario: An open drawer is always one action from closed
- **WHEN** a reference drawer is open at either supported viewport
- **THEN** Escape, its labelled close control, and the scrim each close it in one action and return focus to the control that opened it, and the dock, the narrative caption, and the command line remain present behind it

#### Scenario: The map, settings and help surfaces are reachable and closable
- **WHEN** the shell renders in exploration mode at either supported viewport
- **THEN** a labelled control opens each of the map, settings and help surfaces, and Escape or its close control closes the open one in one action with focus returned to the control that opened it

#### Scenario: The top navigation bar carries the persistent surface entry points
- **WHEN** the shell renders in exploration mode at either supported viewport
- **THEN** the top navigation bar shows one labelled control for each navigation-presented entry of the home surface plus a map control, each opening its surface in one action without pushing a keyboard menu frame, while the character, quest, and inventory entries are absent from the dock's root tab bar

#### Scenario: The complete narrative stays reachable from the bounded caption
- **WHEN** the narrative holds more lines than the bounded caption can display
- **THEN** the player reaches the complete retained log in one action from the caption card

#### Scenario: Mounting the shell retires the degraded text fallback
- **WHEN** the Vue SPA shell mounts into its container
- **THEN** the degraded stock text fallback (`#messagewindow`) is hidden so it cannot stack with the mounted shell in normal document flow and push required surfaces below the visible viewport

#### Scenario: The shell identifies brand, location, time, and connection without a mode label
- **WHEN** the shell is connected in exploration mode
- **THEN** the brand shows the game name, the top-meta surface shows the current location label resolved from the committed panels, the world date/time, and an ok-green "● 已連線" indicator, and no raw mode label is rendered

#### Scenario: The top-meta location names the region, not the raw room key
- **WHEN** the player stands in a wilderness cell whose status panel location label is the raw room key `Wilderness` while the committed `local_map` panel's current node is labelled 西部丘陵與谷地
- **THEN** the top-meta location reads 西部丘陵與谷地, the raw room key is not rendered anywhere in the top-meta surface, and no composed string pairing the two appears

#### Scenario: The location falls back when the map panel cannot supply a name
- **WHEN** the `local_map` panel is absent, unavailable, or names a current node that its own nodes do not carry or that carries an empty label
- **THEN** the top-meta location states the committed status panel's actor location label, and states the surface's unavailable placeholder only when neither panel supplies a label

#### Scenario: The action dock renders as a floating panel with a tab bar and a guidance hint
- **WHEN** the action dock is mounted in any mode
- **THEN** it renders as one centred floating panel in the dock anchor, its root frame renders as a tab bar carrying the shortcut-key hint with the open tab in a muted-gold fill, its current frame's rows render with a shape-marked focused row and dimmed but focusable disabled rows, and a breadcrumb with a back control appears below the root frame

#### Scenario: A tall frame grows the band without touching the narrative
- **WHEN** the dock carries a taller frame (the interaction workspace or the three-card waiting frame) at 1440x900 or 1280x720
- **THEN** the shared dock band grows for that frame, the narrative caption's lower edge stays above the dock's upper edge, and neither surface clips the other

#### Scenario: Pane content scrolls inside the band
- **WHEN** the active frame's rows exceed the dock band's height
- **THEN** the rows scroll within the pane host, the tab bar and breadcrumb remain visible and fixed above the scrolling region, and the last row becomes reachable by scrolling

#### Scenario: The dialogue caption stays bounded at the minimum viewport
- **WHEN** the committed mode is dialogue at 1280x720
- **THEN** the host identity, the latest line, every choice row, the free-form input and the exit control are all reachable without document-level scrolling

### Requirement: The command drawer preserves ordinary text control

The command line SHALL be permanently present and its input field SHALL be visible and usable without
any opening action: there SHALL be no entry control, no `aria-expanded` state and no closed state, so
the client's text control cannot be hidden by a stale stored layout and cannot be reached only through
a second control. The field SHALL keep the `#inputfield` identifier inside its `.inputfieldwrapper`
wrapper. Focus SHALL move into the field when the player presses `/` while no editable control is
focused, when the player activates the field with a pointer or keyboard, or when a
dock borrows the field for its own free-form dialogue; `/` SHALL move focus without inserting a literal
`/` into the field. Focusing the input field by any of those entrance paths SHALL leave it ready to send
through its single send implementation. The field SHALL send ordinary text through Evennia's text
message, preserve command history, and SHALL NOT translate text into `ui_action`. Exactly one send
implementation SHALL own the field, so a single key press can never traverse two send paths. Pressing
Enter without Shift while the field is focused SHALL send exactly one command regardless of how focus
arrived; Shift+Enter SHALL insert a newline without sending. After a successful ordinary text send the
field SHALL clear and SHALL retain focus, so consecutive commands are typeable without any pointer
interaction. ArrowUp and ArrowDown SHALL walk the command-history slice with the unsent draft preserved
across the walk and restored when the walk returns past its most recent entry, and the labelled
history controls SHALL drive that same walk without sending. Escape SHALL send nothing and SHALL return
focus to the action dock; because the field is never closed, Escape is the only key that leaves it.
When a dock has borrowed the field for one of its own actions — free-form dialogue — a successful send
SHALL clear the field and return focus to the action dock, because that interaction has completed; when
the action client is locked (offline, awaiting the first snapshot, or another mutation in flight) the
borrowed send SHALL NOT dispatch, SHALL keep the typed speech in the field, and SHALL keep focus in the
field so nothing is silently lost. A borrowed-field reference SHALL be released whenever focus leaves
the field for any reason other than that dock's own successful send, and whenever a send is routed as
ordinary text, so a cancelled or abandoned dock interaction can never capture a later unrelated command.
The field SHALL remain usable when OOB controls are disabled.

#### Scenario: The field is present and usable with no opening action
- **WHEN** the shell mounts the command line in a fresh browser context
- **THEN** the input field is present, visible and focusable, no entry control is rendered, no element reports an `aria-expanded` state, and the field can be typed into as soon as it is focused

#### Scenario: Slash focuses the field without typing a slash
- **WHEN** no editable control is focused and the player presses `/`
- **THEN** focus moves into the input field and the field's content is unchanged — no literal `/` is inserted

#### Scenario: Keyboard-only command send restores focus
- **WHEN** the player focuses the field with `/`, enters a command, and sends it
- **THEN** the command travels through the text input path, the field clears, and focus stays in the
  field for the next command, so consecutive commands need no pointer interaction

#### Scenario: Consecutive commands need no pointer interaction
- **WHEN** the player focuses the field with `/`, sends a command, and immediately types a second command
  and sends it
- **THEN** both commands travel through the text input path, the field is cleared between them, and
  focus never leaves the field

#### Scenario: Escape cancels without sending and returns to the dock
- **WHEN** the player focuses the field, enters unsent text, and presses Escape
- **THEN** no text and no UI action is sent, the field remains present with its text, and action-dock focus is restored

#### Scenario: A pointer-focused field sends on Enter without a prior slash
- **WHEN** the player clicks the input field, types a command in the now-focused field, and
  presses Enter
- **THEN** exactly one text message is sent through the single send path, the field clears, and
  focus stays in the field; the plugin contract reports no unhandled keydown

#### Scenario: Shift+Enter inserts a newline without sending
- **WHEN** the input field is focused and the player presses Shift+Enter
- **THEN** no command is sent and the text insertion point moves to a new line

#### Scenario: The history walk preserves the unsent draft
- **WHEN** the player types an unsent draft, presses ArrowUp twice to recall two prior commands, and then presses ArrowDown past the most recent entry
- **THEN** the recalled commands appear in order, the unsent draft is restored when the walk returns past its most recent entry, and no command is sent by the walk

#### Scenario: A dock-borrowed send returns focus to the dock
- **WHEN** the exploration dock borrows the field for free-form dialogue and the player sends the speech
  while the action client is unlocked
- **THEN** exactly one `explore.talk_freeform` action is submitted, the field clears, and action-dock
  focus is restored

#### Scenario: A locked borrowed send keeps the speech
- **WHEN** the exploration dock borrows the field for free-form dialogue and the player sends the speech
  while the action client is locked
- **THEN** no action is submitted, no text is lost (the speech remains in the field), focus stays in the
  field, and no input line is echoed

#### Scenario: One key press sends exactly one command
- **WHEN** the player presses Enter in the input field
- **THEN** exactly one text message is sent regardless of how focus arrived

#### Scenario: A cancelled dialogue cannot capture a later command
- **WHEN** the player opens free-form dialogue, leaves the field without sending, and later sends an
  ordinary command through the field
- **THEN** the command travels through the ordinary text path, no `explore.talk_freeform` action is
  submitted, and the typed text is not delivered as speech to the previously selected NPC
