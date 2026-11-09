## REMOVED Requirements

### Requirement: The codex drawer renders the panel in two navigation levels

**Reason**: The world-codex drawer (`LoreCodexDrawer.vue`) is replaced by the handbook's codex tab (design D1, D3). Its navigation is covered by "The handbook codex tab renders the committed panel as a grouped tile wall".

**Migration**: None (pre-release). The `lore` drawer name is retired, and the 圖鑑 tool opens the handbook codex tab.

### Requirement: The codex drawer discloses no more than the panel does

**Reason**: Design D4 now discloses counts and ordinal placeholders. The codex tab's disclosure is covered by the tile-wall and degradation requirements below, which render exactly what the v2 panel ships.

**Migration**: None.

### Requirement: The codex opens from the top navigation bar, not from the quest drawer

**Reason**: Design D1 and D2 put the codex inside the quest drawer (the handbook). The 圖鑑 tool opens that tab through the handbook route request (see `webclient-desktop-shell`).

**Migration**: None.

## ADDED Requirements

### Requirement: The handbook codex tab renders the committed panel as a grouped tile wall

The codex tab SHALL render only the committed `lore_codex` panel. Its rail SHALL carry one entry per shipped category, in panel order, with the category's `discovered` count. The wall SHALL render the selected category's groups in order, with a group heading for each non-null label, and one tile per slot in slot order. Navigation SHALL be local and dispatch nothing.

#### Scenario: Selecting a category shows its wall
- **WHEN** the player selects a rail entry
- **THEN** the wall shows exactly that category's slots grouped as shipped, and no request is dispatched

#### Scenario: Placeholders are focusable but not selectable
- **WHEN** focus reaches a placeholder tile and the player presses Enter or clicks it
- **THEN** the tile carries an accessible name that names no entry and `aria-disabled`, and the selection does not change

#### Scenario: Tiles walk by keyboard
- **WHEN** focus is on a tile and the player presses an arrow key, Home or End, then Enter on an entry tile
- **THEN** focus moves in reading order across groups without changing the selection, and Enter selects the focused entry

#### Scenario: The detail renders the card verbatim
- **WHEN** an entry tile is selected
- **THEN** the detail shows the slot's title and every card field other than the title field, in panel order, each value verbatim under a readable field name, and no raw field identifier is visible

#### Scenario: The selection is remembered per category
- **WHEN** the player selects an entry, switches category, and returns
- **THEN** the same entry is selected again within the same memory scope

#### Scenario: A codex route request opens the codex tab
- **WHEN** the handbook route entry is called with the codex tab, in exploration and in combat
- **THEN** the quest drawer opens with the codex tab selected

### Requirement: Monster research stages differ by shape and are explained

A monster entry tile SHALL mark its stage by a shape that differs between `defeated` and `sighted`, and a placeholder SHALL use a third mark. The monster wall SHALL carry a legend naming all three marks. The legend SHALL stay visible at the bottom edge of the wall while the tiles scroll. The monster detail SHALL show a two-step research track whose steps reflect the stage.

#### Scenario: Stage marks differ by shape
- **WHEN** the monster wall shows a defeated tile, a sighted tile and a placeholder
- **THEN** each carries a distinct stage-mark element (`data-stage` `defeated`, `sighted`, or `unknown`) whose shape differs, not only its colour

#### Scenario: The legend stays pinned
- **WHEN** the monster wall's tiles overflow and the wall is scrolled to its top and then to its bottom
- **THEN** the legend's box lies inside the wall's visible box at both positions

#### Scenario: The research track follows the stage
- **WHEN** a sighted and then a defeated monster entry is selected
- **THEN** the track marks only its first step reached for the sighted entry, and both steps for the defeated entry; for the sighted entry the second step names exactly the readable names of its `locked_fields`

### Requirement: A sighted monster shows its locked fields without values

For each name in a selected entry's `locked_fields`, the detail SHALL render one locked box labelled with that field's readable name. A locked box SHALL show no value. A defeated entry SHALL render no locked box.

#### Scenario: Locked fields render as locked boxes
- **WHEN** a sighted entry whose `locked_fields` names four fields is selected
- **THEN** the detail renders four locked boxes in `locked_fields` order and no value for those fields

#### Scenario: A defeated entry has no locked box
- **WHEN** a defeated entry is selected
- **THEN** no locked box renders

### Requirement: Codex hero art falls back to the category emblem

The detail hero SHALL render the selected entry's `art` descriptor through the shared artwork attempt lifecycle. When `art` is null, when no attempt or terminal of the descriptor has loaded, or when every permitted source failed, the hero SHALL render the category emblem instead. The hero SHALL never show an empty frame.

#### Scenario: A null art shows the emblem
- **WHEN** an entry whose `art` is null is selected
- **THEN** the hero shows that category's emblem

#### Scenario: A failed image falls back to the emblem
- **WHEN** an entry's art descriptor has one attempt whose image fails to load and no terminal
- **THEN** after the failure the hero shows the category emblem and no image frame

#### Scenario: A loaded image replaces the emblem
- **WHEN** an entry's art descriptor attempt loads successfully
- **THEN** the hero shows that image

### Requirement: The handbook codex tab degrades honestly

Before the first `lore_codex` commit the codex tab SHALL be enabled and show the shared empty state. While the panel is unavailable the tab SHALL be disabled, yet focusable, with the panel's reason. A codex with nothing discovered SHALL render its full placeholder wall and the empty detail guidance. A selection gone after a commit SHALL move to the category's first entry, else to the empty detail.

#### Scenario: Before the first commit
- **WHEN** the codex tab is selected before any `lore_codex` panel was committed
- **THEN** it shows the shared empty state and no tile

#### Scenario: An unavailable panel disables the tab
- **WHEN** the committed `lore_codex` panel is the common unavailable form
- **THEN** the codex tab is disabled, keyboard focus can reach it, and its tooltip and accessible description carry the panel's reason message

#### Scenario: Nothing discovered shows the placeholder wall
- **WHEN** the committed panel holds only placeholders
- **THEN** the wall renders every placeholder and the detail renders the shared empty guidance

#### Scenario: A vanished selection falls back
- **WHEN** the selected entry is gone after a commit
- **THEN** the category's first entry is selected, or the empty detail shows when it has none

### Requirement: The handbook codex tab fits the reference viewports

On the live client at 1451x790 and at 2560x1440 the codex tab SHALL lay out its rail, wall and detail columns side by side inside the drawer body. The wall SHALL NOT scroll horizontally. No rendered text SHALL be smaller than the `--text-xs` token's computed size. Each legend mark SHALL have a fixed size that does not depend on the wall width.

#### Scenario: Three columns fit at both viewports
- **WHEN** the live client opens the monster category of the codex tab at 1451x790 and at 2560x1440
- **THEN** the rail, wall and detail columns do not overlap, each lies inside the drawer body, and the wall has no horizontal scroll overflow

#### Scenario: No text below the floor
- **WHEN** the codex tab renders at either viewport
- **THEN** every visible text node's computed font size is at least the computed size of `--text-xs`

#### Scenario: Legend marks keep their size
- **WHEN** the monster legend renders at both viewports
- **THEN** each legend mark's rendered width equals `12px` times the page's `--ui-scale` within 1px
