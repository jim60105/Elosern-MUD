## MODIFIED Requirements

### Requirement: Required desktop surfaces remain visible and usable
The narrative SHALL occupy the bottom band's message region as the bounded message window, whose
complete log is reachable in one action through its `日誌` control, with the brand, the top-meta pill, the
place card, the action dock (in every playing mode except dialogue, where the command region collapses)
and the command-line toggle visible at 1920x1080, 1440x900, and
1280x720, and with each HUD island visible whenever its own contextual-HUD rule renders it (the vitals
island in combat or while a vital or a `warning`, `harmful`, or `critical` condition needs attention, the party island while the party is
non-empty). The action dock and the message window SHALL NOT be permanently closable; the dock's collapse in
dialogue mode lasts exactly as long as the committed mode is `dialogue`. The command
line SHALL NOT be permanently closable either: it is collapsed by default, and its input field SHALL be
reachable in exactly one action — `/` outside an editable control, or the ⌨ toggle — in every mode that
renders it; every other surface MAY be opened on demand and closed. The reference
surfaces — the skill book, the bag and equipment, the shop, the quest board, the lore reference, and
the character status — SHALL NOT be permanently visible: each SHALL render in a drawer anchored to the
right edge of the stage, SHALL be absent from the layout and from the tab order while that drawer is
closed, SHALL be reachable in at most two actions from the top navigation bar or from the action dock's
scene overview, and SHALL be closable in one action that returns focus to the control that opened it. The shell SHALL render a top navigation bar carrying
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
panel filling the bottom band's command region (the band's right third), whose exploration root
renders as the scene overview (chip rows for exits, people, and objects, and a footer) and whose
combat root renders as a tab bar of icon-and-label tabs with the open entry marked by a muted-gold
fill, and whose remaining region renders the current frame's rows or chips. The dock SHALL carry the
shortcut legend the contextual-HUD legend requirement defines. The focused row or chip SHALL be marked
by a muted-gold fill plus a leading glyph, unfocused rows bordered, and disabled rows dimmed
but focusable for their explanation. Below the root frame the
dock SHALL render a breadcrumb naming the parent and current frames with a back control, and SHALL
render each frame's rows in the form that frame calls for — a target's verb popover over the inert
overview, navigation rows, the waiting cards, suggestion cards, or the combat forms — beside a detail
pane that names the focused item, its availability, and the next key action wherever the frame
carries one.
The stage SHALL give the message window and the action dock one fixed-height bottom band - the
message region on the left two thirds and the command region on the right third, or the message region
across the whole band in dialogue mode - whose height comes
from one shared band-height token and never depends on the frame the dock carries, on the mode, or on
the narrative: the scene overview, a target's verb popover, the waiting frame, the combat frames, and an empty
pane host all render inside the same command-region box, so the message window and the action dock never
overlap and neither clips the other at a supported viewport. A frame whose rows exceed the region
SHALL scroll inside the pane host while the dock's chrome (the combat tab bar, the breadcrumb, and
the legend strip) stays fixed around it. In dialogue
mode the message window SHALL span the whole band at the band's fixed height and carry the host's name
plate and the paged line, reachable at 1280x720 by paging inside the window, never by growing it; the
choice rows, the free-dialogue row, the move row and the exit row SHALL render in the dialogue choice
list centred over the stage (the contextual-HUD dialogue-choices requirement), never inside the message
window, and SHALL fit the stage above the band at 1280x720 without document-level scrolling.

#### Scenario: Standard desktop viewport contains every required surface
- **WHEN** the shell renders at 1440x900
- **THEN** the message window, the brand, the top-meta surface, the top navigation bar with its tool group, the place card, every HUD island its own rule renders, the action dock, and the command-line toggle are present without overlapping the narrative input path, and one `/` press renders the command line with its input field focused

#### Scenario: Minimum desktop viewport remains usable
- **WHEN** the shell renders at 1280x720
- **THEN** every required surface remains reachable and the player can read narrative, open the complete log, open the character-status drawer to inspect status, and type a command after exactly one opening action (`/` or the ⌨ toggle)

