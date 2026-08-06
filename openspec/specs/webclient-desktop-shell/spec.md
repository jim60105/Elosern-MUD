## Purpose

The desktop GoldenLayout surfaces, client state reduction, keyboard focus model, command drawer, layout migration, theme, accessibility, and text fallback.

## Requirements


### Requirement: The WebClient loads a local desktop GoldenLayout shell
The project WebClient SHALL load Evennia's existing transport together with locally served, pinned, license-documented jQuery and GoldenLayout assets. It SHALL make no remote request for a runtime UI dependency. Layout version 1 SHALL provide required header, narrative, art, status, local-map, action-dock, and command-drawer components. The `local-map` component SHALL render the `webclient-local-map` panel owned by the `map-knowledge-minimap` delivery unit. The `art` component SHALL render the validated `webclient-art-panel` payload: the current scene and its contextual portrait overlay when the panel is available, and a truthful scene placeholder (never an invented image) whenever the asset is missing, pending without a prior image, failed, invalid, or the OOB channel is unavailable.

#### Scenario: Offline page load has its UI dependencies
- **WHEN** the WebClient is opened with all non-local network requests blocked
- **THEN** the transport code, GoldenLayout shell, project modules, and theme load from the project origin without a CDN failure

#### Scenario: The minimap renders while art degrades to its placeholder
- **WHEN** the version-1 shell renders the local_map payload and the art panel is unavailable, missing, or failed
- **THEN** the local-map surface renders the validated `local_map` payload, and the art surface renders the truthful scene placeholder with no invented image

#### Scenario: Art renders when the validated panel is available
- **WHEN** the `webclient-art-panel` payload is available in the current snapshot
- **THEN** the art surface renders the scene with cover-style 16:9 layout and its contextual portrait overlay, with the scene label and alternative text outside the bitmap

### Requirement: Required desktop surfaces remain visible and usable
The narrative log SHALL occupy the primary reading area, with supporting header, status, placeholders, and action dock visible at 1440x900 and 1280x720. Required components and the action dock SHALL NOT be permanently closable. The foundation SHALL target desktop only and SHALL NOT claim mobile acceptance.

#### Scenario: Standard desktop viewport contains every required surface
- **WHEN** the shell renders at 1440x900
- **THEN** every required component and the command-drawer control is visible without overlapping the narrative input path

#### Scenario: Minimum desktop viewport remains usable
- **WHEN** the shell renders at 1280x720
- **THEN** every required component remains reachable and the player can read narrative, inspect status, and open the command drawer

#### Scenario: Mounting the shell retires the degraded text fallback
- **WHEN** the GoldenLayout shell mounts into its container
- **THEN** the stock text-only fallback is hidden so it cannot stack with the mounted shell in normal document flow and push required surfaces below the visible viewport

### Requirement: Narrative output remains the authoritative text surface
The shell SHALL route Evennia's existing narrative and command output to a scrollable narrative log without parsing it to infer panel state. Because the portal converts server output to HTML before the `text` message is sent, the narrative log SHALL render that stream through the `webclient-narrative-markup` allowlist pipeline rather than inserting it as a single text node; it SHALL NOT display markup source to the player, and it SHALL NOT interpret anything outside that pipeline's allowlist. When the player has scrolled away from the bottom, new output SHALL increment an unread indicator without forcing the viewport to the bottom. Narrative output SHALL remain usable if every structured renderer is unavailable, and SHALL remain usable if a message cannot be fully tokenized — such a message degrades to readable literal text rather than suppressing the log.

#### Scenario: New text does not disrupt scrollback reading
- **WHEN** the player is reading older narrative above the bottom and new text arrives
- **THEN** the scroll position is preserved and a visible unread count increases

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
After initial synchronization and after every completed or rejected action whose declared presentation revision has been accepted, the action dock SHALL own focus. Key events SHALL be dispatched through the WebClient plugin `onKeydown` contract, claimed exactly when the router consumed them, rather than bound directly to the document. Arrow keys SHALL move within the active finite menu, Enter SHALL confirm an enabled focused item, Escape SHALL pop exactly one menu level, Space SHALL be reserved for multi-select toggles, and `/` SHALL open the command drawer. Pointer activation of a rendered row SHALL be admitted and SHALL traverse the identical focus, disabled-explanation, and submission-gating path as Enter, as specified by `webclient-pointer-activation`. Disabled entries SHALL remain focusable for their explanation but SHALL NOT submit. Held or repeated Enter and all mutation submissions while one is in flight or awaiting its declared presentation revision SHALL be suppressed, and no combination of key and pointer input SHALL emit more than one request per deliberate activation.

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
- **THEN** the project plugin's `onKeydown` claims it, the plugin handler reports no unhandled keydown, and keys the router does not consume still reach the stock plugins

