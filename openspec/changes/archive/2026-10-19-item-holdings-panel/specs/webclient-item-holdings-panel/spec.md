# Spec Delta

## Purpose

Answer, for one selected item, every party member's held count and, for equipment, each member's server-computed stat delta, so the bag and shop strips never compute anything client-side.

## ADDED Requirements

### Requirement: The item_holdings panel is an exact read-only version-1 panel
The presentation registry SHALL register `item_holdings` at schema version 1, available in exploration and combat. Its available form SHALL contain exactly `schema_version`, `available`, `kind: "item_holdings"`, `item_key` (null when no item is selected), `giver_id` (the viewed member) and `rows`, one row per party member in party order (commander first). Server, protocol mirror and Vue store allowlists SHALL name it in lockstep.

#### Scenario: No selection yields no rows
- **WHEN** the session has no selected item
- **THEN** `item_key` is null and `rows` is empty

### Requirement: Holdings rows report counts and transfer availability
Each row SHALL contain exactly `member_id`, `held`, `equipped`, `delta` and `receive`; `held` SHALL count the member's canonical copies and `receive` SHALL carry `enabled` and a bounded reason from the transfer preflight for giving the selected item from the viewed member to that member (disabled on the viewed member's own row).

#### Scenario: An absent member cannot receive
- **WHEN** the selected potion is held by the viewed commander and companion 卡恩 is in another room
- **THEN** 卡恩's row reports his held count and `receive.enabled: false` with the `member_not_present` message

#### Scenario: Combat shows counts without transfer
- **WHEN** the panel is built during an active combat session
- **THEN** every row reports its held count and `receive.enabled` is false with 「戰鬥中無法交換物品。」

### Requirement: Equipment deltas are server-computed against each member's slot occupant
For an equipment item, each row's `delta` SHALL be either `{equippable: true, changes}` listing every nonzero effective-trait change (trait key, label, signed amount) from replacing that member's current occupant of the item's slot with the item, computed with the same breakdown arithmetic as the character panel, or `{equippable: false, reason}` with the toggle rule's stable reason; for a non-equipment item `delta` SHALL be null.

#### Scenario: A sword upgrade for one member and a downgrade for another
- **WHEN** the selected steel shortsword (attack +6) is compared for 艾拉 wielding a staff with attack +0 and for 卡恩 wielding a warhammer with attack +10
- **THEN** 艾拉's row lists attack +6 and 卡恩's row lists attack −4, each from the breakdown read model with no stored value changed

#### Scenario: An already equipped item reports no change
- **WHEN** the selected item is the member's current occupant of its slot
- **THEN** that row has `equipped: true` and `delta.changes` empty

### Requirement: The selected item rides the viewed-member selection
The session selection SHALL carry the selected item key, set through `party.view_member`, and the panel SHALL be republished with the viewed-member panels; computing it SHALL write nothing.

#### Scenario: Selecting an item republishes holdings
- **WHEN** the player selects 治療藥水 in the bag
- **THEN** one update carries `item_holdings` for 治療藥水 and every entity's attributes are unchanged
