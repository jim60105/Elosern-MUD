## MODIFIED Requirements

### Requirement: Every action-dock surface renders exactly the keyboard router's current menu frame

Each dock that owns the action dock — exploration, character, creation, and combat — SHALL render its rows
from the keyboard router's current menu frame, so the rows on screen are exactly the items the router will
navigate, explain, and submit. The exploration compass is independent of router rows and submits committed
move rows through the same store gate; the exploration root's router menu is empty, and the place card's
room actions and the 建議 pill submit or open through the same gate outside it. A dock SHALL re-render its rows whenever the router pushes, replaces,
or pops a frame.

#### Scenario: Combat submenus become visible instead of blind
- **WHEN** the player opens Skills, a target list, a shorthand choice, or the Forfeit confirmation in combat mode
- **THEN** that frame's entries are rendered as rows in the action dock with the focused entry marked, instead of the root actions remaining on screen

#### Scenario: Popping a frame restores the parent's rows
- **WHEN** the player presses Escape from a submenu in any dock
- **THEN** exactly one level closes and the rendered rows return to the parent frame with the previously focused row marked

#### Scenario: The combat root list is the root frame's rows
- **WHEN** the combat dock is at its root frame
- **THEN** the list rows are exactly the root frame's items in the router's order with their row identities, and opening one pushes that item's frame through the ordinary confirmation path, which replaces the list with the pushed frame's rows

#### Scenario: Level indicators are derived, never held separately
- **WHEN** the router pops or replaces a frame for any reason, including a panel replacement
- **THEN** the rendered rows and the breadcrumb both re-derive from the router's frame stack in the same render, and no client-held pane or crumb state survives to contradict Escape

#### Scenario: Display-only rows stay display-only
- **WHEN** the character panel's read-only rows are rendered
- **THEN** they are focusable and update the detail pane, and no row submits an action

#### Scenario: A modal form is not required to become rows
- **WHEN** the wait card's rest-duration form or the creation dock's field form is open
- **THEN** it captures its own input, the router's frame is unchanged beneath it, and closing it restores what that surface showed before it opened

#### Scenario: The overview beneath a popover is inert
- **WHEN** a person's verb card is open over the stage and the player presses the compass or the 建議 pill in the command panel beneath it
- **THEN** the command panel is `inert` while the card is open, so the press reaches no compass target or pill, no `ui_action` is emitted, the router's current frame is unchanged, and the card keeps focus until Escape or its `✕ 返回` row closes it

#### Scenario: Re-render is synchronous with the router event
- **WHEN** the router pushes, replaces, or pops a frame
- **THEN** the re-render is synchronous with the router event that caused it, so no interval exists in which the rendered rows describe a frame the router has already left

#### Scenario: One shared renderer defines every row
- **WHEN** rows are rendered in any dock
- **THEN** the row markup, the focused marker, the disabled marker and its `（無法使用）` suffix, the accessible disabled association, and the row identity attribute are defined in exactly one shared renderer

#### Scenario: The shared renderer adapts to the frame's shape
- **WHEN** a frame's shape calls for a tab, a skill row, a target token, a scale choice, or a confirmation row
- **THEN** the same shared renderer renders the row in that visual form, chosen from the frame's own shape, and is not duplicated per form

#### Scenario: The row model preserves menu semantics
- **WHEN** the shared-renderer row model is in place
- **THEN** no menu's items, labels, order, or semantics have changed

#### Scenario: Modal forms stay outside the row model
- **WHEN** the creation dock's text and numeric fields or the wait card's bounded rest-duration form is open — modal forms never pushed onto the router stack
- **THEN** each keeps its existing self-contained key capture, restores the router's frame rendering when it closes, and is an exception to the row model, not a violation of it

#### Scenario: The combat root frame renders as a vertical command list
- **WHEN** the combat dock renders its root frame
- **THEN** the root frame appears as a vertical command list in the rows region carrying the same items, order, keys and row identities, and no root row stays rendered, focusable, or submittable while a deeper frame is open

#### Scenario: Level indicators come only from the router's stack
- **WHEN** any visible level indicator, including a breadcrumb, is rendered
- **THEN** it is derived from the router's frame stack and its depth, and the dock renders no navigation affordance whose state is held outside that stack

### Requirement: The action dock is a single composite widget that cannot double-activate

The rendered rows SHALL form one composite widget: the row container SHALL carry the listbox role, be the row
region's single tab stop, and name the focused row through an active-descendant association, with each row
carrying the option role and its selected state. The exploration compass SHALL be a separate single tab stop
with `role="application"`; no exit is a router row. A pointer press on a row SHALL NOT move DOM focus off
that container.

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

#### Scenario: Exactly one container holds the listbox role
- **WHEN** the dock is at the root frame, where the root frame renders as a tab bar, and at any deeper frame
- **THEN** exactly one row container holds the role — the tab bar's container at the root frame and the rows region's container at every deeper frame — and the other is neither a tab stop nor a listbox

#### Scenario: The action-dock element forwards focus
- **WHEN** an active row container is mounted
- **THEN** the action-dock element remains the surface's documented focus target and forwards exploration-root focus to the compass and other frame focus to the active row container, so existing focus-restoration callers need no change

#### Scenario: Only live primary pointer activations are admitted
- **WHEN** a pointer activation arrives
- **THEN** it is admitted only when it is a primary single activation and its resolved row is still part of the rendered document; a keyboard-synthesized activation, the repeated events of a multi-click, and an activation whose row belongs to a frame that has already been replaced are all ignored

#### Scenario: Ancestor-tab activation goes through the router
- **WHEN** a deeper frame is open and a pointer activates an inert ancestor tab
- **THEN** it is admitted only as router operations — closing frames one level at a time until the root frame is current, moving focus to that tab's row, then performing the ordinary confirmation — bounded by the router's own depth, never swapping the rendered rows directly, and activating the tab of the already-open root entry does nothing

#### Scenario: One deliberate activation yields one effect
- **WHEN** the keyboard confirms a focused row, or key and pointer inputs combine on rows
- **THEN** keyboard confirmation emits exactly one action, no combination of key and pointer input on the same row emits more than one action per deliberate activation, and no sequence of pointer activations pushes a menu frame more than once per deliberate activation

#### Scenario: Navigation rows obey the single-activation guarantee
- **WHEN** a navigation row — which opens a submenu rather than submitting and is therefore not covered by the in-flight mutation lock — is activated
- **THEN** the one-action-per-deliberate-activation guarantee still holds