#### Scenario: The reference surfaces are demand-opened, not permanently visible
- **WHEN** the shell renders at 1440x900 or 1280x720 with no drawer open
- **THEN** no skill book, bag, shop, quest board, lore reference, or character-status surface is present in the layout or the tab order, and no permanently visible column of reference panels is rendered

#### Scenario: An open drawer is always one action from closed
- **WHEN** a reference drawer is open at either supported viewport
- **THEN** Escape, its labelled close control, and the scrim each close it in one action and return focus to the control that opened it, and the dock, the message window, and the command-line toggle remain present behind it

#### Scenario: The map, settings and help surfaces are reachable and closable
- **WHEN** the shell renders in exploration mode at either supported viewport with the command line collapsed
- **THEN** a labelled control opens each of the map, settings and help surfaces, and Escape or its close control closes the open one in one action with focus returned to the control that opened it

#### Scenario: The top navigation bar carries the persistent surface entry points
- **WHEN** the shell renders in exploration mode at either supported viewport
- **THEN** the top navigation bar shows one labelled control for each navigation-presented entry of the home surface plus a map control, a settings control, and the tool group, and no 探索 or 戰鬥 entry, each opening its surface in one action without pushing a keyboard menu frame, while the character, quest, and inventory entries are absent from the dock's scene overview

#### Scenario: The complete narrative stays reachable from the bounded caption
- **WHEN** the narrative holds more lines than the message window's page can display
- **THEN** the player reaches the complete retained log in one action through the window's `日誌` control

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
- **THEN** it renders as one panel filling the band's command region with one shortcut-legend strip, its exploration root renders as the scene overview and its combat root as a tab bar with the open tab in a muted-gold fill, its current frame's rows or chips render with a shape-marked focused entry and dimmed but focusable disabled entries, and a breadcrumb with a back control appears below the root frame

