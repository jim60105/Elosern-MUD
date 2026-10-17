# Spec Delta

## ADDED Requirements

### Requirement: In combat the bag shows counts and saves draft item use
During combat the holdings strip SHALL show counts only, transfer controls SHALL be absent, the action bar SHALL show 戰鬥中無法交換物品, 使用 SHALL become 設為 X 本回合的行動… which saves that member's v7 draft entry through the existing combat item flow, and equipment toggles SHALL stay available for every member.

#### Scenario: Combat use saves the draft entry
- **WHEN** in combat the player selects 艾拉's mana potion and activates 設為 艾拉 本回合的行動…
- **THEN** the existing combat item review/target flow opens for 艾拉 and no `inventory.use` or `party.transfer` is sent
