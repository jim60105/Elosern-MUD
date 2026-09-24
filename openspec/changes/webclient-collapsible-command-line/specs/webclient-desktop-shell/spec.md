## MODIFIED Requirements

### Requirement: Required desktop surfaces remain visible and usable
The narrative SHALL occupy the bottom band's message region as a bounded caption whose complete log is
reachable in one action, with the brand, the top-meta pill, the place card, the action dock and the command-line toggle visible at 1920x1080, 1440x900, and
1280x720, and with each HUD island visible whenever its own contextual-HUD rule renders it (the vitals
island in combat or while a vital or a `warning`, `harmful`, or `critical` condition needs attention, the party island while the party is
non-empty). The action dock and the narrative caption SHALL NOT be permanently closable. The command
line SHALL NOT be permanently closable either: it is collapsed by default, and its input field SHALL be
reachable in exactly one action — `/` outside an editable control, or the ⌨ toggle — in every mode that
renders it; every other surface MAY be opened on demand and closed. The reference
surfaces — the skill book, the bag and equipment, the shop, the quest board, the lore reference, and
the character status — SHALL NOT be permanently visible: each SHALL render in a drawer anchored to the
right edge of the stage, SHALL be absent from the layout and from the tab order while that drawer is
closed, SHALL be reachable in at most two actions from the top navigation bar or from the action dock's
root frame, and SHALL be closable in one action that returns focus to the control that opened it. The shell SHALL render a top navigation bar carrying
a labelled control for each navigation-presented entry of the current mode's home surface - the character
status, quest, and inventory entries - a labelled control for the map and settings surfaces, and the
tool group that the top-navigation tool-group requirement defines, which carries the help control;
activating a bar control SHALL open its surface in one action and SHALL NOT push a keyboard menu frame.
The bar SHALL carry no entry that names the screen the player is already on - no 探索 or 戰鬥 home
entry - because the stage itself is that screen; returning the dock to its root stays on Escape and
the dock's back controls.
The map control on the bar is an additional entry point beside the minimap's own control; the
map, settings and help surfaces SHALL each remain reachable from the running client by a labelled control and SHALL be closable in
one action that returns focus to that control. The foundation
SHALL target desktop only and SHALL NOT claim mobile acceptance. The shell SHALL show the game name as its brand and the connection state in the top bar's top-meta
surface, with the connected state marked by an ok-green dot paired with a label, and SHALL show the
current location and the world date/time only in the stage's place card, resolved as the
contextual-HUD place-card requirement states - never in the top bar, and never a raw mode label in
place of location. The top bar SHALL be 48px tall. The action dock SHALL render as the approved command surface: a
panel filling the bottom band's command region (the band's right third), whose root menu
frame renders as a tab bar of icon-and-label tabs with the open entry marked by a muted-gold fill, and
whose remaining region renders the current frame's rows. The tab bar SHALL carry a guidance hint
naming the shortcuts (direction keys to choose, Enter to confirm, Escape to return, `/` to open the
command input). The focused row SHALL be marked by a muted-gold fill plus a leading glyph, unfocused
rows bordered, and disabled rows dimmed but focusable for their explanation. Below the root frame the
dock SHALL render a breadcrumb naming the parent and current frames with a back control, and SHALL
render each frame's rows in the form that frame calls for — an exit outlet, navigation rows, a
target's affordance rows under its name, suggestion cards, or the combat forms — beside a detail pane
that names the focused item, its availability, and the next key action wherever the frame carries one.
The stage SHALL give the narrative caption and the action dock one fixed-height bottom band - the
message region on the left two thirds and the command region on the right third - whose height comes
from one shared band-height token and never depends on the frame the dock carries, on the mode, or on
the narrative: the interaction workspace, the waiting frame, the combat frames, and an empty pane host
all render inside the same command-region box, so the narrative caption and the action dock never
overlap and neither clips the other at a supported viewport. A frame whose rows exceed the region
SHALL scroll inside the pane host while the tab bar and breadcrumb stay fixed above it. In dialogue
mode the narrative caption SHALL keep the message region's fixed box, and the host, the latest line,
the choice rows, the free-form input and the exit control SHALL all stay reachable at 1280x720 by
scrolling inside the caption, never by growing it.

