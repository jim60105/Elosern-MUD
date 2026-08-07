## Purpose

Delta to the desktop-shell current contract: the `/` key toggles the command drawer and never fires
while an editable control is focused, the drawer defaults to closed behind an actionable entry button,
the borrowed free-form send closes the drawer only when its action actually dispatches, and the
narrative surface gains player input lines separated from server output by a divider.

## MODIFIED Requirements

### Requirement: Keyboard routing is menu-first and submission-safe

After initial synchronization and after every completed or rejected action whose declared presentation
revision has been accepted, the action dock SHALL own focus. Key events SHALL be dispatched through the
WebClient plugin `onKeydown` contract, claimed exactly when the router consumed them, rather than bound
directly to the document. Arrow keys SHALL move within the active finite menu, Enter SHALL confirm an
enabled focused item, Escape SHALL pop exactly one menu level, Space SHALL be reserved for multi-select
toggles, and `/` SHALL toggle the command drawer: when the drawer is closed it SHALL open and focus the
input field, and when the drawer is already open with no editable control focused it SHALL close and
restore action-dock focus. A `/` pressed while an editable control is focused SHALL be ordinary text
input: it SHALL not close the drawer and SHALL never be claimed by the router, so commands or text that
contain a slash remain typeable in the drawer field and in other editable controls (creation forms,
rest forms). Pointer activation of a rendered row SHALL be admitted and SHALL traverse the identical
focus, disabled-explanation, and submission-gating path as Enter, as specified by
`webclient-pointer-activation`. Disabled entries SHALL remain focusable for their explanation but SHALL
NOT submit. Held or repeated Enter and all mutation submissions while one is in flight or awaiting its
declared presentation revision SHALL be suppressed, and no combination of key and pointer input SHALL
emit more than one request per deliberate activation.

#### Scenario: Keyboard navigation and backtracking are deterministic
- **WHEN** the player navigates a test menu with arrows, enters a submenu, and presses Escape
- **THEN** focus follows the menu geometry, exactly one menu level closes, and the prior focused item is restored

#### Scenario: Disabled item explains without submitting
- **WHEN** focus moves to a disabled item and the player presses Enter or clicks it
- **THEN** its explanation remains readable and no `ui_action` message is sent

#### Scenario: Repeated Enter submits once
- **WHEN** Enter key repeat fires while a proof action is being submitted
- **THEN** the browser emits one request and keeps mutation controls locked until resolution

#### Scenario: Key dispatch goes through the plugin contract
- **WHEN** the player presses a navigation key over the action dock
- **THEN** the project plugin's `onKeydown` claims it, the plugin handler reports no unhandled keydown,
  and keys the router does not consume still reach the stock plugins

#### Scenario: Slash toggles the drawer from the action dock
- **WHEN** the drawer is closed and the player presses `/` over the action dock
- **THEN** the drawer opens and the input field receives focus
- **WHEN** the drawer is open, no editable control is focused, and the player presses `/` again
- **THEN** the drawer closes and action-dock focus is restored

#### Scenario: A slash typed in an editable control is text
- **WHEN** an editable control (the drawer field, a creation form, or a rest form) is focused and the
  player presses `/`
- **THEN** the drawer stays open (if it was open) and a literal `/` is typed into that control, so
  text such as `whisper /ooc` remains fully typeable

### Requirement: The command drawer preserves ordinary text control

The drawer SHALL default to closed: its input row is hidden until the player opens it, and the only
visible drawer element is an actionable entry button (a real `<button type="button">`) with an
accessible name such as `指令輸入（/）` and an `aria-expanded` state, so the drawer stays discoverable
and a stale localStorage layout never removes the entry point. The drawer SHALL open and focus the
input field when the player presses `/` while the drawer is closed, when the player activates the
entry button with a pointer or keyboard, or when a dock borrows the drawer for its own free-form
dialogue. Focusing the input field by any of those entrance paths SHALL make the drawer ready to send
through its single send implementation. The drawer SHALL send ordinary text through Evennia's text
message, preserve command history, and SHALL NOT translate text into `ui_action`. Exactly one send
implementation SHALL own the field, so a single key press can never traverse two send paths. Pressing
Enter without Shift while the drawer field is focused SHALL send exactly one command regardless of how
the drawer was opened; Shift+Enter SHALL insert a newline without sending. After a successful ordinary
text send the drawer SHALL clear the field, remain open, and retain focus, so consecutive commands are
typeable without any pointer interaction. Escape SHALL close the drawer without sending and restore
action-dock focus. When a dock has borrowed the drawer for one of its own actions — free-form
dialogue — a successful send SHALL clear the field, close the drawer, and restore action-dock focus,
because that interaction has completed; when the action client is locked (offline, awaiting the first
snapshot, or another mutation in flight) the borrowed send SHALL NOT dispatch, SHALL keep the typed
speech in the field, and SHALL keep the drawer open so nothing is silently lost. A borrowed-drawer
reference SHALL be released whenever the drawer closes for any reason other than that dock's own
successful send, and whenever a send is routed as ordinary text, so a cancelled or abandoned dock
interaction can never capture a later unrelated command. The drawer SHALL remain usable when OOB
controls are disabled.

