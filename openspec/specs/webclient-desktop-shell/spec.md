## Purpose

The desktop Vue SPA shell surfaces, client state reduction, keyboard focus model, command drawer, layout migration, theme, accessibility, and text fallback.
## Requirements
### Requirement: The WebClient loads a local Vue SPA desktop shell
The project WebClient SHALL load Evennia's existing transport together with a locally built,
self-contained Vue 3 single-page application. It SHALL make no remote request for a runtime UI
dependency. The application SHALL provide the required brand, narrative, scene, status, local-map,
action-dock, and command-drawer surfaces and SHALL render them as self-identifying surfaces — the
narrative caption, status resources, map legend, scene label, dock menu, and prompt line — never as a
tab-title component strip. The `local-map` surface SHALL render the `webclient-local-map` panel owned
by the `map-knowledge-minimap` delivery unit. The `scene` surface SHALL render the validated
`webclient-art-panel` payload as the stage backdrop: the current scene when the panel is available,
and a truthful degrade to the mode's gradient stage (never an invented image) whenever the asset is
missing, pending without a prior image, failed, invalid, or the OOB channel is unavailable.

#### Scenario: Offline page load has its UI dependencies
- **WHEN** the WebClient is opened with all non-local network requests blocked
- **THEN** the transport code, the Vite-built Vue application, the project modules, and the theme load from the project origin without a CDN failure

#### Scenario: The minimap renders while the scene degrades to its gradient stage
- **WHEN** the shell renders the local_map payload and the art panel is unavailable, missing, or failed
- **THEN** the local-map surface renders the validated `local_map` payload, and the stage backdrop renders the mode gradient with no invented image

#### Scenario: The scene renders when the validated panel is available
- **WHEN** the `webclient-art-panel` payload is available in the current snapshot
- **THEN** the stage backdrop renders the scene cover-cropped behind the HUD surfaces, with the scene label and alternative text rendered as text outside the bitmap

#### Scenario: The shell renders self-identifying surfaces without a tab strip
- **WHEN** the shell mounts
- **THEN** no tab-title chrome is rendered anywhere, every required surface is present, and each surface carries its own self-identifying content instead of a component-name tab title

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

### Requirement: Narrative output remains the authoritative text surface
The shell SHALL route Evennia's existing narrative and command output to a scrollable narrative log without parsing it to infer panel state. Because the portal converts server output to HTML before the `text` message is sent, the narrative log SHALL render that stream through the `webclient-narrative-markup` allowlist pipeline rather than inserting it as a single text node; it SHALL NOT display markup source to the player, and it SHALL NOT interpret anything outside that pipeline's allowlist. When the player has scrolled away from the bottom, new output SHALL increment an unread indicator without forcing the viewport to the bottom; the indicator SHALL be a labeled control that states its count and its jump action — a button reading "↓ N 則新訊息（點擊返回最新）" or equivalent — SHALL be announced through a polite live region, SHALL be hidden entirely while the count is zero, and SHALL, when activated, scroll the log to the latest output and clear the count, exactly as scrolling to the bottom does. Narrative output SHALL remain usable if every structured renderer is unavailable, and SHALL remain usable if a message cannot be fully tokenized — such a message degrades to readable literal text rather than suppressing the log.

#### Scenario: New text does not disrupt scrollback reading
- **WHEN** the player is reading older narrative above the bottom and new text arrives
- **THEN** the scroll position is preserved and a visible unread count increases

#### Scenario: The unread marker names its action and clears on use
- **WHEN** the player is scrolled away from the bottom, new text arrives, and the player activates the unread marker
- **THEN** the marker shows a count label with an explicit jump action, the log scrolls to the latest output, the count clears, and the marker disappears while the count is zero

#### Scenario: Structured failure does not suppress narrative
- **WHEN** status validation and OOB initialization fail
- **THEN** ordinary text output continues to appear in the narrative log

#### Scenario: Converted server output renders as text, not as markup source
- **WHEN** the server sends ordinary room, command, or narrator output that the portal converted to HTML
- **THEN** the narrative shows the styled, line-broken prose and no element, attribute, or entity source characters are visible

### Requirement: Client state reduction is strict and atomic
The client state store SHALL validate protocol, transport generation, epoch, revision, mode, panel allowlist, layout version, and panel schema before publishing state to renderers. `connection_open` SHALL start a new local generation in `awaiting_initial_snapshot`, retire the prior epoch in bounded memory, clear prior panel state, and lock mutations. Only that generation's first valid full snapshot with a non-retired epoch SHALL establish active state. Once active, a different epoch on the same generation, an older receiver generation, a non-newer active-epoch revision, or any malformed message SHALL be discarded. Included panels SHALL replace completely, and subscribers SHALL observe no partially applied message.

#### Scenario: Malformed update changes no panel
- **WHEN** a multi-panel update contains one malformed included panel
- **THEN** the entire update is rejected and no subscriber observes partially replaced state

#### Scenario: Subscribers observe only committed state
- **WHEN** a valid snapshot or update is accepted
- **THEN** subscribed renderers receive one notification after the complete new state becomes the store baseline

