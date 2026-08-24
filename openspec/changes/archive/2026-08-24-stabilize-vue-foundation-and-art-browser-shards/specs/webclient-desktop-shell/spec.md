## MODIFIED Requirements

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
Interact / Character / Quests / Inventory / Wait), whose items carry the bare keys
`move`, `look`, `interact`, `character`, `quests`, `inventory`, `wait`, rendered as a
single-row grid. This root replaces the legacy B2 flat `context_actions` affordance list,
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

#### Scenario: Exploration root exposes the G2 hierarchical keys
- **WHEN** the client is in exploration mode and the player presses ArrowDown on the single-row
  exploration root (Move / Look / Interact / Character / Quests / Inventory / Wait)
- **THEN** the keyboard router's focus key is the bare G2 key (`move` at the first cell, a no-op
  on the single-row grid), not the legacy B2 `action-guild`-style `action-<id>`/`action-<surface>`
  key, and Enter on the focused root item pushes its client-local submenu (the dock depth becomes
  2) without dispatching a `ui_action`; focus then lands on the pushed submenu's first item (for an
  empty exploration panel, the disabled `move-empty` row), so `store.view.focus.key` is `move-empty`
  and `store.view.focus.enabled` is false
