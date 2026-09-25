## MODIFIED Requirements

### Requirement: Every action-dock surface renders exactly the keyboard router's current menu frame
Each dock that owns the action dock — exploration, character, creation, and combat — SHALL render its rows from the keyboard router's current menu frame, so the rows visible on screen are always exactly the items the router will navigate, explain, and submit. A dock SHALL re-render its rows whenever the router pushes, replaces, or pops a frame, and SHALL NOT leave a pushed frame without a rendered representation. That re-render SHALL be synchronous with the router event that caused it, so no interval exists in which the rendered rows describe a frame the router has already left. Rows SHALL be produced by one shared renderer so the row markup, the focused marker, the disabled marker and its `（無法使用）` suffix, the accessible disabled association, and the row identity attribute are defined in exactly one place; that renderer MAY render a row in different visual forms (a tab, a scene-overview chip, a verb-popover row, an exit outlet cell, a navigation row, an affordance row, a suggestion card, a skill row, a target token, a scale choice, or a confirmation row) chosen from the frame's own shape, but SHALL NOT be duplicated per form. This SHALL NOT change any menu's items, labels, order, or semantics.

Two modal forms are explicitly outside this invariant because they are never pushed onto the router stack: the creation dock's text and numeric fields and the exploration dock's bounded rest-duration form. Each SHALL keep its existing self-contained key capture and SHALL restore the router's frame rendering when it closes. They are exceptions to the row model, not violations of it.

A dock MAY render its root frame as a persistent tab bar while a deeper frame owns the rows region (the combat dock does). When it does, the tab bar SHALL be the root frame's own rendered rows — the same items, order, keys and row identities — and while a deeper frame is open the tab bar SHALL be inert ancestor chrome that marks which root entry is open and submits nothing on its own. While a target's verb popover is the current frame, the exploration dock SHALL keep the scene overview (the root frame's own rendered chips) visible beneath the popover as inert ancestor chrome: it SHALL be hidden from assistive technology, SHALL take no focus, and SHALL submit nothing, and a pointer press on it SHALL close the popover exactly as the back row does. The dock SHALL NOT render any navigation affordance whose state is held outside the router's frame stack: every visible level indicator, including a breadcrumb, SHALL be derived from that stack and its depth.

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

#### Scenario: The overview beneath a popover is inert
- **WHEN** a target's verb popover is open and the player clicks an exit chip of the overview visible beneath it
- **THEN** the popover closes exactly as its back row would, no `ui_action` is emitted, and the overview becomes the current frame with the target's chip focused
