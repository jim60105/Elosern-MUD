## ADDED Requirements

### Requirement: TileWall is a grouped roving-focus listbox

`TileWall` SHALL render its groups in order as one listbox with exactly one tab stop. Arrow keys, Home and End SHALL move focus in reading order across groups without changing the selection. Enter, Space and click SHALL emit `select` with the item id. An item marked not selectable SHALL stay focusable, carry `aria-disabled`, and never emit `select`.

#### Scenario: One tab stop
- **WHEN** a wall with two groups and five items renders
- **THEN** exactly one item has `tabindex="0"`, the selected one when present and otherwise the first

#### Scenario: Keys move focus, not selection
- **WHEN** focus is on the first item and the player presses ArrowRight, then End, then Home
- **THEN** focus moves to the second item, then the last, then the first, and no `select` is emitted

#### Scenario: Activation selects
- **WHEN** the player presses Enter or Space on a focused selectable item, or clicks it
- **THEN** `select` is emitted once with that item's id

#### Scenario: A non-selectable item never selects
- **WHEN** focus reaches an item marked not selectable and the player presses Enter or clicks it
- **THEN** the item is focused, carries `aria-disabled="true"`, and no `select` is emitted

### Requirement: DetailFooter renders descriptor buttons and a committed reason

`DetailFooter` SHALL render its buttons in order with an optional reason line. A disabled button SHALL stay focusable with `aria-disabled` and emit nothing, except a toggle button, which SHALL use native `disabled`. Pressing an enabled button SHALL emit `press` with its key. The quest detail SHALL render its footer through `DetailFooter` with unchanged testids and focus behavior.

#### Scenario: A disabled button emits nothing
- **WHEN** a disabled non-toggle button is clicked
- **THEN** it carries `aria-disabled="true"`, can take focus, and no `press` is emitted

#### Scenario: A toggle keeps native disabled
- **WHEN** a disabled toggle button (one with a pressed state) renders
- **THEN** it carries the native `disabled` attribute

#### Scenario: The quest footer is unchanged
- **WHEN** the quest detail renders an armed abandon, a track toggle, a turn-in and a disabled accept
- **THEN** every existing quest-drawer footer testid is present, cancel takes focus on arming, and each control emits exactly the descriptor action it emitted before the extraction
