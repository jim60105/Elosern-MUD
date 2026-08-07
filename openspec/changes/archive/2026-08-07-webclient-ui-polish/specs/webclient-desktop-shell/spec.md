## MODIFIED Requirements

### Requirement: The WebClient loads a local desktop GoldenLayout shell
The project WebClient SHALL load Evennia's existing transport together with locally served, pinned, license-documented jQuery and GoldenLayout assets. It SHALL make no remote request for a runtime UI dependency. Layout version 1 SHALL provide required header, narrative, art, status, local-map, action-dock, and command-drawer components, and SHALL render them without a GoldenLayout tab strip (`settings.hasHeaders: false`): each surface SHALL be identified by its own content — the narrative log, status resources, map legend, art caption, dock menu, and prompt line — never by a GoldenLayout tab title. The `local-map` component SHALL render the `webclient-local-map` panel owned by the `map-knowledge-minimap` delivery unit. The `art` component SHALL render the validated `webclient-art-panel` payload: the current scene and its contextual portrait overlay when the panel is available, and a truthful scene placeholder (never an invented image) whenever the asset is missing, pending without a prior image, failed, invalid, or the OOB channel is unavailable.

#### Scenario: Offline page load has its UI dependencies
- **WHEN** the WebClient is opened with all non-local network requests blocked
- **THEN** the transport code, GoldenLayout shell, project modules, and theme load from the project origin without a CDN failure

#### Scenario: The minimap renders while art degrades to its placeholder
- **WHEN** the version-1 shell renders the local_map payload and the art panel is unavailable, missing, or failed
- **THEN** the local-map surface renders the validated `local_map` payload, and the art surface renders the truthful scene placeholder with no invented image

#### Scenario: Art renders when the validated panel is available
- **WHEN** the `webclient-art-panel` payload is available in the current snapshot
- **THEN** the art surface renders the scene with cover-style 16:9 layout and its contextual portrait overlay, with the scene label and alternative text outside the bitmap

#### Scenario: The shell renders without a GoldenLayout tab strip
- **WHEN** the version-1 layout mounts
- **THEN** no GoldenLayout tab header (`.lm_header`) is rendered anywhere, every required component is present, and each surface carries its own self-identifying content instead of a component-name tab title

### Requirement: Required desktop surfaces remain visible and usable
The narrative log SHALL occupy the primary reading area, with supporting header, status, placeholders, and action dock visible at 1440x900 and 1280x720. Required components and the action dock SHALL NOT be permanently closable. The foundation SHALL target desktop only and SHALL NOT claim mobile acceptance. The header SHALL show the game title, the current location, the world date/time, and the connection state, with the connected state marked by an ok-green dot paired with a label — never a raw mode label in place of location. The action dock SHALL render as the approved command surface: a seal-red frame, a guidance line naming the shortcuts (direction keys to choose, Enter to confirm, Escape to return, `/` to open the command input), and its items as grid buttons, with the focused cell marked by a seal-red fill plus a leading glyph, unfocused cells bordered, and disabled cells dimmed but focusable for their explanation. Submenus SHALL render as an item grid beside a detail pane that names the focused item, its availability, and the next key action.

#### Scenario: Standard desktop viewport contains every required surface
- **WHEN** the shell renders at 1440x900
- **THEN** every required component and the command-drawer control is visible without overlapping the narrative input path

#### Scenario: Minimum desktop viewport remains usable
- **WHEN** the shell renders at 1280x720
- **THEN** every required component remains reachable and the player can read narrative, inspect status, and open the command drawer

#### Scenario: Mounting the shell retires the degraded text fallback
- **WHEN** the GoldenLayout shell mounts into its container
- **THEN** the stock text-only fallback is hidden so it cannot stack with the mounted shell in normal document flow and push required surfaces below the visible viewport

#### Scenario: The header identifies location, time, and connection without a mode label
- **WHEN** the shell is connected in exploration mode
- **THEN** the header shows the game title, the current location label from the synced status panel, the world date/time, and an ok-green "● 已連線" indicator, and no raw mode label is rendered

#### Scenario: The action dock renders as a framed grid with a guidance line
- **WHEN** the action dock is mounted in any mode
- **THEN** it is framed in seal red, carries a guidance line naming the shortcut keys, renders its current menu items as grid cells with a shape-marked focused cell and dimmed disabled cells, and its submenus show a detail pane beside the item grid

### Requirement: The command drawer preserves ordinary text control
Pressing `/` outside an editable field SHALL open and focus the command drawer. Focusing the drawer field by any means — keyboard `/`, a dock-borrowed free-form dialogue, or a direct pointer click — SHALL make the drawer ready to send through its single send implementation. The drawer SHALL send ordinary text through Evennia's text message, preserve command history, and SHALL NOT translate text into `ui_action`. Exactly one send implementation SHALL own the drawer field, so a single key press can never traverse two send paths. Pressing Enter without Shift while the drawer field is focused SHALL send exactly one command regardless of how the drawer was opened; Shift+Enter SHALL insert a newline without sending. After a successful ordinary text send the drawer SHALL clear the field, remain open, and retain focus, so consecutive commands are typeable without any pointer interaction. Escape SHALL close the drawer without sending and restore action-dock focus. When a dock has borrowed the drawer for one of its own actions — free-form dialogue — a successful send SHALL clear the field, close the drawer, and restore action-dock focus, because that interaction has completed. A borrowed-drawer reference SHALL be released whenever the drawer closes for any reason other than that dock's own successful send, and whenever a send is routed as ordinary text, so a cancelled or abandoned dock interaction can never capture a later unrelated command. The drawer SHALL remain usable when OOB controls are disabled.

#### Scenario: Keyboard-only command send restores focus
- **WHEN** the player opens the drawer with `/`, enters a command, and sends it
- **THEN** the command travels through the text input path, the field clears, and focus stays in the field for the next command, so consecutive commands need no pointer interaction

#### Scenario: Consecutive commands need no pointer interaction
- **WHEN** the player opens the drawer with `/`, sends a command, and immediately types a second command and sends it
- **THEN** both commands travel through the text input path, the field is cleared between them, and focus never leaves the field

#### Scenario: A pointer-focused field sends on Enter without a prior slash
- **WHEN** the player clicks directly into the drawer field without opening the drawer first, types a command, and presses Enter
- **THEN** exactly one text message is sent through the single drawer send path, the field clears, and focus stays in the field; the plugin contract reports no unhandled keydown

#### Scenario: Shift+Enter inserts a newline without sending
- **WHEN** the drawer field is focused and the player presses Shift+Enter
- **THEN** no command is sent and the text insertion point moves to a new line

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
