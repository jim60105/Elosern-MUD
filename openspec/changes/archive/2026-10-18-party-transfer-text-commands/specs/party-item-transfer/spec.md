# Spec Delta

## ADDED Requirements

### Requirement: Text clients move items between members
The command `給 [數量] <物品> = <成員>` SHALL move items from the caller to the named member and `取回 [數量] <物品> = <成員>` SHALL move items from the named member to the commander, both through the party item transfer rule with the same rejections and messages as `party.transfer`. Both commands SHALL be documented in both player command documents.

#### Scenario: 取回 returns an item to the commander
- **WHEN** the commander uses `取回 魔力藥水 = 艾拉` outside combat while 艾拉 holds two
- **THEN** 艾拉 holds one, the commander holds one more, and no time passes

#### Scenario: 取回 during possession still returns to the commander
- **WHEN** the player, possessing 艾拉, uses `取回 乾糧 = 卡恩`
- **THEN** the ration moves from 卡恩 to the commander, not to 艾拉

#### Scenario: Text and action rejections match
- **WHEN** the same equipped item is requested through `取回` and through `party.transfer`
- **THEN** both report `item_equipped` with the same fixed Traditional Chinese message and nothing changes

#### Scenario: An unknown member token is refused
- **WHEN** a player uses `取回 乾糧 = 不存在的人`
- **THEN** the command reports `not_party_member` and nothing changes