### Requirement: The command drawer preserves ordinary text control
Pressing `/` outside an editable field SHALL open and focus the command drawer. The drawer SHALL send ordinary text through Evennia's text message, preserve command history, and SHALL NOT translate text into `ui_action`. Exactly one send implementation SHALL own the drawer field, so a single key press can never traverse two send paths. After a successful ordinary text send the drawer SHALL clear the field, remain open, and retain focus, so consecutive commands are typeable without any pointer interaction. Escape SHALL close the drawer without sending and restore action-dock focus. When a dock has borrowed the drawer for one of its own actions — free-form dialogue — a successful send SHALL clear the field, close the drawer, and restore action-dock focus, because that interaction has completed. A borrowed-drawer reference SHALL be released whenever the drawer closes for any reason other than that dock's own successful send, and whenever a send is routed as ordinary text, so a cancelled or abandoned dock interaction can never capture a later unrelated command. The drawer SHALL remain usable when OOB controls are disabled.

#### Scenario: Keyboard-only command send restores focus
- **WHEN** the player opens the drawer with `/`, enters a command, and sends it
- **THEN** the command travels through the text input path, the field clears, and focus stays in the field for the next command, so consecutive commands need no pointer interaction

#### Scenario: Consecutive commands need no pointer interaction
- **WHEN** the player opens the drawer with `/`, sends a command, and immediately types a second command and sends it
- **THEN** both commands travel through the text input path, the field is cleared between them, and focus never leaves the field

#### Scenario: Escape cancels without sending
- **WHEN** the player opens the drawer, enters unsent text, and presses Escape
- **THEN** no text or UI action is sent, the drawer closes, and action-dock focus is restored

#### Scenario: A dock-borrowed send returns focus to the dock
- **WHEN** the exploration dock opens the drawer for free-form dialogue and the player sends the speech
- **THEN** exactly one `explore.talk_freeform` action is submitted, the drawer closes, and action-dock focus is restored

#### Scenario: One key press sends exactly one command
- **WHEN** the player presses Enter in the drawer field
- **THEN** exactly one text message is sent regardless of how the drawer was opened

#### Scenario: A cancelled dialogue cannot capture a later command
- **WHEN** the player opens free-form dialogue, presses Escape without sending, and later sends an ordinary command through the drawer
- **THEN** the command travels through the ordinary text path, no `explore.talk_freeform` action is submitted, and the typed text is not delivered as speech to the previously selected NPC

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
The shell SHALL use the approved charcoal, warm-paper, and vermilion visual language while pairing color with labels, borders, icons, or shapes. Focus SHALL be visibly indicated, resource values SHALL include numeric text, disabled reasons SHALL be programmatically associated with controls, action results SHALL use a non-interrupting live region, and reduced-motion preference SHALL disable nonessential transitions. Every server-authored value carried in a structured presentation panel — labels, descriptions, reasons, names, and legend entries — SHALL be inserted as text and SHALL NEVER be treated as markup. The single bounded exception is the narrative transport stream, which the portal already converts to HTML and escapes player content within; it SHALL be rendered only through the `webclient-narrative-markup` allowlist pipeline, which constructs nodes exclusively through element and text-node constructors and degrades everything outside its allowlist to literal text. No other surface SHALL render server bytes as markup.

#### Scenario: Keyboard focus does not depend on color alone
- **WHEN** keyboard focus moves between action controls
- **THEN** the focused control is distinguishable by a non-color visual indicator and an accessible focus state

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

#### Scenario: The overlay stays off before any successful connection
- **WHEN** a first-time visitor opens the WebClient and no connection has ever reached the active phase
- **THEN** the offline overlay remains hidden so the stock connect/create prompt underneath stays visible and usable
