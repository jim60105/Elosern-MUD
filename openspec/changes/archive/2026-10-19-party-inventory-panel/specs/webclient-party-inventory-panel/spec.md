# Spec Delta

## Purpose

Publish the viewed party member's equipment doll, bag rows with server-authored use, equip and give descriptors, and the party purse as one exact read-only panel for the party window's bag tab.

## ADDED Requirements

### Requirement: The party_inventory panel is an exact read-only version-1 panel
The presentation registry SHALL register `party_inventory` at schema version 1, available in exploration and combat. Its available form SHALL contain exactly `schema_version`, `available`, `kind: "party_inventory"`, `member_id`, `purse`, `equipment` and `rows`; server, protocol mirror and Vue store allowlists SHALL name it in lockstep.

#### Scenario: The purse is the commander's wallet
- **WHEN** the viewed member is companion 艾拉 and the commander holds 1,240 copper
- **THEN** `purse` is 1240 and no companion wallet appears anywhere

#### Scenario: Shape drift is rejected identically
- **WHEN** a payload carries an unknown field or a row without its descriptors
- **THEN** the server validator and the client mirror reject it identically

### Requirement: Equipment reflects the viewed member's worn slots
`equipment` SHALL contain exactly `weapon_main`, `weapon_off`, `armor` (each an item key or null), `accessories` (ordered item keys) and `accessory_limit`, read from the viewed member's normalized canonical equipment.

#### Scenario: A companion's doll is her own
- **WHEN** the viewed member is 艾拉 wearing a staff, a robe and one accessory
- **THEN** `equipment` names exactly those keys with `weapon_off` null and `accessory_limit` equal to the rule's accessory cap

### Requirement: Bag rows carry presentation and server-authored descriptors
Each row SHALL contain exactly `item_key`, `display_name`, `held`, `equipped_count`, `slot` (null for non-equipment), `presentation` (kind, icon, rarity, summary, or null), `use`, `toggle` and `give`. `use` and `toggle` SHALL be descriptors with `enabled` and a bounded reason (or null when inapplicable); `give` SHALL carry `enabled`, a bounded reason and `max_quantity` (unequipped copies), computed by the transfer rule's preflight.

#### Scenario: Equipped copies cannot be given
- **WHEN** 卡恩 holds one warhammer and has it equipped
- **THEN** the warhammer row has `equipped_count: 1`, `give.enabled: false` with the `item_equipped` message, and `give.max_quantity: 0`

#### Scenario: Combat disables giving with the fixed reason
- **WHEN** the snapshot is built during an active combat session
- **THEN** every row's `give.enabled` is false with the reason 「戰鬥中無法交換物品。」, toggles stay enabled where the rule allows, and `use` routes to the member's combat draft instead of field use

### Requirement: The panel follows the viewed member and never invents rows
The panel SHALL be built for the session's viewed member (falling back to the commander), republished by `party.view_member`, identical with and without possession, and SHALL use the common unavailable form rather than invent rows, counts or descriptors when canonical inventory cannot be read.

#### Scenario: Malformed storage is unavailable
- **WHEN** the viewed member's stored inventory is malformed
- **THEN** `party_inventory` takes the common unavailable form with a stable reason and no rows
