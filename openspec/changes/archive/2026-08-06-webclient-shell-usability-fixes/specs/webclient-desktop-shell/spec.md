## MODIFIED Requirements

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