#### Scenario: The drawer is closed until the player opens it
- **WHEN** the shell mounts the `command-drawer` component in a fresh browser context
- **THEN** the input row is not visible, the entry button is visible with its accessible name and an
  `aria-expanded="false"` state, and the input field is focused only after an open action (a `/` press
  or an activation of the entry button)

#### Scenario: The entry button opens and focuses the field
- **WHEN** the player activates the drawer entry button with a click or keyboard
- **THEN** the drawer opens, the entry button reports `aria-expanded="true"`, and the input field
  receives focus

#### Scenario: Keyboard-only command send restores focus
- **WHEN** the player opens the drawer with `/`, enters a command, and sends it
- **THEN** the command travels through the text input path, the field clears, and focus stays in the
  field for the next command, so consecutive commands need no pointer interaction

#### Scenario: Consecutive commands need no pointer interaction
- **WHEN** the player opens the drawer with `/`, sends a command, and immediately types a second command
  and sends it
- **THEN** both commands travel through the text input path, the field is cleared between them, and
  focus never leaves the field

#### Scenario: Escape cancels without sending
- **WHEN** the player opens the drawer, enters unsent text, and presses Escape
- **THEN** no text or UI action is sent, the drawer closes, and action-dock focus is restored

#### Scenario: A pointer-opened field sends on Enter without a prior slash
- **WHEN** the player activates the drawer entry button, types a command in the now-focused field, and
  presses Enter
- **THEN** exactly one text message is sent through the single drawer send path, the field clears, and
  focus stays in the field; the plugin contract reports no unhandled keydown

#### Scenario: Shift+Enter inserts a newline without sending
- **WHEN** the drawer field is focused and the player presses Shift+Enter
- **THEN** no command is sent and the text insertion point moves to a new line

#### Scenario: A dock-borrowed send returns focus to the dock
- **WHEN** the exploration dock opens the drawer for free-form dialogue and the player sends the speech
  while the action client is unlocked
- **THEN** exactly one `explore.talk_freeform` action is submitted, the drawer closes, and action-dock
  focus is restored

#### Scenario: A locked borrowed send keeps the speech
- **WHEN** the exploration dock opens the drawer for free-form dialogue and the player sends the speech
  while the action client is locked
- **THEN** no action is submitted, no text is lost (the speech remains in the field), the drawer stays
  open, and no input line is echoed

#### Scenario: One key press sends exactly one command
- **WHEN** the player presses Enter in the drawer field
- **THEN** exactly one text message is sent regardless of how the drawer was opened

#### Scenario: A cancelled dialogue cannot capture a later command
- **WHEN** the player opens free-form dialogue, presses Escape without sending, and later sends an
  ordinary command through the drawer
- **THEN** the command travels through the ordinary text path, no `explore.talk_freeform` action is
  submitted, and the typed text is not delivered as speech to the previously selected NPC

## ADDED Requirements

### Requirement: Player input lines are part of the narrative stream with a divider

The narrative log SHALL render, in addition to server text, one input line per deliberate player action:
a typed drawer send echoes the exact raw text the player sent, and a button-triggered mutation echoes
its resolved command line (see the `webclient-input-narrative` capability). Input lines SHALL be
inserted as literal text through the same single append path as narrative output — preserving the
scroll position, driving the same polite unread marker, and forcing a new line — and SHALL be styled
distinctly from server output (`.inp`). A `.narrative-divider` hairline SHALL separate each input line
from the preceding server or input line so system prose and player actions never visually merge while
re-reading; the divider SHALL NOT appear before the very first line of the log. One input event
(divider + input line together) SHALL count as exactly one unread increment and one scroll-keep event.
An input line SHALL never be executed, replayed, or sent back to the server. The append path SHALL
handle an input line exactly like a server line that fails to tokenize: degrade to literal text and
never suppress the log.

#### Scenario: A typed command appears with a divider
- **WHEN** the player types a command in the drawer and sends it while scrolled above the bottom
- **THEN** the narrative appends one `.inp` line containing the raw sent text, preceded by a
  `.narrative-divider`, the scroll position is preserved, the unread marker increases by exactly one,
  and the text is never sent back to the server

#### Scenario: A button action appears with a divider
- **WHEN** the player submits `explore.move` via the dock or the minimap
- **THEN** the narrative appends one `.inp` line with its resolved command line, preceded by a
  `.narrative-divider`, and the server output that follows appears after it

#### Scenario: The first line needs no separator
- **WHEN** a fresh log's first entry is an input line
- **THEN** it renders with the input style but without a preceding divider hairline

#### Scenario: Input lines are never executed
- **WHEN** the player re-reads the log and its input lines sit alongside server lines
- **THEN** no line is ever sent to the server, nothing is replayed, and the log content has no effect on
  game state