#### Scenario: A tall frame grows the band without touching the narrative
- **WHEN** the dock carries a taller frame (a crowded scene overview, a target's verb popover, or the waiting frame) at 1440x900 or 1280x720
- **THEN** the bottom band keeps its fixed height, the frame's rows scroll inside the command region, the message window's box is unchanged, and neither surface clips the other

#### Scenario: Pane content scrolls inside the band
- **WHEN** the active frame's rows exceed the command region's height
- **THEN** the rows scroll within the pane host, the dock's chrome (the combat tab bar, the breadcrumb, and the legend strip) remains visible and fixed around the scrolling region, and the last row becomes reachable by scrolling

#### Scenario: The dialogue caption stays bounded at the minimum viewport
- **WHEN** the committed mode is dialogue at 1280x720
- **THEN** the message window spans the whole band and carries the host's name plate and the paged line, the command region is not rendered, and once the line is fully shown every choice row, the free-dialogue row, the move row and the exit row are reachable in the choice list centred over the stage, never inside the message window, without document-level scrolling and without the window or the band changing size

### Requirement: Keyboard routing is menu-first and submission-safe

After initial synchronization and after every completed or rejected action whose declared
presentation revision has been accepted, the current mode's focus home SHALL own focus: the action
dock, or in dialogue mode the message window's focus target, as `webclient-contextual-hud` "The command
region collapses in dialogue mode and the message window spans the band" defines. Key events SHALL
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
pressed while the command field holds focus SHALL send nothing, SHALL return focus to the current
mode's focus home, and SHALL collapse the command line. While the committed mode is `dialogue` the
router SHALL claim only `/`; arrows, Enter, Space, Escape, and digits SHALL be unclaimed by it, so the
hidden dock is never navigated or activated, and the dialogue choice list handles its own keys before
they reach the bridge.
Pointer activation of a rendered row SHALL be admitted and SHALL traverse the identical
focus, disabled-explanation, and submission-gating path as Enter, as specified by
`webclient-pointer-activation`. Disabled entries SHALL remain focusable for their
explanation but SHALL NOT submit. Held or repeated Enter and all mutation submissions while
one is in flight or awaiting its declared presentation revision SHALL be suppressed, and no
combination of key and pointer input SHALL emit more than one request per deliberate
activation. The exploration keyboard root SHALL be the scene overview frame, whose items carry
the bare keys `exit-<exit_ref>` for exits, `target-<identity>` for interact targets,
`entity-<identity>` and `object-<identity>` for look-only people and objects, and `look-room`,
`wait`, and — whenever the committed `suggestions` envelope is not `unavailable` — `suggestions` for
the footer, in the overview's reading order and navigated by its row-of-chips geometry; it SHALL
carry no `character`, `quests`, or `inventory` entry - the top navigation bar carries them as the sole
keyboard-visible stop. The combat root SHALL declare a column count equal to its item count, so its
horizontal arrow geometry matches its rendered tab order. This root replaces the legacy B2 flat `context_actions` affordance list,
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
- **THEN** the scene overview carries no `suggestions` chip at all
- **WHEN** the status is `generating`, `ready`, or `degraded`
- **THEN** the overview's footer carries the `suggestions` chip and activating it pushes the suggestions frame without dispatching a `ui_action`

#### Scenario: Exploration root exposes the G2 hierarchical keys
- **WHEN** the client is in exploration mode on a scene overview whose first two chips are an exit
  and an interact target, and the player presses ArrowRight
- **THEN** the keyboard router's focus key is the bare overview key `target-<identity>`, not the
  legacy B2 `action-guild`-style `action-<id>`/`action-<surface>` key, and Enter on it pushes the
  target's verb popover (the dock depth becomes 2) without dispatching a `ui_action`; focus then
  lands on the popover's first row; for an exploration panel with no exits, people, or objects the
  overview's first chip is `look-room`

#### Scenario: The dock root omits the navigation-carried entries
- **WHEN** the committed exploration panel makes the character, quest, and inventory surfaces
  available and the dock renders its root
- **THEN** the scene overview carries no 角色狀態, 任務, or 背包 entry - those surfaces are opened
  from the top navigation bar - and the overview's chips keep the panel's order

#### Scenario: The router is inert while the dock is collapsed
- **WHEN** the committed mode is dialogue, focus is on the document body, and the player presses ArrowDown, Enter, Space, and Escape
- **THEN** the bridge reports each key unclaimed by the router, the router's focused key and depth are unchanged, and no request is emitted

## ADDED Requirements

### Requirement: The collapsible command line preserves ordinary text control and the dialogue's free-form borrow

The command line SHALL be collapsed by default and SHALL always be one entrance action away from use:
its input field SHALL become visible and focused through exactly one entrance action — `/` pressed while no
editable control is focused, activation of the ⌨ toggle, or the dialogue choice list's `⌨ 自由對話` row
borrowing the field for free-form speech to the conversation's host — and no stored layout or presentation state SHALL be able to keep it collapsed or
open it. While collapsed, the field SHALL stay in the DOM, hidden with its row, and SHALL keep the
`#inputfield` identifier inside its `.inputfieldwrapper` wrapper in both states. `/` SHALL move focus
without inserting a literal `/` into the field, and every entrance path SHALL render the row before it
moves focus, so focus never lands on a hidden field. Focusing the input field by any of those entrance
paths SHALL leave it ready to send through its single send implementation. The field SHALL send
ordinary text through Evennia's text message, preserve command history, and SHALL NOT translate text
into `ui_action`. Exactly one send implementation SHALL own the field, so a single key press can never
traverse two send paths. Pressing Enter without Shift while the field is focused SHALL send exactly one
command regardless of how focus arrived; Shift+Enter SHALL insert a newline without sending. The field SHALL accept a send by exactly the predicate that decides whether the send is delivered: an
ordinary text send while connected, mutations unlocked, and no mutation in flight; a borrowed free-form
send while connected, mutations unlocked, the presentation phase active, and no mutation in flight —
the same predicate the action dispatch path applies, so the field never accepts a borrowed send the
dispatch path then refuses. After a send the field accepts the field SHALL clear, focus SHALL move to
the current mode's focus home (the action dock; in dialogue mode the dialogue choice list while it is
rendered and otherwise the message window's page surface), and the command line SHALL collapse; the
next command starts with one more entrance action. When the field rejects a send, the typed text SHALL
stay in the field, focus SHALL stay in the field, and the command line SHALL stay expanded, so nothing
is silently lost. ArrowUp and ArrowDown SHALL walk the command-history
slice with the unsent draft preserved across the walk and restored when the walk returns past its most
recent entry, and the labelled history controls SHALL drive that same walk without sending; the walk
and Tab completion SHALL behave identically in every entrance path. Escape SHALL send nothing, SHALL
return focus to the current mode's focus home, and SHALL collapse the command line while keeping any unsent draft for
the next expansion. The only borrower is the dialogue choice list's `⌨ 自由對話` row. While it has borrowed the field, a
successful send SHALL dispatch exactly one `explore.talk_freeform` with the host's identity and the
speech, clear the field, return focus to the dialogue's focus home, and collapse the command line,
because that interaction has completed; when the action client is locked (offline, awaiting the first
snapshot, a presentation phase other than active, or another mutation in flight) the borrowed send
SHALL NOT dispatch, SHALL keep the typed speech in the field, SHALL keep focus in the field, SHALL keep
the command line expanded, and SHALL keep the borrow bound to the same host, so the next send once the
lock lifts is still delivered as that speech. A
borrowed-field reference SHALL be released whenever focus leaves the field for any reason other than
a send the field accepted or rejected, and whenever a send is routed as ordinary text, so a cancelled or
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

#### Scenario: A borrowed dialogue send returns focus to the dialogue
- **WHEN** the dialogue choice list's `⌨ 自由對話` row borrows the field while the command line is collapsed,
  and the player sends the speech while the action client is unlocked and the presentation phase is active
- **THEN** the borrow expanded the command line and focused the field, exactly one `explore.talk_freeform`
  action is submitted for the host, the field clears, the command line collapses, focus is on the message
  window's page surface while the reply is awaited, and focus moves to the choice list once the reply's
  last page is fully shown

#### Scenario: A locked borrowed send keeps the speech
- **WHEN** the dialogue free row borrows the field and the player sends the speech while the action client
  is locked, and then sends again after the lock lifts
- **THEN** the first send submits no action, keeps the speech in the field with focus and the expanded
  line, and echoes no input line; the second send submits exactly one `explore.talk_freeform` for the same
  host and no ordinary text command

#### Scenario: A borrowed send outside the active phase is rejected by the field
- **WHEN** the dialogue free row borrows the field and the player sends the speech while the transport is
  connected and unlocked with no mutation in flight but the presentation phase is not active
- **THEN** the field does not clear, the command line stays expanded with focus in the field, no action is
  submitted, and the speech is not lost

#### Scenario: One key press sends exactly one command
- **WHEN** the player presses Enter in the input field
- **THEN** exactly one text message is sent regardless of how focus arrived

#### Scenario: A cancelled dialogue cannot capture a later command
- **WHEN** the player activates the dialogue free row, leaves the field without sending, and later sends an
  ordinary command through the field
- **THEN** the command travels through the ordinary text path, no `explore.talk_freeform` action is
  submitted, and the typed text is not delivered as speech to the previously selected NPC

## REMOVED Requirements

### Requirement: The collapsible command line preserves ordinary text control
**Reason**: After `explore-talk-open-action` and `webclient-talk-open-dock` the only borrower of the command line is the dialogue's free row, and the AVG stage design (§8.2) moves that row into the choice list over the stage. The requirement's borrowed-send scenario "A dock-borrowed send returns focus to the dock" names a borrower and a focus target that no longer exist in dialogue mode (the dock is collapsed), and a MODIFIED block cannot rename it. The field's accept rule also gains the presentation-phase condition the dispatch path already applies.
**Migration**: "The collapsible command line preserves ordinary text control and the dialogue's free-form borrow" restates every send, history, Escape, and release rule, names the dialogue free row as the borrower, returns focus to the mode's focus home, aligns the borrowed accept predicate with the dispatch path, and keeps the borrow bound across a rejected send. Tests annotated with the old ID re-anchor to the new one.
