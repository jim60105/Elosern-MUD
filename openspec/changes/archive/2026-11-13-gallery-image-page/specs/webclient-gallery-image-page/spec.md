## Purpose

Present one selected gallery image with its committed facts and a footer whose
buttons follow the selected subject's declared capabilities, never a
comparison of subject kinds in the client.

## ADDED Requirements

### Requirement: The footer follows the declared capabilities
The page footer SHALL offer, for a stored card, in order: 刪除 when deletion is declared, 臉框 when face rectangles are declared, 舞台位置 when stage is declared, 綁定裝備 when bindings are declared, 設為預設 when the kind allows several cards (disabled as 目前預設 on the default), and 重新生成 when it allows one card. The footer SHALL be computed from committed capabilities only.

#### Scenario: A multi-card card with every capability
- **WHEN** capabilities declare deletion, face rectangles, stage, bindings and `max_cards: null`, and the selected card is not the default
- **THEN** the buttons are 刪除, 臉框, 舞台位置, 綁定裝備, 設為預設, all enabled

#### Scenario: The default card's 設為預設 is disabled
- **WHEN** the same card is the default
- **THEN** 設為預設 is disabled with the reason 目前預設

#### Scenario: A one-card kind without deletion
- **WHEN** capabilities declare face rectangles and stage, no deletion, no bindings and `max_cards: 1`
- **THEN** the buttons are 臉框, 舞台位置, 重新生成

#### Scenario: A one-card kind with deletion and no geometry
- **WHEN** capabilities declare deletion, no face rectangle, no stage and `max_cards: 1`
- **THEN** the buttons are 刪除 and 重新生成

### Requirement: Non-card selections have fixed footers
The footer SHALL offer no button for a pending row, 重新生成 for a failed row, 生成新圖 for a subject without any image, and for an official entry 清除個人調整, 臉框, 舞台位置 and 設為預設 (清除選取 instead when it is current) only while personal official preferences are supported, gating 臉框 and 舞台位置 on the declared geometry facts.

#### Scenario: A pending row has no buttons and says it is generating
- **WHEN** the selection is a pending row
- **THEN** the footer has no buttons and the page shows 生成中

#### Scenario: Official entries without personal preferences are read-only
- **WHEN** an official entry is selected and `supports_personal_official_preferences` is false
- **THEN** the footer has no buttons

#### Scenario: A current official entry offers clearing
- **WHEN** a current official entry is selected with personal preferences supported
- **THEN** the buttons are 清除個人調整, 臉框, 舞台位置, 清除選取

### Requirement: Deletion takes two steps
Pressing 刪除 SHALL arm a confirmation instead of emitting; only the confirmation SHALL emit `press("delete")`, and cancel, Escape or a changed selection SHALL disarm without emitting.

#### Scenario: Cancel emits nothing
- **WHEN** the player presses 刪除 and then cancels
- **THEN** no `press` event was emitted

### Requirement: The page renders committed facts in cells
The page SHALL render the selected image's facts as cells: 圖片 (committed label), 生成時間 (relative and exact local time from `created_at`) for stored and failed rows, 狀態 only when the kind allows several cards, 標記 with the committed chips, and 綁定條件 with committed warning conditions for that card spanning both columns. A non-null committed `description` SHALL render in a letter box. The ribbon SHALL read the category label, followed by `・` and the group label when the group has one.

#### Scenario: A tier subject's ribbon names the tier
- **WHEN** the selected subject is in group `t_low` of category `monster`
- **THEN** the ribbon reads 魔物・t_low

#### Scenario: Chips are verbatim
- **WHEN** the selected card's committed chips are 主手 and 預設臉框
- **THEN** the 標記 cell lists exactly those two strings