#### Scenario: Standard desktop viewport contains every required surface
- **WHEN** the shell renders at 1440x900
- **THEN** the narrative caption, the brand, the top-meta surface, the top navigation bar with its tool group, the place card, every HUD island its own rule renders, the action dock, and the command-line toggle are present without overlapping the narrative input path, and one `/` press renders the command line with its input field focused

#### Scenario: Minimum desktop viewport remains usable
- **WHEN** the shell renders at 1280x720
- **THEN** every required surface remains reachable and the player can read narrative, open the complete log, open the character-status drawer to inspect status, and type a command after exactly one opening action (`/` or the ⌨ toggle)

#### Scenario: The reference surfaces are demand-opened, not permanently visible
- **WHEN** the shell renders at 1440x900 or 1280x720 with no drawer open
- **THEN** no skill book, bag, shop, quest board, lore reference, or character-status surface is present in the layout or the tab order, and no permanently visible column of reference panels is rendered

#### Scenario: An open drawer is always one action from closed
- **WHEN** a reference drawer is open at either supported viewport
- **THEN** Escape, its labelled close control, and the scrim each close it in one action and return focus to the control that opened it, and the dock, the narrative caption, and the command-line toggle remain present behind it

#### Scenario: The map, settings and help surfaces are reachable and closable
- **WHEN** the shell renders in exploration mode at either supported viewport with the command line collapsed
- **THEN** a labelled control opens each of the map, settings and help surfaces, and Escape or its close control closes the open one in one action with focus returned to the control that opened it

#### Scenario: The top navigation bar carries the persistent surface entry points
- **WHEN** the shell renders in exploration mode at either supported viewport
- **THEN** the top navigation bar shows one labelled control for each navigation-presented entry of the home surface plus a map control, a settings control, and the tool group, and no 探索 or 戰鬥 entry, each opening its surface in one action without pushing a keyboard menu frame, while the character, quest, and inventory entries are absent from the dock's root tab bar

#### Scenario: The complete narrative stays reachable from the bounded caption
- **WHEN** the narrative holds more lines than the bounded caption can display
- **THEN** the player reaches the complete retained log in one action from the caption card

#### Scenario: Mounting the shell retires the degraded text fallback
- **WHEN** the Vue SPA shell mounts into its container
- **THEN** the degraded stock text fallback (`#messagewindow`) is hidden so it cannot stack with the mounted shell in normal document flow and push required surfaces below the visible viewport

#### Scenario: The shell identifies brand, location, time, and connection without a mode label
- **WHEN** the shell is connected in exploration mode
- **THEN** the brand shows the game name, the top-meta surface shows an ok-green "● 已連線" indicator and no location or time, the place card shows the current location label resolved from the committed panels and the world date/time, and no raw mode label is rendered

#### Scenario: The top-meta location names the region, not the raw room key
- **WHEN** the player stands in a wilderness cell whose status panel location label is the raw room key `Wilderness` while the committed `local_map` panel's current node is labelled 西部丘陵與谷地
- **THEN** the place card's location reads 西部丘陵與谷地, the raw room key is rendered neither in the place card nor anywhere in the top bar, and no composed string pairing the two appears

#### Scenario: The location falls back when the map panel cannot supply a name
- **WHEN** the `local_map` panel is absent, unavailable, or names a current node that its own nodes do not carry or that carries an empty label
- **THEN** the place card's location states the committed status panel's actor location label, and states the card's unavailable placeholder only when neither panel supplies a label

#### Scenario: The action dock renders as a floating panel with a tab bar and a guidance hint
- **WHEN** the action dock is mounted in any mode
- **THEN** it renders as one panel filling the band's command region, its root frame renders as a tab bar carrying the shortcut-key hint with the open tab in a muted-gold fill, its current frame's rows render with a shape-marked focused row and dimmed but focusable disabled rows, and a breadcrumb with a back control appears below the root frame

