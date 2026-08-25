## MODIFIED Requirements

### Requirement: The command drawer preserves ordinary text control

The command line SHALL be permanently present and its input field SHALL be visible and usable without
any opening action: there SHALL be no entry control, no `aria-expanded` state and no closed state, so
the client's text control cannot be hidden by a stale stored layout and cannot be reached only through
a second control. The field SHALL keep the `#inputfield` identifier inside its `.inputfieldwrapper`
wrapper. Focus SHALL move into the field when the player presses `/` while no editable control is
focused, when the player activates the field or a quick-word chip with a pointer or keyboard, or when a
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


### Requirement: Keyboard routing is menu-first and submission-safe

After initial synchronization and after every completed or rejected action whose declared
presentation revision has been accepted, the action dock SHALL own focus. Key events SHALL
be dispatched through the public keyboard bridge (the `window.Elosern.KeyboardRouter` handle
contract), claimed exactly when the router consumed them, rather than bound directly to the
document. Arrow keys SHALL move within the active finite menu, Enter SHALL confirm an
enabled focused item, Escape SHALL pop exactly one menu level, Space SHALL be reserved for
multi-select toggles, and `/` SHALL focus the command line's input field: the field is permanently
present, so `/` has no closed state to open and no open state to close — it SHALL move focus into the
field and SHALL NOT insert a literal `/` into it. A `/` pressed while an
editable control is focused — the command field included — SHALL be ordinary text input: it SHALL
never be claimed by the router, so commands or text that contain a slash remain
typeable in the command field and in other editable controls (creation forms, rest forms). Escape
pressed while the command field holds focus SHALL send nothing and SHALL return focus to the action
dock, and SHALL be the only key that leaves the field.
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
single-row grid whose column count equals its item count. The combat root SHALL likewise declare a
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
- **WHEN** the action dock holds focus and the player presses `/`
- **THEN** focus moves into the command input field and no literal `/` is inserted
- **WHEN** the field then holds focus and the player presses Escape
- **THEN** nothing is sent and action-dock focus is restored

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
  exploration root (Move / Look / Interact / Character / Quests / Inventory / Wait)
- **THEN** the keyboard router's focus key is the bare G2 key (`move` at the first cell, a no-op
  on the single-row grid), not the legacy B2 `action-guild`-style `action-<id>`/`action-<surface>`
  key, and Enter on the focused root item pushes its client-local submenu (the dock depth becomes
  2) without dispatching a `ui_action`; focus then lands on the pushed submenu's first item (for an
  empty exploration panel, the disabled `move-empty` row), so `store.view.focus.key` is `move-empty`
  and `store.view.focus.enabled` is false


### Requirement: Required desktop surfaces remain visible and usable
The narrative SHALL occupy the visual centre of the stage as a bounded caption whose complete log is
reachable in one action, with the brand, the top-meta pill, the HUD island stack, the action dock and
the command line visible at 1440x900 and 1280x720. The action dock, the narrative caption, and the
command line SHALL NOT be permanently closable, and the command line's input field SHALL be present and
usable without an opening action; every other surface MAY be opened on demand and closed. The reference
surfaces — the skill book, the bag and equipment, the shop, the quest board, the lore reference, and
the character status — SHALL NOT be permanently visible: each SHALL render in a drawer anchored to the
right edge of the stage, SHALL be absent from the layout and from the tab order while that drawer is
closed, SHALL be reachable in at most two actions from the action dock's root frame, and SHALL be
closable in one action that returns focus to the control that opened it. The map, settings and help
surfaces SHALL each be reachable from the running client by a labelled control and SHALL be closable in
one action that returns focus to that control. The foundation
SHALL target desktop only and SHALL NOT claim mobile acceptance. The shell SHALL show the game name as
its brand and SHALL show the current location, the world date/time, and the connection state in a
top-meta surface, with the connected state marked by an ok-green dot paired with a label — never a raw
mode label in place of location. The action dock SHALL render as the approved command surface: a
floating panel bounded to a maximum width and centred in the stage's dock anchor, whose root menu
frame renders as a tab bar of icon-and-label tabs with the open entry marked by a seal-red fill, and
whose remaining region renders the current frame's rows. The tab bar SHALL carry a guidance hint
naming the shortcuts (direction keys to choose, Enter to confirm, Escape to return, `/` to focus the
command input). The focused row SHALL be marked by a seal-red fill plus a leading glyph, unfocused
rows bordered, and disabled rows dimmed but focusable for their explanation. Below the root frame the
dock SHALL render a breadcrumb naming the parent and current frames with a back control, and SHALL
render each frame's rows in the form that frame calls for — an exit outlet, navigation rows, a
target's affordance rows under its name, suggestion cards, or the combat forms — beside a detail pane
that names the focused item, its availability, and the next key action wherever the frame carries one.

#### Scenario: Standard desktop viewport contains every required surface
- **WHEN** the shell renders at 1440x900
- **THEN** the narrative caption, the brand, the top-meta surface, the HUD island stack, the action dock, and the command line with its visible input field are present without overlapping the narrative input path

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

#### Scenario: The complete narrative stays reachable from the bounded caption
- **WHEN** the narrative holds more lines than the bounded caption can display
- **THEN** the player reaches the complete retained log in one action from the caption card

#### Scenario: Mounting the shell retires the degraded text fallback
- **WHEN** the Vue SPA shell mounts into its container
- **THEN** the degraded stock text fallback (`#messagewindow`) is hidden so it cannot stack with the mounted shell in normal document flow and push required surfaces below the visible viewport

#### Scenario: The shell identifies brand, location, time, and connection without a mode label
- **WHEN** the shell is connected in exploration mode
- **THEN** the brand shows the game name, the top-meta surface shows the current location label from the synced status panel, the world date/time, and an ok-green "● 已連線" indicator, and no raw mode label is rendered

#### Scenario: The action dock renders as a floating panel with a tab bar and a guidance hint
- **WHEN** the action dock is mounted in any mode
- **THEN** it renders as one centred floating panel in the dock anchor, its root frame renders as a tab bar carrying the shortcut-key hint with the open tab in a seal-red fill, its current frame's rows render with a shape-marked focused row and dimmed but focusable disabled rows, and a breadcrumb with a back control appears below the root frame
