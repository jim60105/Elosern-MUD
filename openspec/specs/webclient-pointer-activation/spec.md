## Purpose

The dock-wide contract that every action-dock surface renders exactly the keyboard router's current menu frame, that pointer activation traverses the identical focus, disabled-explanation, and submission-gating path as the keyboard, the composite-widget focus model, the single delegated listener on the action dock, the plugin-contract keydown routing, and the pointer browser-acceptance journeys.

## Requirements


### Requirement: Every action-dock surface renders exactly the keyboard router's current menu frame
Each dock that owns the action dock — exploration, services, character, creation, and combat — SHALL render its rows from the keyboard router's current menu frame, so the rows visible on screen are always exactly the items the router will navigate, explain, and submit. A dock SHALL re-render its rows whenever the router pushes, replaces, or pops a frame, and SHALL NOT leave a pushed frame without a rendered representation. That re-render SHALL be synchronous with the router event that caused it, so no interval exists in which the rendered rows describe a frame the router has already left. Rows SHALL be produced by one shared renderer so the row markup, the focused marker, the disabled marker and its `（無法使用）` suffix, the accessible disabled association, and the row identity attribute are defined in exactly one place. This SHALL NOT change any menu's items, labels, order, or semantics.

Three modal forms are explicitly outside this invariant because they are never pushed onto the router stack: the creation dock's text and numeric fields, the services dock's bounded quantity form, and the exploration dock's bounded rest-duration form. Each SHALL keep its existing self-contained key capture and SHALL restore the router's frame rendering when it closes. They are exceptions to the row model, not violations of it.

#### Scenario: Combat submenus become visible instead of blind
- **WHEN** the player opens Skills, a target list, a shorthand choice, or the Forfeit confirmation in combat mode
- **THEN** that frame's entries are rendered as rows in the action dock with the focused entry marked, instead of the root actions remaining on screen

#### Scenario: Popping a frame restores the parent's rows
- **WHEN** the player presses Escape from a submenu in any dock
- **THEN** exactly one level closes and the rendered rows return to the parent frame with the previously focused row marked

#### Scenario: Display-only rows stay display-only
- **WHEN** the character panel's read-only rows are rendered
- **THEN** they are focusable and update the detail pane, and no row submits an action

#### Scenario: A modal form is not required to become rows
- **WHEN** the services quantity form, the exploration rest-duration form, or the creation dock's field form is open
- **THEN** it captures its own input, the router's frame is unchanged beneath it, and closing it restores the rendered rows for that frame

### Requirement: Pointer activation traverses the identical path as keyboard confirmation
Activating an action-dock row with the pointer SHALL move the router's focus to that row and then perform the same confirmation the keyboard performs, so both input methods share one gate. A pointer activation on a disabled row SHALL surface that row's explanation and SHALL NOT submit. A pointer activation while a mutation is in flight or while the client is awaiting a declared presentation revision SHALL be suppressed exactly as the keyboard is suppressed. A pointer activation on an enabled row SHALL emit exactly one `ui_action` message, with the same action ID and payload the keyboard would emit. Pointer activation SHALL NOT consult or set the held-Enter repeat guard, because that guard exists to suppress key repeat and would otherwise reject a legitimate second click on the same row. Pointer activation SHALL be delivered by exactly one delegated listener installed on the stable action-dock element, so it survives every dock re-render without per-row binding.

#### Scenario: Clicking a row submits exactly what Enter submits
- **WHEN** the player clicks an enabled exploration, service, creation, or combat row
- **THEN** the browser emits exactly one `ui_action` with the same action ID and payload that confirming the same row with Enter emits

#### Scenario: Clicking a disabled row explains without submitting
- **WHEN** the player clicks a row rendered as disabled
- **THEN** the row's disabled reason becomes readable in the detail pane and no `ui_action` message is emitted

#### Scenario: Clicking while locked emits nothing
- **WHEN** the player clicks an enabled mutating row while a mutation is in flight, while the client awaits a declared presentation revision, or while the offline overlay is shown
- **THEN** no message is emitted and the lock remains in effect

#### Scenario: One delegated listener survives dock re-renders
- **WHEN** a dock replaces its entire rendered subtree after a snapshot, a mode change, or a menu transition
- **THEN** clicking a newly rendered row still activates it, and no per-row listener is registered or leaked

