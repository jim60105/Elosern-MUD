## MODIFIED Requirements

### Requirement: Every action-dock surface renders exactly the keyboard router's current menu frame

Each dock that owns the action dock — exploration, character, creation, and combat — SHALL render its rows
from the keyboard router's current menu frame, so the rows on screen are exactly the items the router will
navigate, explain, and submit. The exploration compass is independent of router rows and submits committed
move rows through the same store gate. A dock SHALL re-render its rows whenever the router pushes, replaces,
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
- **WHEN** the exploration rest-duration form or the creation dock's field form is open
- **THEN** it captures its own input, the router's frame is unchanged beneath it, and closing it restores the rendered rows for that frame

#### Scenario: The overview beneath a popover is inert
- **WHEN** a person's verb card is open over the stage and the player presses the compass or an overview chip in the command panel beneath it
- **THEN** the command panel is `inert` while the card is open, so the press reaches no compass target or chip, no `ui_action` is emitted, the router's current frame is unchanged, and the card keeps focus until Escape or its `✕ 返回` row closes it

#### Scenario: Re-render is synchronous with the router event
- **WHEN** the router pushes, replaces, or pops a frame
- **THEN** the re-render is synchronous with the router event that caused it, so no interval exists in which the rendered rows describe a frame the router has already left

#### Scenario: One shared renderer defines every row
- **WHEN** rows are rendered in any dock
- **THEN** the row markup, the focused marker, the disabled marker and its `（無法使用）` suffix, the accessible disabled association, and the row identity attribute are defined in exactly one shared renderer

#### Scenario: The shared renderer adapts to the frame's shape
- **WHEN** a frame's shape calls for a tab, a scene-overview chip, a suggestion card, a skill row, a target token, a scale choice, or a confirmation row
- **THEN** the same shared renderer renders the row in that visual form, chosen from the frame's own shape, and is not duplicated per form

#### Scenario: The row model preserves menu semantics
- **WHEN** the shared-renderer row model is in place
- **THEN** no menu's items, labels, order, or semantics have changed

#### Scenario: Modal forms stay outside the row model
- **WHEN** the creation dock's text and numeric fields or the exploration dock's bounded rest-duration form is open — modal forms never pushed onto the router stack
- **THEN** each keeps its existing self-contained key capture, restores the router's frame rendering when it closes, and is an exception to the row model, not a violation of it

#### Scenario: The combat root frame renders as a vertical command list
- **WHEN** the combat dock renders its root frame
- **THEN** the root frame appears as a vertical command list in the rows region carrying the same items, order, keys and row identities, and no root row stays rendered, focusable, or submittable while a deeper frame is open

#### Scenario: Level indicators come only from the router's stack
- **WHEN** any visible level indicator, including a breadcrumb, is rendered
- **THEN** it is derived from the router's frame stack and its depth, and the dock renders no navigation affordance whose state is held outside that stack
