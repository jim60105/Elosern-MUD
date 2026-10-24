## MODIFIED Requirements

### Requirement: Keyboard routing is menu-first and submission-safe

After initial synchronization and after every completed or rejected action whose declared
presentation revision has been accepted, the current mode's focus home SHALL own focus. Key events
SHALL be dispatched through the public keyboard bridge (the `window.Elosern.KeyboardRouter` handle
contract), claimed exactly when the router or focused compass consumed them, rather than bound directly to the
document.

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
- **THEN** the command panel carries no 建議 pill at all
- **WHEN** the status is `generating`, `ready`, or `degraded`
- **THEN** the command panel carries the 建議 pill and activating it opens the client-local suggestions card without dispatching a `ui_action` and without pushing a router frame

#### Scenario: Exploration root exposes the G2 hierarchical keys
- **WHEN** the exploration root renders beside the compass and the presence rail
- **THEN** the router's exploration root carries no item; an interact target is the rail's `target-<identity>` entry, outside the router, whose Enter opens its client-local verb card without submitting and without pushing a router frame; exits, rail entries, the place card's room actions, and the 建議 pill are not router items

#### Scenario: The dock root omits the navigation-carried entries
- **WHEN** the party and quest surfaces are available and the dock renders its exploration root
- **THEN** the action dock carries no 隊伍 or 任務 entry - those surfaces are opened from the top
  navigation bar or their hotkeys

#### Scenario: The router is inert while the dock is collapsed
- **WHEN** the committed mode is dialogue, focus is on the document body, and the player presses ArrowDown, Enter, Space, and Escape
- **THEN** the bridge reports each key unclaimed by the router, the router's focused key and depth are unchanged, and no request is emitted

#### Scenario: The router owns the menu and command-line keys
- **WHEN** the router handles a navigation key over a menu
- **THEN** arrow keys move within the active finite menu, Enter confirms an enabled focused item, Escape pops exactly one menu level, Space is reserved for multi-select toggles, and `/` opens the command line
- **AND** disabled entries remain focusable for their explanation but never submit

#### Scenario: The mode's focus home reclaims focus after synchronization and actions
- **WHEN** the shell reaches initial synchronization, or an action completes or is rejected with its declared presentation revision accepted
- **THEN** the current mode's focus home owns focus: the exit compass at the exploration root, the active dock row container in other dock frames, or in dialogue mode the message window's focus target, as `webclient-contextual-hud` "The command region collapses in dialogue mode and the message window spans the band" defines

#### Scenario: Slash expands the line and focuses the field without typing itself
- **WHEN** `/` opens the command line from the focus home
- **THEN** a collapsed line expands, in either state focus moves into the input field once the field is rendered, and no literal `/` is inserted into it

#### Scenario: Escape from the command field returns to the focus home
- **WHEN** the command field holds focus and the player presses Escape
- **THEN** nothing is sent, focus returns to the current mode's focus home, and the command line collapses

#### Scenario: Dialogue claims only slash and the choice list keeps its own keys
- **WHEN** the committed mode is `dialogue`
- **THEN** the router claims only `/`; arrows, Enter, Space, Escape, and digits are unclaimed by it, so the hidden dock is never navigated or activated, and the dialogue choice list handles its own keys before they reach the bridge

#### Scenario: Pointer activation follows the Enter path
- **WHEN** the player activates a rendered row with the pointer
- **THEN** the activation is admitted and traverses the identical focus, disabled-explanation, and submission-gating path as Enter, as specified by `webclient-pointer-activation`

#### Scenario: Repeat and in-flight submissions are suppressed
- **WHEN** Enter is held or repeated, or a mutation submission occurs while one is in flight or awaiting its declared presentation revision
- **THEN** the submission is suppressed, and no combination of key and pointer input emits more than one request per deliberate activation

#### Scenario: The exploration root carries the bare overview keys
- **WHEN** the shell is in exploration mode
- **THEN** the keyboard root is the exploration root frame, an empty menu: the room actions are the place card's 查看房間 and 休息 buttons and the 建議 pill (present whenever the committed `suggestions` envelope is not `unavailable`), each its own tab stop outside the router; exits are independent compass targets with no router key, and interact targets, look-only people, and objects are the presence rail's `target-<identity>`, `entity-<identity>`, and `object-<identity>` entries, also outside the router

#### Scenario: The exploration root omits the navigation-carried entries
- **WHEN** the exploration keyboard root renders
- **THEN** it carries no `party`, `character`, `quests`, or `inventory` entry - the top navigation bar's 隊伍 and 任務 entries are the sole keyboard-visible stops for the party window and the quest board

#### Scenario: The combat root declares a single column
- **WHEN** the shell is in combat mode
- **THEN** the root declares a single column, so its vertical arrow geometry matches its rendered list order and the horizontal arrow keys are no-ops

#### Scenario: The legacy B2 key contract survives only as a gate
- **WHEN** the exploration keyboard root replaced the legacy B2 flat `context_actions` affordance list, whose items were keyed `action-<action_id>` / `action-<surface>` (e.g. `action-guild`)
- **THEN** the B2 key-derivation contract is preserved only as the isolated Node gate (`web/webclient-app/tests/action/dock_items.test.js`), not as the live exploration focus frame
