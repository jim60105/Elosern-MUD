# Spec Delta

## Purpose

Shared window primitives extracted from the quest drawer frame (window frame, member rail, list-detail grid, action bar and holdings strip) that the party window and the shop window compose.

## ADDED Requirements

### Requirement: WindowFrame carries the drawer chrome and focus contract
`WindowFrame` SHALL render the seal glyph, the title, the first-level `IconTabs`, a header-extras slot (purse, quota) and a close control, and SHALL inherit the `HudDrawer` modal focus, Escape and motion contract unchanged.

#### Scenario: Escape closes and restores focus
- **WHEN** a window built on `WindowFrame` is open and the player presses Escape outside any text input
- **THEN** the window closes and focus returns to its opener, exactly as the quest drawer does

### Requirement: MemberRail is a roving-focus member list
`MemberRail` SHALL list member entries in the given order with portrait, name, a ▼倒地 shape-and-text marker for knocked-out members, and an unread dot with a text accessible name, end with a dashed 空位 entry when a slot is free, and move focus with the arrow keys while Enter or Space selects.

#### Scenario: Knocked-out state is never color-only
- **WHEN** an entry is knocked out
- **THEN** it shows the ▼ shape and the text 倒地, and its accessible name includes 倒地

#### Scenario: Arrow keys move focus without selecting
- **WHEN** focus is on the first entry and the player presses ArrowDown
- **THEN** focus moves to the second entry and the selection is unchanged until Enter or Space

### Requirement: ListDetail scrolls its columns independently
`ListDetail` SHALL render a list column and a detail column whose overflow scrolls independently, with the action bar pinned to the bottom of the detail column.

#### Scenario: Scrolling the list keeps the action bar visible
- **WHEN** the list column scrolls to its end
- **THEN** the detail column and its action bar stay in place

### Requirement: ActionBar shows a committed disabled reason
`ActionBar` SHALL render a left reason slot and right-aligned buttons; a disabled control's committed reason SHALL be shown as state feedback, and the bar SHALL render no explanatory rule text of its own.

#### Scenario: A disabled transfer shows its reason
- **WHEN** the bar receives a disabled give control with the reason 戰鬥中無法交換物品
- **THEN** the reason text is visible in the left slot and the control is disabled

### Requirement: HoldingsStrip renders server facts only
`HoldingsStrip` SHALL render one cell per member with that member's held count and, when supplied, the server delta (signed changes or 無法裝備), and a per-cell give control only when the caller supplies an enabled receive fact; it SHALL compute no count or delta.

#### Scenario: Missing deltas are not invented
- **WHEN** a holdings row carries a null delta
- **THEN** the cell shows the count only and no delta text

### Requirement: Primitive sizing and motion use tokens
Every primitive size SHALL use `calc(<n>px * var(--ui-scale))` or a design token, no text SHALL be smaller than `--text-xs`, every literal duration SHALL use a `--motion-*` token, and the new glyphs from the approved prototype SHALL be added to `dock-icons.js`.

#### Scenario: The style lint finds no raw sizes
- **WHEN** the primitives' styles are inspected by the component tests
- **THEN** no raw pixel size, sub-`--text-xs` text or literal duration appears