#### Scenario: A tall frame grows the band without touching the narrative
- **WHEN** the dock carries a taller frame (the interaction workspace or the waiting frame) at 1440x900 or 1280x720
- **THEN** the bottom band keeps its fixed height, the frame's rows scroll inside the command region, the narrative caption's box is unchanged, and neither surface clips the other

#### Scenario: Pane content scrolls inside the band
- **WHEN** the active frame's rows exceed the command region's height
- **THEN** the rows scroll within the pane host, the tab bar and breadcrumb remain visible and fixed above the scrolling region, and the last row becomes reachable by scrolling

#### Scenario: The dialogue caption stays bounded at the minimum viewport
- **WHEN** the committed mode is dialogue at 1280x720
- **THEN** the host identity, the latest line, every choice row, the free-form input and the exit control are all reachable by scrolling inside the caption, without document-level scrolling and without the caption or the band changing size

### Requirement: Keyboard routing is menu-first and submission-safe

After initial synchronization and after every completed or rejected action whose declared
presentation revision has been accepted, the action dock SHALL own focus. Key events SHALL
be dispatched through the public keyboard bridge (the `window.Elosern.KeyboardRouter` handle
contract), claimed exactly when the router consumed them, rather than bound directly to the
document. Arrow keys SHALL move within the active finite menu, Enter SHALL confirm an
enabled focused item, Escape SHALL pop exactly one menu level, Space SHALL be reserved for
multi-select toggles, and `/` SHALL open the command line: when the line is collapsed it SHALL expand
it, and in either state it SHALL move focus into the input field once the field is rendered and SHALL
NOT insert a literal `/` into it. A `/` pressed while an
editable control is focused — the command field included — SHALL be ordinary text input: it SHALL
never be claimed by the router, so commands or text that contain a slash remain
typeable in the command field and in other editable controls (creation forms, rest forms). Escape
pressed while the command field holds focus SHALL send nothing, SHALL return focus to the action
dock, and SHALL collapse the command line.
Pointer activation of a rendered row SHALL be admitted and SHALL traverse the identical
focus, disabled-explanation, and submission-gating path as Enter, as specified by
`webclient-pointer-activation`. Disabled entries SHALL remain focusable for their
explanation but SHALL NOT submit. Held or repeated Enter and all mutation submissions while
one is in flight or awaiting its declared presentation revision SHALL be suppressed, and no
combination of key and pointer input SHALL emit more than one request per deliberate
activation. The exploration keyboard root SHALL be the G2 hierarchical root (Move / Look /
Interact / Character / Quests / Inventory / Wait, plus Suggestions whenever the committed
`suggestions` envelope is not `unavailable`), whose items carry the bare keys
`move`, `look`, `interact`, `character`, `quests`, `inventory`, `wait`, `suggestions`, rendered as a
single-row grid whose column count equals its item count; the root projection presented to both the
tab bar and the keyboard router SHALL omit the `character`, `quests`, and `inventory` entries - the
top navigation bar carries them as the sole keyboard-visible stop - and SHALL NOT reorder the
remaining entries. The combat root SHALL likewise declare a
column count equal to its item count, so both roots' horizontal arrow geometry matches their rendered
tab order. This root replaces the legacy B2 flat `context_actions` affordance list,
whose items were keyed `action-<action_id>` / `action-<surface>` (e.g. `action-guild`). The
B2 key-derivation contract is preserved only as the isolated Node gate
(`web/webclient-app/tests/action/dock_items.test.js`), not as the live exploration focus frame.

#### Scenario: Keyboard navigation and backtracking are deterministic
- **WHEN** the player navigates a test menu with arrows, enters a submenu, and presses Escape
- **THEN** focus follows the menu geometry, exactly one menu level closes, and the prior
  focused item is restored

#### Scenario: Disabled item explains without submitting
- **WHEN** focus moves to a disabled item and the player presses Enter or clicks it
- **THEN** its explanation remains readable and no `ui_action` message is sent

#### Scenario: Repeated Enter submits once
- **WHEN** Enter key repeat fires while a proof action is being submitted
- **THEN** the browser emits one request and keeps mutation controls locked until resolution

