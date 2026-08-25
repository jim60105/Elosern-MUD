## MODIFIED Requirements

### Requirement: Required desktop surfaces remain visible and usable
The narrative SHALL occupy the visual centre of the stage as a bounded caption whose complete log is
reachable in one action, with the brand, the top-meta pill, the HUD island stack, and the action dock
visible at 1440x900 and 1280x720. The action dock, the narrative caption, and the command line SHALL
NOT be permanently closable; every other surface MAY be opened on demand and closed. The foundation
SHALL target desktop only and SHALL NOT claim mobile acceptance. The shell SHALL show the game name as
its brand and SHALL show the current location, the world date/time, and the connection state in a
top-meta surface, with the connected state marked by an ok-green dot paired with a label — never a raw
mode label in place of location. The action dock SHALL render as the approved command surface: a
floating panel bounded to a maximum width and centred in the stage's dock anchor, whose root menu
frame renders as a tab bar of icon-and-label tabs with the open entry marked by a seal-red fill, and
whose remaining region renders the current frame's rows. The tab bar SHALL carry a guidance hint
naming the shortcuts (direction keys to choose, Enter to confirm, Escape to return, `/` to open the
command input). The focused row SHALL be marked by a seal-red fill plus a leading glyph, unfocused
rows bordered, and disabled rows dimmed but focusable for their explanation. Below the root frame the
dock SHALL render a breadcrumb naming the parent and current frames with a back control, and SHALL
render each frame's rows in the form that frame calls for — an exit outlet, navigation rows, a
target's affordance rows under its name, suggestion cards, or the combat forms — beside a detail pane
that names the focused item, its availability, and the next key action wherever the frame carries one.

#### Scenario: Standard desktop viewport contains every required surface
- **WHEN** the shell renders at 1440x900
- **THEN** the narrative caption, the brand, the top-meta surface, the HUD island stack, the action dock, and the command-drawer control are visible without overlapping the narrative input path

#### Scenario: Minimum desktop viewport remains usable
- **WHEN** the shell renders at 1280x720
- **THEN** every required surface remains reachable and the player can read narrative, open the complete log, inspect status, and open the command drawer

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

### Requirement: Keyboard routing is menu-first and submission-safe

After initial synchronization and after every completed or rejected action whose declared
presentation revision has been accepted, the action dock SHALL own focus. Key events SHALL
be dispatched through the public keyboard bridge (the `window.Elosern.KeyboardRouter` handle
contract), claimed exactly when the router consumed them, rather than bound directly to the
document. Arrow keys SHALL move within the active finite menu, Enter SHALL confirm an
enabled focused item, Escape SHALL pop exactly one menu level, Space SHALL be reserved for
multi-select toggles, and `/` SHALL toggle the command drawer: when the drawer is closed it
SHALL open and focus the input field, and when the drawer is already open with no editable
control focused it SHALL close and restore action-dock focus. A `/` pressed while an
editable control is focused SHALL be ordinary text input: it SHALL not close the drawer and
SHALL never be claimed by the router, so commands or text that contain a slash remain
typeable in the drawer field and in other editable controls (creation forms, rest forms).
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
- **THEN** the public keyboard bridge claims it (the router consumed the key or the open
  drawer owns it), the bridge reports no unclaimed keydown, and keys the router does not
  consume still reach the text and command-history path

#### Scenario: Slash toggles the drawer from the action dock
- **WHEN** the drawer is closed and the player presses `/` over the action dock
- **THEN** the drawer opens and the input field receives focus
- **WHEN** the drawer is open, no editable control is focused, and the player presses `/`
  again
- **THEN** the drawer closes and action-dock focus is restored

#### Scenario: A slash typed in an editable control is text
- **WHEN** an editable control (the drawer field, a creation form, or a rest form) is
  focused and the player presses `/`
- **THEN** the drawer stays open (if it was open) and a literal `/` is typed into that
  control, so text such as `whisper /ooc` remains fully typeable

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