### Requirement: The action dock is a single composite widget that cannot double-activate
The rendered rows SHALL form one composite widget: the row container SHALL carry the listbox role, be the surface's single tab stop, and name the focused row through an active-descendant association, and each row SHALL carry the option role with its selected state. Rows SHALL NOT be individually reachable by sequential keyboard navigation. The action-dock element SHALL remain the surface's documented focus target and SHALL forward focus to the active row container when one is mounted, so existing focus-restoration callers need no change. Pressing the pointer on a row SHALL NOT move DOM focus off that container.

A pointer activation SHALL be admitted only when it is a primary single activation and its resolved row is still part of the rendered document: a keyboard-synthesized activation, the repeated events of a multi-click, and an activation whose row belongs to a frame that has already been replaced SHALL all be ignored. Consequently, confirming a focused row from the keyboard SHALL emit exactly one action, no combination of key and pointer input on the same row SHALL emit more than one action per deliberate activation, and no sequence of pointer activations SHALL push a menu frame more than once per deliberate activation. This SHALL hold for navigation rows, which open a submenu rather than submitting and are therefore not covered by the in-flight mutation lock.

#### Scenario: Enter on a focused row emits one action, not two
- **WHEN** the player moves focus to an enabled row with the arrow keys and presses Enter
- **THEN** exactly one `ui_action` is emitted, with no additional activation from a synthesized click

#### Scenario: A double-click does not activate a replaced row
- **WHEN** the player double-clicks a row that opens a submenu
- **THEN** the submenu opens once and the second click does not activate whichever row now occupies that position

#### Scenario: A stale row cannot push a second frame
- **WHEN** a pointer activation resolves to a row that the previous activation's re-render already removed from the document
- **THEN** the activation is ignored, no additional menu frame is pushed, and one Escape still returns to the parent frame

#### Scenario: Focus indication stays with the router
- **WHEN** the player clicks a row
- **THEN** the row container retains DOM focus, the active-descendant association names the clicked row, and the visible focus indicator is on that row

#### Scenario: Composite roles are present and machine-checkable
- **WHEN** the rendered action dock is inspected in the browser
- **THEN** the row container exposes the listbox role with a tab stop and an active-descendant reference, each row exposes the option role with its selected and disabled state, and no row is reachable by sequential keyboard navigation

### Requirement: Keyboard input is dispatched through the WebClient plugin contract
Key input SHALL be dispatched through the KeyboardRouter handle path exposed by the
public keyboard bridge (the `window.Elosern.KeyboardRouter` claim contract), claimed
exactly when the router consumed the event or when the open command drawer owns the
key; unconsumed keys SHALL fall through to the text and command-history path, so
history recall keeps its turn. A modal capture that must pre-empt the keyboard
bridge — the exploration dock's bounded rest-duration entry, the services dock's
bounded quantity form, or the creation dock's text/numeric field — MAY use a
capture-phase listener and SHALL remove it when its form closes.

#### Scenario: No unclaimed-keydown noise remains
- **WHEN** the player navigates the action dock and types in the command drawer
- **THEN** the bridge claims exactly the events its router consumed and the keys its
  open drawer owns, so no unclaimed keydown noise remains

#### Scenario: Unclaimed keys still reach the text and history path
- **WHEN** the player uses the stock command-history recall keys in the command drawer
- **THEN** the bridge does not claim them and history recall works

### Requirement: Pointer parity is verified in the browser without weakening keyboard-only acceptance
The managed localhost Playwright suite SHALL exercise, with the pointer only at both supported desktop viewports: an exploration root entry and one submenu submission, a service submenu submission, a combat root action and one combat submenu selection, a disabled row that explains without submitting, and an activation attempt while the offline overlay is shown. Each SHALL assert the exact emitted `ui_action` count and payload. The existing keyboard-only acceptance requirements SHALL remain unchanged and SHALL continue to pass, so keyboard-only play is still a verified guarantee rather than a side effect.

#### Scenario: A pointer-only journey completes in Chromium
- **WHEN** a seeded actor uses only the mouse to open an exploration submenu and submit an action
- **THEN** each step emits exactly one expected `ui_action` and the panels refresh, with no key press required

#### Scenario: Keyboard-only journeys still pass unchanged
- **WHEN** the existing keyboard-only exploration, service, creation, and combat journeys run
- **THEN** they pass without modification to their keyboard steps or assertions

#### Scenario: Offline pointer activation emits nothing
- **WHEN** the WebSocket is interrupted and the player clicks an enabled row under the offline overlay
- **THEN** no `ui_action` crosses the wire and the overlay remains until a valid new-epoch snapshot is adopted
