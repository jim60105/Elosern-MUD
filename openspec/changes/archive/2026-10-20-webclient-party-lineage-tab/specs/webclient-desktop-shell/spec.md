# Spec Delta

## MODIFIED Requirements

### Requirement: The top navigation bar carries the tool group

The top navigation bar SHALL carry, after its 設定 control, one labelled group (`工具`) of icon
controls that open the client's secondary overlays and reference drawers, and SHALL NOT push a
keyboard menu frame.

#### Scenario: Each tool opens its surface in one action
- **WHEN** the shell renders in exploration mode with the command line collapsed and the `gallery` panel available, and the player activates 技能系譜, then 稱號冊, then 角色肖像圖庫, then 說明, closing each surface in between
- **THEN** each activation opens its surface (技能系譜 the party window on its 系譜 tab, the others their overlays), and each close returns focus to the control that opened it

#### Scenario: The codex tool opens the reference drawer
- **WHEN** the player activates the 圖鑑 control in the tool group
- **THEN** the world-codex reference drawer opens through the single open-drawer entry point, and closing it returns focus to the control

#### Scenario: The gallery tool follows the committed gallery panel
- **WHEN** the committed `gallery` panel is available, and a later revision commits the panel's unavailable form
- **THEN** the 角色肖像圖庫 control is rendered in the tool group while the panel is available, and after the unavailable form commits it is absent from the bar and the tab order

#### Scenario: The tool group is keyboard reachable
- **WHEN** the player moves focus through the top navigation bar with Tab
- **THEN** focus reaches every tool-group control in order, each exposes its label as its accessible name, and Enter on a focused control opens its surface

#### Scenario: The tool group fits the 48px bar at the minimum viewport
- **WHEN** the shell renders in exploration mode at 1451x790 with every navigation entry, the gallery control, and a maximum-length character name present
- **THEN** every tool-group control lies inside the 48px bar, and no navigation control intersects the top-meta or character-switcher cluster

#### Scenario: The command line carries no tool opener
- **WHEN** the command line is expanded
- **THEN** it carries no 技能系譜, 圖鑑, 稱號冊, 設定, 說明, or 角色肖像圖庫 control

#### Scenario: The tool group carries the five tools in order
- **WHEN** the tool group renders
- **THEN** it carries, in order, 技能系譜 for the party window's 系譜 tab, 圖鑑 for the world-codex reference drawer, 稱號冊 for the title-codex overlay, 角色肖像圖庫 for the portrait gallery overlay, and 說明 for the help overlay

#### Scenario: Each tool control names itself from the shared tool model
- **WHEN** a tool control renders
- **THEN** it carries an accessible name equal to its label, taken from the one tool model that also titles the header of the overlay or drawer it opens (技能系譜 instead opens the party window, whose 系譜 tab it selects), discloses that label visually in the shared tool tooltip that the stable top-navigation placement requirement defines, carries no native `title` tooltip, and is reachable by sequential keyboard navigation

#### Scenario: A tool opens through the opener-captured path
- **WHEN** the player activates a tool control with one pointer action or one Enter press
- **THEN** its surface opens through the same opener-captured path every other overlay or drawer opener uses, so closing the surface returns focus to that control

#### Scenario: The portrait gallery control follows the committed gallery panel
- **WHEN** the committed `gallery` panel is available and later becomes unavailable
- **THEN** the 角色肖像圖庫 control renders only while the committed `gallery` panel is available

#### Scenario: The tool group renders in every bar-bearing mode
- **WHEN** the top navigation bar renders in any mode, with the command line expanded or collapsed
- **THEN** the group renders

#### Scenario: The five surfaces have exactly one opener each
- **WHEN** the rendered surfaces are inspected for openers of the five tool surfaces
- **THEN** no surface other than the tool group carries a second opener for the 圖鑑, 稱號冊, 角色肖像圖庫 and 說明 surfaces (the party window keeps its own openers, and its 技能 tab links into 系譜), and the command line carries none of the tool openers

#### Scenario: The tool group fits the 48px bar
- **WHEN** the shell renders at the 1451x790 reference viewport with every navigation entry, the gallery control, and a maximum-length character name present
- **THEN** the group fits the 48px bar and the navigation bar's controls do not intersect the top-meta and character-switcher cluster
