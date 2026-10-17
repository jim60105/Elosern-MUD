# Spec Delta

## ADDED Requirements

### Requirement: Any present party member's equipment toggles through the same free rule
The equipment toggle SHALL accept an explicit member, authorized for the organizing purpose, and SHALL apply the existing toggle rule to that member's own inventory and equipment, in exploration and in combat, consuming no combat turn and no world time. A member's saved combat draft entry SHALL be revalidated against the new equipment when the round is submitted.

#### Scenario: A knocked-out companion is re-equipped
- **WHEN** the commander toggles a warhammer onto companion 卡恩 at stored HP 1 outside combat
- **THEN** 卡恩's main hand holds the warhammer, the replaced weapon stays in his bag, and the tick is unchanged

#### Scenario: Combat toggle keeps the round
- **WHEN** during command selection the commander equips a shield on companion 艾拉, whose draft entry is already saved
- **THEN** no round, turn or time is consumed, and 艾拉's saved entry is preflighted against her new equipment when the full draft is submitted

#### Scenario: Toggling an absent member is refused
- **WHEN** the named member is in another room
- **THEN** the toggle is rejected with `member_not_present` and no equipment changes