#### Scenario: Key dispatch goes through the bridge contract
- **WHEN** the player presses a navigation key over the action dock
- **THEN** the public keyboard bridge claims it (the router consumed the key or the focused
  command field owns it), the bridge reports no unclaimed keydown, and keys the router does not
  consume still reach the text and command-history path

#### Scenario: Slash focuses the command field from the action dock
- **WHEN** the action dock holds focus, the command line is collapsed, and the player presses `/`
- **THEN** the command line expands, focus moves into the command input field, and no literal `/` is inserted
- **WHEN** the field then holds focus and the player presses Escape
- **THEN** nothing is sent, action-dock focus is restored, and the command line collapses

#### Scenario: A slash typed in an editable control is text
- **WHEN** an editable control (the command field, a creation form, or a rest form) is
  focused and the player presses `/`
- **THEN** a literal `/` is typed into that control and the router claims nothing, so text such as
  `whisper /ooc` remains fully typeable

#### Scenario: The suggestions root entry appears only when the envelope carries one
- **WHEN** the committed `suggestions` envelope's status is `unavailable`
- **THEN** the exploration root carries no `suggestions` item at all
- **WHEN** the status is `generating`, `ready`, or `degraded`
- **THEN** the exploration root carries the `suggestions` item and opening it pushes the suggestions frame without dispatching a `ui_action`

#### Scenario: Exploration root exposes the G2 hierarchical keys
- **WHEN** the client is in exploration mode and the player presses ArrowDown on the single-row
  exploration root (the navigation-projected projection of Move / Look / Interact / Wait - plus
  Suggestions when available)
- **THEN** the keyboard router's focus key is the bare G2 key (`move` at the first cell, a no-op
  on the single-row grid), not the legacy B2 `action-guild`-style `action-<id>`/`action-<surface>`
  key, and Enter on the focused root item pushes its client-local submenu (the dock depth becomes
  2) without dispatching a `ui_action`; focus then lands on the pushed submenu's first item (for an
  empty exploration panel, the disabled `move-empty` row), so `store.view.focus.key` is `move-empty`
  and `store.view.focus.enabled` is false

#### Scenario: The dock root omits the navigation-carried entries
- **WHEN** the committed exploration panel makes the character, quest, and inventory surfaces
  available and the dock renders its root
- **THEN** neither the tab bar nor the keyboard root carries a 角色狀態, 任務, or 背包 entry - those
  surfaces are opened from the top navigation bar - and the remaining root entries keep their
  authored order

## ADDED Requirements

### Requirement: The collapsible command line preserves ordinary text control

The command line SHALL be collapsed by default and SHALL always be one entrance action away from use:
its input field SHALL become visible and focused through exactly one entrance action — `/` pressed while no
editable control is focused, activation of the ⌨ toggle, or a dock borrowing the field for its own
free-form dialogue — and no stored layout or presentation state SHALL be able to keep it collapsed or
open it. While collapsed, the field SHALL stay in the DOM, hidden with its row, and SHALL keep the
`#inputfield` identifier inside its `.inputfieldwrapper` wrapper in both states. `/` SHALL move focus
without inserting a literal `/` into the field, and every entrance path SHALL render the row before it
moves focus, so focus never lands on a hidden field. Focusing the input field by any of those entrance
paths SHALL leave it ready to send through its single send implementation. The field SHALL send
ordinary text through Evennia's text message, preserve command history, and SHALL NOT translate text
into `ui_action`. Exactly one send implementation SHALL own the field, so a single key press can never
traverse two send paths. Pressing Enter without Shift while the field is focused SHALL send exactly one
command regardless of how focus arrived; Shift+Enter SHALL insert a newline without sending. After a
send the field accepts (connected, mutations unlocked, and no mutation in flight) the field SHALL clear,
focus SHALL move to the action dock, and the command line SHALL collapse; the next command starts with
one more entrance action. When the field rejects a send (offline, mutations locked, or another mutation
in flight), the typed text SHALL stay in the field, focus SHALL stay in the field, and the command line
SHALL stay expanded, so nothing is silently lost. ArrowUp and ArrowDown SHALL walk the command-history
slice with the unsent draft preserved across the walk and restored when the walk returns past its most
recent entry, and the labelled history controls SHALL drive that same walk without sending; the walk
and Tab completion SHALL behave identically in every entrance path. Escape SHALL send nothing, SHALL
return focus to the action dock, and SHALL collapse the command line while keeping any unsent draft for
the next expansion. When a dock has borrowed the field for one of its own actions — free-form dialogue
— a successful send SHALL clear the field, return focus to the action dock, and collapse the command
line, because that interaction has completed; when the action client is locked (offline, awaiting the
first snapshot, or another mutation in flight) the borrowed send SHALL NOT dispatch, SHALL keep the
typed speech in the field, SHALL keep focus in the field, and SHALL keep the command line expanded. A
borrowed-field reference SHALL be released whenever focus leaves the field for any reason other than
that dock's own successful send, and whenever a send is routed as ordinary text, so a cancelled or
abandoned dock interaction can never capture a later unrelated command. The field SHALL remain usable
when OOB controls are disabled.

