## MODIFIED Requirements

### Requirement: Every action-dock surface renders exactly the keyboard router's current menu frame
Each dock that owns the action dock — exploration, services, character, creation, and combat — SHALL render its rows from the keyboard router's current menu frame, so the rows visible on screen are always exactly the items the router will navigate, explain, and submit. A dock SHALL re-render its rows whenever the router pushes, replaces, or pops a frame, and SHALL NOT leave a pushed frame without a rendered representation. That re-render SHALL be synchronous with the router event that caused it, so no interval exists in which the rendered rows describe a frame the router has already left. Rows SHALL be produced by one shared renderer so the row markup, the focused marker, the disabled marker and its `（無法使用）` suffix, the accessible disabled association, and the row identity attribute are defined in exactly one place; that renderer MAY render a row in different visual forms (a tab, an exit outlet cell, a navigation row, an affordance row, a suggestion card, a skill row, a target token, a scale choice, or a confirmation row) chosen from the frame's own shape, but SHALL NOT be duplicated per form. This SHALL NOT change any menu's items, labels, order, or semantics.

A dock MAY render its root frame as a persistent tab bar while a deeper frame owns the rows region. When it does, the tab bar SHALL be the root frame's own rendered rows — the same items, order, keys and row identities — and while a deeper frame is open the tab bar SHALL be inert ancestor chrome that marks which root entry is open and submits nothing on its own. The dock SHALL NOT render any navigation affordance whose state is held outside the router's frame stack: every visible level indicator, including a breadcrumb, SHALL be derived from that stack and its depth.

Three modal forms are explicitly outside this invariant because they are never pushed onto the router stack: the creation dock's text and numeric fields, the services dock's bounded quantity form, and the exploration dock's bounded rest-duration form. Each SHALL keep its existing self-contained key capture and SHALL restore the router's frame rendering when it closes. They are exceptions to the row model, not violations of it.

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
- **WHEN** the services quantity form, the exploration rest-duration form, or the creation dock's field form is open
- **THEN** it captures its own input, the router's frame is unchanged beneath it, and closing it restores the rendered rows for that frame

### Requirement: The action dock is a single composite widget that cannot double-activate
The rendered rows SHALL form one composite widget: the row container SHALL carry the listbox role, be the surface's single tab stop, and name the focused row through an active-descendant association, and each row SHALL carry the option role with its selected state. Exactly one row container SHALL hold that role at any moment — when the root frame renders as a tab bar it is the tab bar's container at the root frame and the rows region's container at every deeper frame, and the other SHALL be neither a tab stop nor a listbox. Rows SHALL NOT be individually reachable by sequential keyboard navigation. The action-dock element SHALL remain the surface's documented focus target and SHALL forward focus to the active row container when one is mounted, so existing focus-restoration callers need no change. Pressing the pointer on a row SHALL NOT move DOM focus off that container.

A pointer activation SHALL be admitted only when it is a primary single activation and its resolved row is still part of the rendered document: a keyboard-synthesized activation, the repeated events of a multi-click, and an activation whose row belongs to a frame that has already been replaced SHALL all be ignored. A pointer activation of an inert ancestor tab while a deeper frame is open SHALL be admitted only as router operations — closing frames one level at a time until the root frame is current, moving focus to that tab's row, and then performing the ordinary confirmation — bounded by the router's own depth, and SHALL NOT swap the rendered rows directly; activating the tab of the already-open root entry SHALL do nothing. Consequently, confirming a focused row from the keyboard SHALL emit exactly one action, no combination of key and pointer input on the same row SHALL emit more than one action per deliberate activation, and no sequence of pointer activations SHALL push a menu frame more than once per deliberate activation. This SHALL hold for navigation rows, which open a submenu rather than submitting and are therefore not covered by the in-flight mutation lock.

#### Scenario: Enter on a focused row emits one action, not two
- **WHEN** the player moves focus to an enabled row with the arrow keys and presses Enter
- **THEN** exactly one `ui_action` is emitted, with no additional activation from a synthesized click

#### Scenario: A double-click does not activate a replaced row
- **WHEN** the player double-clicks a row that opens a submenu
- **THEN** the submenu opens once and the second click does not activate whichever row now occupies that position

#### Scenario: A stale row cannot push a second frame
- **WHEN** a pointer activation resolves to a row that the previous activation's re-render already removed from the document
- **THEN** the activation is ignored, no additional menu frame is pushed, and one Escape still returns to the parent frame

#### Scenario: Clicking another tab returns through the router
- **WHEN** a deeper frame is open and the player clicks the tab of a different root entry
- **THEN** the router closes the open frames one level at a time back to the root, focuses that tab's row, and opens its frame with exactly one deliberate activation, emitting no unexpected `ui_action`

#### Scenario: Only one container is the listbox at a time
- **WHEN** the dock is inspected at the root frame and again at a deeper frame
- **THEN** exactly one row container carries the listbox role, the tab stop and the active-descendant reference in each case, and the other container is neither focusable by Tab nor exposed as a listbox

#### Scenario: Focus indication stays with the router
- **WHEN** the player clicks a row
- **THEN** the row container retains DOM focus, the active-descendant association names the clicked row, and the visible focus indicator is on that row

#### Scenario: Composite roles are present and machine-checkable
- **WHEN** the rendered action dock is inspected in the browser
- **THEN** the row container exposes the listbox role with a tab stop and an active-descendant reference, each row exposes the option role with its selected and disabled state, and no row is reachable by sequential keyboard navigation

