## MODIFIED Requirements

### Requirement: Every action-dock surface renders exactly the keyboard router's current menu frame
Each dock that owns the action dock — exploration, character, creation, and combat — SHALL render its rows from the keyboard router's current menu frame, so the rows visible on screen are always exactly the items the router will navigate, explain, and submit. A dock SHALL re-render its rows whenever the router pushes, replaces, or pops a frame, and SHALL NOT leave a pushed frame without a rendered representation. That re-render SHALL be synchronous with the router event that caused it, so no interval exists in which the rendered rows describe a frame the router has already left. Rows SHALL be produced by one shared renderer so the row markup, the focused marker, the disabled marker and its `（無法使用）` suffix, the accessible disabled association, and the row identity attribute are defined in exactly one place; that renderer MAY render a row in different visual forms (a tab, an exit outlet cell, a navigation row, an affordance row, a suggestion card, a skill row, a target token, a scale choice, or a confirmation row) chosen from the frame's own shape, but SHALL NOT be duplicated per form. This SHALL NOT change any menu's items, labels, order, or semantics.

Two modal forms are explicitly outside this invariant because they are never pushed onto the router stack: the creation dock's text and numeric fields and the exploration dock's bounded rest-duration form. Each SHALL keep its existing self-contained key capture and SHALL restore the router's frame rendering when it closes. They are exceptions to the row model, not violations of it.

A dock MAY render its root frame as a persistent tab bar while a deeper frame owns the rows region. When it does, the tab bar SHALL be the root frame's own rendered rows — the same items, order, keys and row identities — and while a deeper frame is open the tab bar SHALL be inert ancestor chrome that marks which root entry is open and submits nothing on its own. The dock SHALL NOT render any navigation affordance whose state is held outside the router's frame stack: every visible level indicator, including a breadcrumb, SHALL be derived from that stack and its depth.

#### Scenario: Combat submenus become visible instead of blind
- **WHEN** the player opens Skills, a target list, a shorthand choice, or the Forfeit confirmation in combat mode
- **THEN** that frame's entries are rendered as rows in the action dock with the focused entry marked, instead of the root actions remaining on screen

#### Scenario: Popping a frame restores the parent's rows
- **WHEN** the player presses Escape from a submenu in any dock
- **THEN** exactly one level closes and the rendered rows return to the parent frame with the previously focused row marked

#### Scenario: The root frame's tab bar is the root frame's rows
- **WHEN** the dock is at its root frame and its root renders as a tab bar
- **THEN** the tabs are exactly the root frame's items in the router's order with their row identities, and opening one pushes that item's frame through the ordinary confirmation path

#### Scenario: Level indicators are derived, never held separately
- **WHEN** the router pops or replaces a frame for any reason, including a panel replacement
- **THEN** the tab bar's open marking and the breadcrumb both re-derive from the router's frame stack in the same render, and no client-held pane or crumb state survives to contradict Escape

#### Scenario: Display-only rows stay display-only
- **WHEN** the character panel's read-only rows are rendered
- **THEN** they are focusable and update the detail pane, and no row submits an action

#### Scenario: A modal form is not required to become rows
- **WHEN** the exploration rest-duration form or the creation dock's field form is open
- **THEN** it captures its own input, the router's frame is unchanged beneath it, and closing it restores the rendered rows for that frame

### Requirement: Keyboard input is dispatched through the WebClient plugin contract
Key input SHALL be dispatched through the KeyboardRouter handle path exposed by the
public keyboard bridge (the `window.Elosern.KeyboardRouter` claim contract), claimed
exactly when the router consumed the event or when the focused command field owns the
key; unconsumed keys SHALL fall through to the text and command-history path, so
history recall keeps its turn. Because the command field is permanently present rather
than opened, field ownership SHALL be determined by whether the field holds focus, not
by an open state. A modal capture that must pre-empt the keyboard
bridge — the exploration dock's bounded rest-duration entry or the creation dock's
text/numeric field — MAY use a
capture-phase listener and SHALL remove it when its form closes. A focus-trapped
surface laid over the stage — a reference drawer or a full-screen overlay — SHALL own
every key it receives while it holds trapped focus, and SHALL release that ownership
when it closes and returns focus to the control that opened it.

#### Scenario: No unclaimed-keydown noise remains
- **WHEN** the player navigates the action dock and types in the command field
- **THEN** the bridge claims exactly the events its router consumed and the keys its
  focused command field owns, so no unclaimed-keydown noise remains

#### Scenario: Unclaimed keys still reach the text and history path
- **WHEN** the player uses the stock command-history recall keys in the command field
- **THEN** the bridge does not claim them and history recall works

#### Scenario: A trapped surface owns its keys while it is open
- **WHEN** a full-screen overlay holds trapped focus and the player presses a navigation key
- **THEN** the overlay owns the key, the router consumes nothing behind it, and closing the
  overlay returns focus to its trigger and restores the router's ownership

### Requirement: Pointer parity is verified in the browser without weakening keyboard-only acceptance
The managed localhost Playwright suite SHALL exercise, with the pointer only at both supported desktop viewports: an exploration root entry and one submenu submission, a service action submitted from its reference drawer's own control, a combat root action and one combat submenu selection, a disabled row that explains without submitting, and an activation attempt while the offline overlay is shown. Each SHALL assert the exact emitted `ui_action` count and payload. The keyboard-only acceptance requirements SHALL NOT be weakened to accommodate pointer parity and SHALL continue to pass, so keyboard-only play is still a verified guarantee rather than a side effect.

#### Scenario: A pointer-only journey completes in Chromium
- **WHEN** a seeded actor uses only the mouse to open an exploration submenu and submit an action
- **THEN** each step emits exactly one expected `ui_action` and the panels refresh, with no key press required

#### Scenario: Keyboard-only journeys still pass unchanged
- **WHEN** the existing keyboard-only exploration, service, creation, and combat journeys run
- **THEN** they pass with the keyboard steps and assertions their own acceptance requirements define, none of which is relaxed for pointer parity

#### Scenario: Offline pointer activation emits nothing
- **WHEN** the WebSocket is interrupted and the player clicks an enabled row under the offline overlay
- **THEN** no `ui_action` crosses the wire and the overlay remains until a valid new-epoch snapshot is adopted
