## ADDED Requirements

### Requirement: The key list is the single canonical inventory record for registry items

For every item whose key exists in `ITEM_REGISTRY`, `actor.db.inventory` SHALL be the canonical inventory representation consumed by economy (buy/sell), quest ACQUIRE progress, guild rewards, NPC intent transfers, and the `背包` command; any registry item the player legitimately holds SHALL be present in this list. The shop economy and the localized item commands SHALL keep the canonical list mirrored by contained Evennia Objects: buy materializes one mirror per bought unit, sell removes the mirrors of the sold units, and 拿/丟/給 move objects together with the key delta. Items granted through key-only flows (quest rewards, guild rewards, NPC intent transfers) remain list-only until the player first uses 拿/丟/給, which materializes the missing mirror object.

#### Scenario: Bought item appears in the canonical inventory

- **WHEN** a player buys an item from a shop
- **THEN** the item key is present in `db.inventory`, visible in `背包`, sellable, counted by ACQUIRE progress, and mirrored by a contained object

### Requirement: Localized item commands synchronize containment and the key list

`拿`, `丟`, and `給` SHALL move the Evennia Object's containment AND apply the matching key-list delta through the deterministic inventory planner in one atomic step, so a held registry item is always mirrored in `db.inventory` and vice versa. A `丟`/`給` on a key that has no contained object yet SHALL first materialize the missing mirror object and then transfer the key in the same atomic step.

#### Scenario: Picked-up object is recorded in the canonical inventory

- **WHEN** a player uses `拿 <item>` on a room object whose key is in `ITEM_REGISTRY`
- **THEN** the object moves into the character's containment and its key is added to `db.inventory` in the same atomic operation

#### Scenario: Dropped object leaves the canonical inventory

- **WHEN** a player uses `丟 <item>` on an item they hold
- **THEN** the object moves to the room and its key is removed from `db.inventory` in the same atomic operation

#### Scenario: Given object leaves the canonical inventory

- **WHEN** a player uses `給 <item> = <target>` on an item they hold and the target is a player character or NPC
- **THEN** the object moves to the target, its key is removed from the giver's `db.inventory`, and the key is added to the target's `db.inventory` in the same atomic operation

#### Scenario: Bought item can be dropped and given

- **WHEN** a player who bought a `meal` uses `丟 meal` or `給 meal = <npc>`
- **THEN** the command resolves the materialized contained object and succeeds, removing the key from `db.inventory` and moving the object

#### Scenario: Key-only item materializes its mirror on drop or give

- **WHEN** a player holds a registry key in `db.inventory` without any contained object (e.g. from a quest reward) and uses `丟 <key>` or `給 <key> = <target>`
- **THEN** the command materializes the missing contained object (in the room, or at the target for give), removes the key from `db.inventory`, and adds it to a character-like target's `db.inventory` in the same atomic operation

#### Scenario: A failed transfer changes nothing

- **WHEN** an object move or key-list write fails mid-operation
- **THEN** neither the containment nor the key list changes (all-or-nothing)

#### Scenario: Non-registry objects remain containment-only

- **WHEN** a player uses `拿`/`丟`/`給` on an Evennia Object whose key is not in `ITEM_REGISTRY`
- **THEN** the object moves as today and no `db.inventory` entry is created or removed
