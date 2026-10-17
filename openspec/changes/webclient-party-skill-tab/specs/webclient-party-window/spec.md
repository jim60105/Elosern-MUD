# Spec Delta

## ADDED Requirements

### Requirement: The skill tab browses the viewed member's skills with growth
The 技能 tab SHALL keep the active/passive segment, search and the category tree, and each row SHALL add the member's proficiency meter and level and a 新 tag for skills in the session recent-unlock set; the detail card SHALL show target, cost, field capability, the lineage position (prerequisite → skill → next unlock) linking into the 系譜 tab, and the 威力與消耗 row of the `freeform_ladder` (1/4, 1/2, 1, 2, 4 with each rung's MP cost or locking level) only when the payload carries it.

#### Scenario: A locked rung shows its level
- **WHEN** 艾拉's 冰錐術 row carries a ladder whose rung 2 is locked at Lv 6
- **THEN** the 威力與消耗 row shows MP costs for the unlocked rungs and 需 Lv 6 for rung 2, with no client arithmetic

#### Scenario: No mastery shows no ladder
- **WHEN** the row carries no `freeform_ladder`
- **THEN** the detail shows no 威力與消耗 row

#### Scenario: Opening the tab clears the unread dot
- **WHEN** the player opens 技能 with 艾拉 selected while 艾拉 is unread
- **THEN** `party.view_member` with `tab: skills` is sent and the 新 tags stay visible for the session

### Requirement: The skill tab casts and books for the viewed member
The action bar SHALL offer 施放 (the viewed member casts through the existing server preview and target flow) and 排入修煉 (books the viewed member's practice); in combat both SHALL be disabled with their committed reasons and combat casting stays on the command card.

#### Scenario: A companion casts from the tab
- **WHEN** 艾拉 is viewed and the player activates 施放 on 治癒之光
- **THEN** one `explore.skill_preview` with 艾拉's `actor_id` is sent and the existing dock target flow continues for 艾拉

#### Scenario: Booking practice for a companion
- **WHEN** 艾拉 is viewed and the player activates 排入修煉 on 治癒之光
- **THEN** exactly one `explore.practice {actor_id: 艾拉, skill: healing_light}` is sent and no time-skip form opens
