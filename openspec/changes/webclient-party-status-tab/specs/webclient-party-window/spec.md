# Spec Delta

## ADDED Requirements

### Requirement: The status tab shows true values with a trait waterfall
The 狀態 tab SHALL show a hero row (portrait, name, title, and the guild `GradeGem` with merit only when the member has a guild rank), the HP, MP and SP gauges, and trait rows (label, base, effective, buffed values green and debuffed values orange, each also signed); selecting a trait SHALL show its breakdown waterfall: base, each layer with its source bar, glyph and text label (裝備, 技能, 狀態), then the effective total. The first trait with layers SHALL be selected on open.

#### Scenario: A buffed trait is never color-only
- **WHEN** 艾拉's 魔力 is 18 base and 27 effective
- **THEN** the row shows 27 with a + sign and the buff colour, and the waterfall lists four layers with their source text labels ending at 27

#### Scenario: No guild rank shows no gem
- **WHEN** the viewed member has no guild rank
- **THEN** the hero row renders no `GradeGem` and no merit

### Requirement: The status tab shows conditions and an honest disguise
Condition rows SHALL show a shape glyph, label, remaining time and modifier summary, and selecting one SHALL show its source, remaining time and modifiers; an active disguise SHALL appear at the detail's foot with its displayed values labelled as displayed, while the tab always shows true values. The tab SHALL be available in exploration and combat.

#### Scenario: Disguise never replaces true values
- **WHEN** the viewed companion is disguised as a herbalist
- **THEN** every trait row shows the true value and the displayed values appear only in the labelled disguise section

#### Scenario: Combat keeps the tab
- **WHEN** the window is opened on 狀態 during combat
- **THEN** the tab renders the viewed member's committed values instead of an unavailable reason
