## ADDED Requirements

### Requirement: Top navigation retains stable tool placement while respecting mode availability
The top navigation bar SHALL lay its labelled primary controls out in one primary region, in this
order: the character status entry (角色狀態), the quest entry (任務), the inventory entry (背包 — the
exploration `inventory` entry and the combat root's `bag` entry are the same concept), the map control
(地圖), and the settings control (設定), followed by the `工具` group. Each primary control SHALL be as
wide as its concept's label length dictates, whatever the mode, and the region SHALL be exactly as
wide as all five controls together and SHALL pack its present controls against its trailing edge, so
the 設定 control and the `工具` group keep the same horizontal position (within 1px) in exploration,
dialogue, and combat at a fixed viewport size, and the space a missing entry leaves collects on the
brand side. An entry the current mode or the committed panels do not supply (the map control in
combat, the character and quest entries in combat, an entry whose panel is unavailable) SHALL be
absent from rendering, the accessibility tree, and the tab order, and SHALL NOT be replaced by a
disabled, `aria-disabled`, `visibility: hidden`, or otherwise present placeholder. The DOM order of
the present controls SHALL equal their visual order. A disabled primary entry keeps its disabled
reason as its `title`. At viewports up to 1350px wide the controls SHALL use compact padding, and at
1280x720 no navigation control SHALL intersect the top-meta or character-switcher cluster.

Each icon-only `工具` control SHALL disclose its label visually in one shared tooltip treatment,
shown while the pointer rests on the control or on the tooltip itself, and when keyboard focus
arrives on the control by Tab. Focus returned to the control programmatically (a closing surface
restoring its opener) SHALL NOT show the tooltip. The tooltip text SHALL be the control's label; the
tooltip SHALL be hidden from assistive technology (the label is already the control's accessible
name), SHALL NOT take focus, SHALL hide when the control is activated, and SHALL follow the motion
level. Escape SHALL hide a visible tooltip without moving focus. When the tooltip belongs to the
focused control, that Escape SHALL be consumed by the dismissal and SHALL NOT also reach the dock's
keyboard router; once no tooltip shows, Escape on the control SHALL reach the router as before. A
tooltip shown by the pointer SHALL hide on any Escape without consuming it. The next hover or Tab
focus SHALL show the tooltip again.

#### Scenario: Combat removes unavailable entries
- **WHEN** the committed mode changes from exploration to combat at a fixed viewport of 1920x1080, 1440x900, or 1280x720
- **THEN** the 角色狀態, 任務, and 地圖 controls are absent from rendering and the tab order, the combat 背包 control stands immediately before 設定, and the left edges of the 設定 control and of the `工具` group differ from their exploration positions by at most 1px

#### Scenario: An unavailable panel leaves no placeholder
- **WHEN** the committed exploration panel reports the quest surface unavailable
- **THEN** no quest control and no placeholder renders, and the 設定 control and the `工具` group keep their positions

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

## MODIFIED Requirements

### Requirement: The top navigation bar carries the tool group

The top navigation bar SHALL carry, after its 設定 control, one labelled group (`工具`) of icon
controls that open the client's secondary overlays and reference drawers: 技能系譜 (the skill lineage
overlay), 圖鑑 (the world-codex reference drawer), 稱號冊 (the title-codex overlay), 角色肖像圖庫 (the
portrait gallery overlay), and 說明 (the help overlay), in that order. Each control SHALL carry an
accessible name equal to its label, taken from the one tool model that also titles the header of the
surface it opens, SHALL disclose that label visually in the shared tool tooltip that the stable
top-navigation placement requirement defines (and carry no native `title` tooltip), SHALL be reachable
by sequential keyboard navigation, and SHALL open its surface in one pointer action or one Enter press, through the
same opener-captured path every other overlay or drawer opener uses, so closing the surface returns
focus to that control. The 角色肖像圖庫 control SHALL render only while the committed `gallery` panel is
available. The group SHALL render in every mode that renders the top navigation bar, whether the
command line is expanded or collapsed, and SHALL NOT push a keyboard menu frame. No other surface
SHALL carry a second opener for these five surfaces, and the command line SHALL carry none. The group
SHALL fit the 48px bar: at 1280x720, with every navigation entry, the gallery control, and a
maximum-length character name present, the navigation bar's controls SHALL NOT intersect the top-meta
and character-switcher cluster.

#### Scenario: Each tool opens its surface in one action
- **WHEN** the shell renders in exploration mode with the command line collapsed and the `gallery` panel available, and the player activates 技能系譜, then 稱號冊, then 角色肖像圖庫, then 說明, closing each surface in between
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
- **WHEN** the shell renders in exploration mode at 1280x720 with every navigation entry, the gallery control, and a maximum-length character name present
- **THEN** every tool-group control lies inside the 48px bar, and no navigation control intersects the top-meta or character-switcher cluster

#### Scenario: The command line carries no tool opener
- **WHEN** the command line is expanded
- **THEN** it carries no 技能系譜, 圖鑑, 稱號冊, 設定, 說明, or 角色肖像圖庫 control
