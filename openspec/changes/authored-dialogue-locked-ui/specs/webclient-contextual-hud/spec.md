# Spec Delta

## MODIFIED Requirements

### Requirement: Dialogue choices appear centred over the stage after the line is fully read
While the committed mode is `dialogue` and the committed `dialogue` panel is available, the client SHALL present the conversation's choices as one choice list in the stage's `choices` anchor, and nowhere else. The list SHALL render only while the message window reports that a native response last page is fully shown or an authored scene has received its explicit final-page finish activation, with no pending action mark, and while no action the player dispatched is in flight.

#### Scenario: Any unread or in-flight moment hides the list
- **WHEN** a page is still typing, a further page is not yet read, or a pick or free-form speech awaits its reply
- **THEN** the list is not rendered

#### Scenario: The rows follow the payload exactly
- **WHEN** the choice list renders
- **THEN** its rows are, in order: one pick row per `dialogue.choices` entry in payload order, each carrying the digit badge of its 1-based position and its bounded label; a `⌨ 自由對話` row; a `↦ 移動…` row; and a `✕ 結束對話` row — and it renders no row the panel does not back, a lock and canonical focus/hover hint for locked selectable-refusal topics; operationally disabled picks retain no-dispatch behavior

#### Scenario: Picks and exits dispatch their exact intents
- **WHEN** the player activates a pick row, or an enabled exit row
- **THEN** a pick dispatches `explore.talk_scripted` with the committed source-correct action payload plus its dispatcher selection identity through the single dispatch entry, and an enabled exit row dispatches the unchanged `explore.move` payload of its committed move row

#### Scenario: The free-form and exit rows dispatch nothing themselves
- **WHEN** the player activates `⌨ 自由對話`, or `✕ 結束對話`
- **THEN** `⌨ 自由對話` expands the command line and focuses its field through the free-form borrow path, bound to the host, and dispatches nothing itself; `✕ 結束對話` dispatches `explore.dialogue_leave` with `{npc_id: host.identity}` with declared lock/unread adornments and accessible hint associations only

#### Scenario: The move row borrows the scene overview's exits
- **WHEN** the player activates `↦ 移動…`
- **THEN** it dispatches nothing and replaces the choices with dedicated committed `moveItems` rows from the store view, independent of the router root, in payload order, carrying their direction glyphs, enabled destination names, disabled markers and unchanged server reasons, followed by a back row

#### Scenario: The exit rows return to the choices
- **WHEN** Escape or the back row is activated in the exit rows, or the committed room has no exits
- **THEN** the choice rows return with the `↦ 移動…` row focused, and a room without exits still shows the back row alone

#### Scenario: One composite, one tab stop, full keyboard
- **WHEN** the choice list holds focus
- **THEN** it is one keyboard composite and one tab stop: DOM focus rests on the list container, which names its focused row through an active-descendant reference; ArrowUp and ArrowDown move to the previous and next row, wrapping; Home and End move to the first and last row; Enter and Space activate the focused row; while the choice rows are shown, digit `1`–`N` activates pick N directly; and a held key's auto-repeat does not activate

#### Scenario: The active row is shown by shape and fill
- **WHEN** the list holds focus on its rows, including a disabled exit row
- **THEN** the active row is shown by shape and fill — a leading `▸` and the dock's muted-gold fill — never by colour alone, and an active disabled exit row keeps a quiet treatment that promises no action

#### Scenario: Handled keys stop at the list
- **WHEN** the list handles a key, and when `/` or an unhandled key is pressed
- **THEN** every key the list handles is consumed by it and does not reach the keyboard router or the page surface, while `/` and every key the list does not handle passes on unchanged

#### Scenario: Focus arrives, leaves, and never dangles
- **WHEN** the list appears while focus is on the message window, inside the message region, or on the document body, and when an activation is about to dispatch
- **THEN** focus moves to the list with its first row focused, and before an activation dispatches focus moves to the message window's page surface, so the list's removal never leaves focus on a removed element or the document body; a pointer activation of a row focuses that row and activates it through the same path as Enter

