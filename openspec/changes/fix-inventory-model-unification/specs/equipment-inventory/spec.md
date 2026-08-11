## ADDED Requirements

### Requirement: The key list is the single canonical inventory record for registry items

For every item whose key exists in `ITEM_REGISTRY`, `actor.db.inventory` SHALL be the canonical inventory representation consumed by economy (buy/sell), quest ACQUIRE progress, guild rewards, NPC intent transfers, and the `背包` command; any registry item the player legitimately holds SHALL be present in this list and mirrored by a contained Evennia Object.

#### Scenario: Bought item appears in the canonical inventory

- **WHEN** a player buys an item from a shop
- **THEN** the item key is present in `db.inventory`, visible in `背包`, sellable, counted by ACQUIRE progress, and mirrored by a contained object

### Requirement: Localized item commands synchronize containment and the key list

`拿`, `丟`, and `給` SHALL move the Evennia Object's containment AND apply the matching key-list delta through the deterministic inventory planner in one atomic step, so a held registry item is always mirrored in `db.inventory` and vice versa.

#### Scenario: Picked-up object is recorded in the canonical inventory

- **WHEN** a player uses `拿 <item>` on a room object whose key is in `ITEM_REGISTRY`
- **THEN** the object moves into the character's containment and its key is added to `db.inventory` in the same atomic operation

#### Scenario: Dropped object leaves the canonical inventory

- **WHEN** a player uses `丟 <item>` on an item they hold
- **THEN** the object moves to the room and its key is removed from `db.inventory` in the same atomic operation

#### Scenario: Given object leaves the canonical inventory

- **WHEN** a player uses `給 <item> = <target>` on an item they hold
- **THEN** the object moves to the target and its key is removed from `db.inventory` in the same atomic operation

#### Scenario: Bought item can be dropped and given

- **WHEN** a player who bought a `meal` uses `丟 meal` or `給 meal = <npc>`
- **THEN** the command resolves the materialized contained object and succeeds, removing the key from `db.inventory` and moving the object

#### Scenario: A failed transfer changes nothing

- **WHEN** an object move or key-list write fails mid-operation
- **THEN** neither the containment nor the key list changes (all-or-nothing)

#### Scenario: Non-registry objects remain containment-only

- **WHEN** a player uses `拿`/`丟`/`給` on an Evennia Object whose key is not in `ITEM_REGISTRY`
- **THEN** the object moves as today and no `db.inventory` entry is created or removed
