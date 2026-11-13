## Purpose

Render the gallery window's wall: the selected category's subjects as
aspect-true tiles in committed groups, with an inline tray for the selected
subject's images and a keyboard contract of two roving listboxes.

## ADDED Requirements

### Requirement: The wall renders committed groups as aspect-true subject tiles
The wall SHALL render the committed groups in order, drawing a heading only for a group with a label (with `seen / total` when both are present, and the count of a collapsed group), and one tile per committed subject showing its display name, its committed artwork, its image count when the count is above one, and a 操作中 marker on the subject marked current. Scene subjects SHALL use landscape tiles and every other kind portrait tiles.

#### Scenario: An unlabeled group starts with tiles
- **WHEN** the committed groups hold one group with a null label and three subjects
- **THEN** the wall renders three tiles and no heading

#### Scenario: A tier heading carries its counts
- **WHEN** a group has label `t_low`, seen 1 and total 2
- **THEN** its heading shows the label and `1 / 2`

#### Scenario: A collapsed group shows only its heading and count
- **WHEN** a group has `expanded: false`, label `t_place` and count 7
- **THEN** the wall renders its heading with `t_place` and 7 and no tiles for it

#### Scenario: The live character is marked by text
- **WHEN** a subject has `is_current: true`
- **THEN** its tile shows the text 操作中 and its accessible name includes 操作中

### Requirement: A multi-card subject opens a tray under its row
When the selected subject's committed capabilities allow more than one card, the wall SHALL render one tray directly after the last tile of the selected subject's row, spanning the row, listing the subject's committed card rows as tiles in payload order, then a 生成新圖 tile, then a 官方圖片（唯讀） run of its official entries. A one-card subject SHALL open no tray. Opening a tray SHALL scroll it into view.

#### Scenario: The tray follows the owner's row
- **WHEN** a four-column wall's selected subject is the second tile and the subject allows several cards
- **THEN** the tray element follows the fourth tile and the owner tile carries `aria-expanded="true"`

#### Scenario: A one-card subject opens no tray
- **WHEN** the selected subject's capabilities declare `max_cards: 1`
- **THEN** no tray renders and the owner tile carries no `aria-expanded`

#### Scenario: Official entries follow the generate tile
- **WHEN** the selected subject has two card rows and one official entry
- **THEN** the tray lists the two cards, then 生成新圖, then a run labelled 官方圖片（唯讀） with one tile

### Requirement: Tray tiles carry state by shape and text
Tray tiles SHALL mark the default card with a crown and the text 預設, a pending row with a spinner and 生成中, a failed row with a warning triangle and 生成失敗, and official entries with a double border; no state SHALL be carried by colour alone.

#### Scenario: Each state has its text
- **WHEN** the tray lists a default card, a pending row and a failed row
- **THEN** their tiles show 預設, 生成中 and 生成失敗 respectively, each with its shape mark

### Requirement: The wall and the tray are two roving listboxes
The wall SHALL be one listbox with one tab stop whose arrow keys, Home and End move focus in reading order across groups and whose Enter, Space and click select a subject. The tray SHALL be a second listbox labelled `<subject>的圖片` with its own tab stop directly after the wall. Escape inside the tray SHALL return focus to the owner tile without closing anything.

#### Scenario: Keys move focus, not selection
- **WHEN** focus is on the first tile and the player presses ArrowRight, End, then Home
- **THEN** focus moves to the second, the last, then the first tile, and no `select-subject` is emitted

#### Scenario: Activation selects once
- **WHEN** the player presses Enter on a focused tile
- **THEN** `select-subject` is emitted once with that subject key

#### Scenario: Escape in the tray returns to the owner
- **WHEN** focus is in the tray and the player presses Escape
- **THEN** focus moves to the owner tile and the Escape does not propagate

#### Scenario: A removed focused tile reports focus loss
- **WHEN** a new committed `groups` no longer contains the focused tile
- **THEN** the wall emits `focus-lost` once
