# Spec Delta

## MODIFIED Requirements

### Requirement: party.view_member selects the viewed member for the session
The production registry SHALL register `party.view_member` accepting exactly `{member_id, tab, skill_key, item_key}`, where `member_id` names the commander or an effective party member (presence not required), `tab` is one of `member`, `bag`, `status`, `skills`, `lineage`, `shop`, `skill_key` is a bounded skill key or null naming the skill selected in the 技能 tab, and `item_key` is a bounded whitespace-free item key or null. The selection SHALL be stored per session, keyed to the commander, and SHALL never authorize a mutation.

#### Scenario: Selecting a companion republishes the party panel
- **WHEN** the player selects 艾拉 on the member rail
- **THEN** one success result is followed by an update whose `party.viewed_member_id` is 艾拉's identity, and no gameplay state changes

#### Scenario: A forged member is refused, not substituted
- **WHEN** `party.view_member` names an NPC outside the party
- **THEN** it is rejected with `not_party_member` and the previous selection stays

#### Scenario: Possession keeps the selection
- **WHEN** the player selects 卡恩 and then possesses 艾拉
- **THEN** the party payload after the possession transition still reports 卡恩 as viewed

#### Scenario: Selecting an item stores it with the member
- **WHEN** the player selects 艾拉 with `item_key` 魔力藥水 on the bag tab
- **THEN** the session selection holds 艾拉 and 魔力藥水, and the update carries `item_holdings` for that item

#### Scenario: An unknown item key clears the holdings
- **WHEN** `item_key` names an item no registry entry defines
- **THEN** the selection stores null for the item and `item_holdings` reports no rows

#### Scenario: Selecting a skill publishes its detail
- **WHEN** the player selects 冰錐術 in the 技能 tab for 艾拉
- **THEN** the session selection holds 艾拉 and 冰錐術 and the next `character` payload carries `selected_skill` for 冰錐術