#### Scenario: The field is one entrance action away
- **WHEN** the shell mounts the command line in a fresh browser context
- **THEN** the input field is present in the DOM inside its wrapper but hidden and outside the tab order, the ⌨ toggle reports `aria-expanded="false"`, and after one `/` press the field is visible, focused, and can be typed into

#### Scenario: Slash focuses the field without typing a slash
- **WHEN** no editable control is focused and the player presses `/`
- **THEN** the command line expands, focus moves into the input field, and the field's content is unchanged — no literal `/` is inserted

#### Scenario: Keyboard-only command send restores focus
- **WHEN** the player opens the field with `/`, enters a command, and sends it
- **THEN** the command travels through the text input path, the field clears, the command line
  collapses, and focus returns to the action dock

#### Scenario: Consecutive commands need no pointer interaction
- **WHEN** the player opens the field with `/`, sends a command, presses `/` again, types a second command,
  and sends it
- **THEN** both commands travel through the text input path, the field is cleared and the line collapsed
  after each, and focus is in the action dock or the field at every step without any pointer interaction

#### Scenario: Escape cancels without sending and returns to the dock
- **WHEN** the player opens the field, enters unsent text, and presses Escape
- **THEN** no text and no UI action is sent, action-dock focus is restored, the command line collapses, and the next expansion shows the same unsent text

#### Scenario: A pointer-opened field sends on Enter without a prior slash
- **WHEN** the player activates the ⌨ toggle with the pointer, types a command in the now-focused field,
  and presses Enter
- **THEN** exactly one text message is sent through the single send path, the field clears, the command
  line collapses, and focus returns to the action dock; the plugin contract reports no unhandled keydown

#### Scenario: A rejected send keeps the text and the open line
- **WHEN** the player sends an ordinary command while mutations are locked or a mutation is in flight
- **THEN** the typed text remains in the field, focus stays in the field, and the command line stays expanded

#### Scenario: Shift+Enter inserts a newline without sending
- **WHEN** the input field is focused and the player presses Shift+Enter
- **THEN** no command is sent and the text insertion point moves to a new line

#### Scenario: The history walk preserves the unsent draft
- **WHEN** the player types an unsent draft, presses ArrowUp twice to recall two prior commands, and then presses ArrowDown past the most recent entry
- **THEN** the recalled commands appear in order, the unsent draft is restored when the walk returns past its most recent entry, and no command is sent by the walk

#### Scenario: A dock-borrowed send returns focus to the dock
- **WHEN** the exploration dock borrows the field for free-form dialogue while the command line is collapsed,
  and the player sends the speech while the action client is unlocked
- **THEN** the borrow expanded the command line and focused the field, exactly one `explore.talk_freeform`
  action is submitted, the field clears, the command line collapses, and action-dock focus is restored

#### Scenario: A locked borrowed send keeps the speech
- **WHEN** the exploration dock borrows the field for free-form dialogue and the player sends the speech
  while the action client is locked