#### Scenario: Activations obey the dispatch lock once each
- **WHEN** a mutation is in flight or awaiting its declared presentation revision, and when key and pointer input combine
- **THEN** every activation is suppressed exactly like a dock entry, and no combination of key and pointer input emits more than one request per deliberate activation

#### Scenario: The list derives only from committed panels
- **WHEN** the list's rows and presence are computed
- **THEN** rows derive from the committed `dialogue` and `exploration` panels alone and depend on no dock frame or router descriptor, and presence derives from the window's reader state and the dispatch state, never from narrative prose

#### Scenario: The choices wait for the last page
- **WHEN** a greeting of two pages commits with three choices at the `normal` text speed
- **THEN** no choice list is rendered while page 1 types, after it is fully shown, or while page 2 types, and the list renders in the `choices` anchor with focus on its first row once page 2 is fully shown

#### Scenario: The rows follow the committed panel
- **WHEN** the list renders for a panel with three choices
- **THEN** it shows pick rows badged `1`, `2`, `3` with the panel's labels in payload order, then `⌨ 自由對話`, `↦ 移動…`, and `✕ 結束對話`, with declared lock/unread adornments and accessible hint associations only

#### Scenario: A pick dispatches the scripted keyword
- **WHEN** the player activates pick 2 through pointer, Enter, or the `2` key
- **THEN** exactly one `explore.talk_scripted` request with the committed host identity and that row's source-correct stable topic or generated keyword payload is submitted, the list is removed while the request is in flight, focus is on the message window's page surface, and the list returns after the scene final fully visible page receives a further activation (native line responses retain existing behavior)

#### Scenario: Free dialogue borrows the command line
- **WHEN** the player activates `⌨ 自由對話`
- **THEN** the command line expands with focus in its field for a freeform utterance to the host, and no action is dispatched

#### Scenario: The exit row ends the conversation
- **WHEN** the player activates `✕ 結束對話`
- **THEN** exactly one `explore.dialogue_leave` request with the committed host identity is submitted and no other action is dispatched

#### Scenario: Move swaps in the exits and Escape returns
- **WHEN** the room has two exits, one locked, and the player activates `↦ 移動…`, focuses the locked exit and presses Enter, then presses Escape
- **THEN** the list shows the two exit rows with their direction glyphs and the back row, the locked row shows its reason and nothing is submitted, and Escape returns to the choice rows with `↦ 移動…` focused

#### Scenario: A move from the list leaves the conversation
- **WHEN** the player activates `↦ 移動…` and then an enabled exit row
- **THEN** exactly one `explore.move` request with the committed move row's unchanged payload is submitted, the movement settlement clears the session through the existing seam, and the committed mode returns to `exploration` with the dock at the new room's overview

#### Scenario: The list is one tab stop and keeps its keys
- **WHEN** the list has focus and the player presses Tab, then Shift+Tab back, then ArrowDown twice and Enter
- **THEN** Tab leaves the list in one step, the list is reached again in one step, the arrows move the active-descendant reference, Enter activates the focused row once, and the keyboard router saw none of those arrow or Enter keys

#### Scenario: The choices never show beside unread text
- **WHEN** a reply's first page is on screen and further lines of the same response arrive
- **THEN** the list stays unrendered until the authored scene explicit finish activation, or the native response last page is fully shown

#### Scenario: Reconnect replays scene from first line
- **WHEN** the client reconnects to the same valid delivered scene
- **THEN** choices stay hidden until that replay finishes explicitly and replay submits no new selection/effect

#### Scenario: Locked topic is intentionally selectable
- **WHEN** a visibly locked formal topic row receives Enter
- **THEN** its permitted refusal is selected, canonical requirement hint is accessible and no formal reading completion is produced
