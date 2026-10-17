# Spec Delta

## MODIFIED Requirements

### Requirement: The top navigation bar carries the tool group

The top navigation bar SHALL carry, after its labelled primary entries and before its 設定 control,
one labelled group (`工具`) of icon controls that open the client's secondary overlays and reference
drawers, and SHALL NOT push a keyboard menu frame.

#### Scenario: Each tool opens its surface in one action
- **WHEN** the shell renders in exploration mode with the command line collapsed and the `gallery` panel available, and the player activates 信件, then 稱號冊, then 角色肖像圖庫, then 說明, closing each surface in between
- **THEN** each activation opens its overlay, and each close returns focus to the control that opened it

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
- **THEN** it carries no 信件, 圖鑑, 稱號冊, 設定, 說明, or 角色肖像圖庫 control

#### Scenario: The tool group carries the five tools in order
- **WHEN** the tool group renders
- **THEN** it carries, in order, 信件 for the letters drawer, 圖鑑 for the world-codex reference drawer, 稱號冊 for the title-codex overlay, 角色肖像圖庫 for the portrait gallery overlay, and 說明 for the help overlay; skill lineage is reached through the party window's 系譜 tab

#### Scenario: Each tool control names itself from the shared tool model
- **WHEN** a tool control renders
- **THEN** it carries an accessible name equal to its label, taken from the one tool model that also titles the header of the surface it opens, discloses that label visually in the shared tool tooltip that the stable top-navigation placement requirement defines, carries no native `title` tooltip, and is reachable by sequential keyboard navigation

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
- **THEN** no surface other than the tool group carries a second opener for them, and the command line carries none

#### Scenario: The tool group fits the 48px bar
- **WHEN** the shell renders at the 1451x790 reference viewport with every navigation entry, the gallery control, and a maximum-length character name present
- **THEN** the group fits the 48px bar and the navigation bar's controls do not intersect the top-meta and character-switcher cluster

### Requirement: Top navigation retains stable tool placement while respecting mode availability
The top navigation bar SHALL lay its labelled primary controls out in one primary region in a fixed
order, each as wide as its concept's label length dictates whatever the mode, with the present
controls packed against the region's trailing edge.

#### Scenario: Combat removes unavailable entries
- **WHEN** the committed mode changes from exploration to combat at a fixed viewport of 1451x790, 1741x948, or 2560x1440
- **THEN** the 任務 and 地圖 controls are absent from rendering and the tab order, the 隊伍 control stays, and the left edges of the `工具` group and of the 設定 control differ from their exploration positions by at most 1px

#### Scenario: An unavailable panel leaves no placeholder
- **WHEN** the committed exploration panel reports the quest surface unavailable
- **THEN** no quest control and no placeholder renders, and the `工具` group and the 設定 control keep their positions

#### Scenario: Keyboard user identifies a tool
- **WHEN** a `工具` control receives keyboard focus by Tab
- **THEN** its label appears as a visible tooltip while focus stays on the control, and Escape hides the tooltip, keeps focus on the control, and leaves the dock's frame unchanged

#### Scenario: A second Escape reaches the dock
- **WHEN** the tooltip of the focused `工具` control has been dismissed with Escape and the player presses Escape again
- **THEN** the key reaches the dock's keyboard router exactly as it would without the tooltip

#### Scenario: A restored opener stays quiet
- **WHEN** a surface opened from a `工具` control closes and returns focus to that control
- **THEN** no tooltip appears

#### Scenario: Pointer user identifies a tool
- **WHEN** the pointer rests on a `工具` control and then moves onto its tooltip
- **THEN** the label appears as a visible tooltip and stays visible, and activating the control hides it

#### Scenario: The primary region's order is fixed
- **WHEN** the bar renders in any mode
- **THEN** the primary region's order is the party entry (隊伍), the quest entry (任務), and the map control (地圖), followed by the `工具` group and finally the settings control (設定)

#### Scenario: Trailing packing keeps the settings and tool positions stable
- **WHEN** the bar renders in exploration, dialogue, and combat at a fixed viewport size
- **THEN** the region is exactly as wide as all three labelled controls together, so the `工具` group and the 設定 control keep the same horizontal position (within 1px) in all three modes, and the space a missing entry leaves collects on the brand side

#### Scenario: An unsupplied entry leaves no placeholder
- **WHEN** the current mode or the committed panels do not supply an entry (the map control in combat, the quest entry in combat, an entry whose panel is unavailable)
- **THEN** it is absent from rendering, the accessibility tree, and the tab order, and is not replaced by a disabled, `aria-disabled`, `visibility: hidden`, or otherwise present placeholder

#### Scenario: Order, disabled reasons, and compact padding hold
- **WHEN** the present controls render, when a primary entry is disabled, and at viewports up to 1350px wide
- **THEN** DOM order equals visual order, a disabled primary entry keeps its disabled reason as its `title`, and the controls use compact padding
- **AND** at the 1451x790 reference viewport no navigation control intersects the top-meta or character-switcher cluster

#### Scenario: A tool tooltip shows on hover and on Tab focus
- **WHEN** the pointer rests on an icon-only `工具` control or on the tooltip itself, or keyboard focus arrives on the control by Tab
- **THEN** the control discloses its label visually in one shared tooltip treatment, while focus returned to the control programmatically by a closing surface restoring its opener shows no tooltip

#### Scenario: The tooltip's own properties are fixed
- **WHEN** a tooltip is shown
- **THEN** its text is the control's label, it is hidden from assistive technology since the label is already the control's accessible name, it takes no focus, it hides when the control is activated, and it follows the motion level

#### Scenario: Escape dismisses a tooltip with router-safe consumption
- **WHEN** the player presses Escape while a tooltip is visible
- **THEN** the tooltip hides without moving focus; when the tooltip belongs to the focused control that Escape is consumed by the dismissal and does not also reach the dock's keyboard router, while once no tooltip shows Escape on the control reaches the router as before
- **AND** a tooltip shown by the pointer hides on any Escape without consuming it, and the next hover or Tab focus shows the tooltip again

#### Scenario: 隊伍 opens the party window on its last tab
- **WHEN** the player last left the party window on 技能 and activates 隊伍
- **THEN** the party window opens on 技能 with the session's viewed member

## ADDED Requirements

### Requirement: Window hotkeys act only outside text inputs
The client SHALL bind P (隊伍, last tab), B (背包), C (狀態), K (技能), L (系譜), J (任務) and M (地圖) to open their surfaces, and the keys SHALL act only while focus is outside any text input, textarea or contenteditable element and no modal question is open; an unavailable surface SHALL ignore its key.

#### Scenario: A hotkey opens the bag tab
- **WHEN** focus is on the stage and the player presses B
- **THEN** the party window opens on 背包 with the session's viewed member

#### Scenario: Typing never triggers a hotkey
- **WHEN** focus is in the command line and the player types "p"
- **THEN** the character is typed and no window opens

#### Scenario: Map is inert in combat
- **WHEN** the player presses M in combat
- **THEN** nothing opens, because the map entry is absent in combat