- **THEN** no action is submitted, no text is lost (the speech remains in the field), focus stays in the
  field, the command line stays expanded, and no input line is echoed

#### Scenario: One key press sends exactly one command
- **WHEN** the player presses Enter in the input field
- **THEN** exactly one text message is sent regardless of how focus arrived

#### Scenario: A cancelled dialogue cannot capture a later command
- **WHEN** the player opens free-form dialogue, leaves the field without sending, and later sends an
  ordinary command through the field
- **THEN** the command travels through the ordinary text path, no `explore.talk_freeform` action is
  submitted, and the typed text is not delivered as speech to the previously selected NPC

### Requirement: The top navigation bar carries the tool group

The top navigation bar SHALL carry, after its 設定 control, one labelled group (`工具`) of icon
controls that open the client's secondary overlays and reference drawers: 技能系譜 (the skill lineage
overlay), 圖鑑 (the world-codex reference drawer), 稱號冊 (the title-codex overlay), 角色肖像圖庫 (the
portrait gallery overlay), and 說明 (the help overlay), in that order. Each control SHALL carry an
accessible name equal to its label and the same label as its tooltip, SHALL be reachable by sequential
keyboard navigation, and SHALL open its surface in one pointer action or one Enter press, through the
same opener-captured path every other overlay or drawer opener uses, so closing the surface returns
focus to that control. The 角色肖像圖庫 control SHALL render only while the committed `gallery` panel is
available. The group SHALL render in every mode that renders the top navigation bar, whether the
command line is expanded or collapsed, and SHALL NOT push a keyboard menu frame. No other surface
SHALL carry a second opener for these five surfaces, and the command line SHALL carry none. The group
SHALL fit the 48px bar: at 1280x720, with every navigation entry, the gallery control, and a
maximum-length character name present, the navigation bar's controls SHALL NOT intersect the top-meta
and character-switcher cluster.

#### Scenario: Each tool opens its surface in one action
- **WHEN** the shell renders in exploration mode with the command line collapsed and the `gallery` panel available, and the player activates 技能系譜, then 稱號冊, then 角色肖像圖庫, then 說明, closing each surface in between
- **THEN** each activation opens its overlay, and each close returns focus to the control that opened it

#### Scenario: The codex tool opens the reference drawer
- **WHEN** the player activates the 圖鑑 control in the tool group
- **THEN** the world-codex reference drawer opens through the single open-drawer entry point, and closing it returns focus to the control

#### Scenario: The gallery tool follows the committed gallery panel
- **WHEN** the committed `gallery` panel is available, and a later revision commits the panel's unavailable form
- **THEN** the 角色肖像圖庫 control is rendered in the tool group while the panel is available, and after the unavailable form commits it is absent from the bar and the tab order

#### Scenario: The tool group is keyboard reachable
- **WHEN** the player moves focus through the top navigation bar with Tab
- **THEN** focus reaches every tool-group control in order, each exposes its label as its accessible name, and Enter on a focused control opens its surface

#### Scenario: The tool group fits the 48px bar at the minimum viewport
- **WHEN** the shell renders in exploration mode at 1280x720 with every navigation entry, the gallery control, and a maximum-length character name present
- **THEN** every tool-group control lies inside the 48px bar, and no navigation control intersects the top-meta or character-switcher cluster

#### Scenario: The command line carries no tool opener
- **WHEN** the command line is expanded
- **THEN** it carries no 技能系譜, 圖鑑, 稱號冊, 設定, 說明, or 角色肖像圖庫 control

## REMOVED Requirements

### Requirement: The command drawer preserves ordinary text control
**Reason**: The AVG stage design (§5.5) makes the command line collapsed by default, and a successful send now collapses it and returns focus to the command panel. The requirement's first scenario ("The field is present and usable with no opening action") and its "never closed" premise cannot be kept, and a MODIFIED block cannot drop a scenario, so the requirement is replaced.
**Migration**: "The collapsible command line preserves ordinary text control" restates the send, history, borrow, and release rules for a collapsible line. Tests annotated with the old ID re-anchor to the new one.