#### Scenario: Same-transport epoch replacement is forbidden
- **WHEN** an active transport generation receives a valid full snapshot with an epoch different from its adopted epoch
- **THEN** the store rejects it and does not clear or replace current state

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

### Requirement: Browser persistence is versioned and presentation-only
Local browser storage SHALL contain only a bounded wrapper with project layout version, safe dimensions/tab state, and harmless display preferences. It SHALL contain no transport generation, active or retired epoch, revision, panel payload, actor identifier, request result, command text, credential, or canonical game state. Known project layout versions SHALL migrate explicitly; malformed, oversized, missing, stock, or unknown versions SHALL reset to the version-1 default while preserving required components.

#### Scenario: Known layout version migrates
- **WHEN** a stored project layout uses a version with a registered migration
- **THEN** the migration produces the current layout and retains only supported display preferences

#### Scenario: Unknown layout version resets safely
- **WHEN** localStorage contains an unknown version or malformed configuration
- **THEN** the shell removes or ignores it and loads the approved default with every required component

#### Scenario: Stock layout state is not imported
- **WHEN** a browser profile contains Evennia's pre-project GoldenLayout storage keys
- **THEN** version 1 does not treat those values as canonical project layout state

### Requirement: Theme and controls remain accessible
The shell SHALL use the approved desktop palette — near-black charcoal surfaces, warm paper-gray text, a deep seal-red accent, and an ok-green connection indicator — while pairing color with labels, borders, icons, or shapes, and SHALL use a serif face for narrative and headings with a legible UI face for controls. Focus SHALL be visibly indicated, resource values SHALL include numeric text, disabled reasons SHALL be programmatically associated with controls, action results SHALL use a non-interrupting live region, and reduced-motion preference SHALL disable nonessential transitions. Every server-authored value carried in a structured presentation panel — labels, descriptions, reasons, names, and legend entries — SHALL be inserted as text and SHALL NEVER be treated as markup. The single bounded exception is the narrative transport stream, which the portal already converts to HTML and escapes player content within; it SHALL be rendered only through the `webclient-narrative-markup` allowlist pipeline, which constructs nodes exclusively through element and text-node constructors and degrades everything outside its allowlist to literal text. No other surface SHALL render server bytes as markup.

#### Scenario: Keyboard focus does not depend on color alone
- **WHEN** keyboard focus moves between action controls
- **THEN** the focused control is distinguishable by a non-color visual indicator and an accessible focus state

#### Scenario: The seal-red accent never carries meaning alone
- **WHEN** a seal-red (vermilion) element is rendered
- **THEN** it is paired with a label, border, glyph, or shape, and seal-red small text on dark surfaces is not used

#### Scenario: Disabled rows expose their reason programmatically
- **WHEN** a disabled action-dock cell is rendered
- **THEN** its disabled reason is programmatically associated with the cell (for example `aria-describedby`) and is readable in the detail pane or a visually hidden description, at every navigation depth including the root

#### Scenario: Player-authored label is not executed as markup
- **WHEN** a server-authored display value in a structured panel contains HTML-like player text
- **THEN** the browser renders it as literal text and no element or script is created from it

#### Scenario: The narrative exception is bounded to one pipeline
- **WHEN** the shell's panel renderers are inspected
- **THEN** only the narrative log renders converted markup, every other renderer inserts server values as text, and no renderer uses an HTML-parsing API

### Requirement: Connection loss locks stale controls
On WebSocket loss after a successful connection, the shell SHALL preserve the last rendered state under a non-dismissible offline overlay and SHALL prevent all graphical mutation submission. Reconnection SHALL request a full snapshot and remove the overlay only after a valid new-epoch snapshot is adopted.

#### Scenario: Offline controls cannot submit
- **WHEN** the active WebSocket closes while an enabled test action is focused
- **THEN** the offline overlay appears and keyboard or mouse activation emits no mutation

#### Scenario: Reconnect waits for canonical state
- **WHEN** the socket reconnects but no valid full snapshot has arrived
- **THEN** the offline/synchronizing lock remains until the new-epoch snapshot is accepted

#### Scenario: A dropped first sync is re-requested on a bounded budget
- **WHEN** the first reconnection `ui_sync` lands before the portal re-attaches the account puppet and the snapshot is dropped
- **THEN** the client re-requests `ui_sync` on a bounded, disarming schedule, ceasing on adoption, on disconnect, or once the attempt budget is spent

#### Scenario: Extremely stale reconnections recover once
- **WHEN** the authenticated snapshot never arrives after the bounded re-request budget, so the portal has lost the browser's authenticated session
- **THEN** the client reloads the page at most once per tab session (guarded by a persistent marker) and otherwise leaves the synchronizing lock in place

#### Scenario: The overlay stays off before any successful connection
- **WHEN** a first-time visitor opens the WebClient and no connection has ever reached the active phase
- **THEN** the offline overlay remains hidden so the stock connect/create prompt underneath stays visible and usable

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

