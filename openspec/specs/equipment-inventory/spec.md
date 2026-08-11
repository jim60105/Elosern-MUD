## Purpose

Defines read-only equipment and inventory views plus deterministic-core mutation operations,
including bounded accessory slots and compatibility with imported persistent storage.

## Requirements

### Requirement: EquipmentSlot defines four slots sized to the sample cards' own equipment shapes
`world/skills/equipment.py` SHALL define an `EquipmentSlot` `StrEnum` with exactly the members
`WEAPON_MAIN`, `WEAPON_OFF`, `ARMOR`, and `ACCESSORY`, borrowing evadventure's wield-location slot
structure (design doc §4: reference only, not its d20 formulas).

#### Scenario: EquipmentSlot has exactly the four documented members
- **WHEN** `EquipmentSlot` is inspected
- **THEN** it has exactly the members `WEAPON_MAIN`, `WEAPON_OFF`, `ARMOR`, `ACCESSORY` and no others

#### Scenario: A dual-wielded weapon pair occupies both weapon slots at once
- **WHEN** `equip_item()` equips one weapon into `WEAPON_MAIN` and a second into `WEAPON_OFF`
- **THEN** `slot_contents(EquipmentSlot.WEAPON_MAIN)` and `slot_contents(EquipmentSlot.WEAPON_OFF)`
  each return their own distinct item key, and neither slot's assignment affects the other

### Requirement: EquipmentHandler is mounted directly as entity.equipment
`LivingEntity` SHALL expose `entity.equipment` as an `EquipmentHandler` instance bound to that
entity — per design doc §5.2, `equipment` **is** the `EquipmentHandler`, the same relationship
`traits` has to `TraitHandler` — replacing change 3's placeholder `AttributeProperty`. The handler
SHALL read the private `entity.db.equipment` attribute, holding the raw dict change 4's loader writes
there (`entity.db.equipment = record["equipment"]`). Writes SHALL be performed by
`world.rules.equipment` deterministic-core operations.

#### Scenario: entity.equipment reads equipment from entity.db.equipment
- **WHEN** `entity.db.equipment` is `{"weapon_main": "light_sword", "weapon_off": None, "armor":
  "elf_traditional_garb", "accessories": ["crescent_earring"]}`
- **THEN** `entity.equipment.slot_contents(EquipmentSlot.WEAPON_MAIN)` returns `"light_sword"` and
  `slot_contents(EquipmentSlot.ACCESSORY)` returns a list containing `"crescent_earring"`

#### Scenario: entity.equipment tolerates an entity never populated by the import loader
- **WHEN** `entity.db.equipment` is `None` (an entity never run through change 4's loader) or `{}`
  (the design doc §5.3 reference example's empty equipment)
- **THEN** every slot reads as empty (`None` for single slots, `[]` for `ACCESSORY`) rather than
  raising

#### Scenario: entity.equipment has no bare-assignment form
- **WHEN** code attempts `entity.equipment = {...}` directly
- **THEN** the assignment raises, since `entity.equipment` is a read-only computed property returning
  an `EquipmentHandler` instance — the same way `entity.traits = {...}` is not a valid operation

#### Scenario: Writing to entity.db.equipment directly is reflected by entity.equipment
- **WHEN** code assigns `entity.db.equipment = {...}` directly, the way change 4's landed
  `instantiate_character()` does
- **THEN** the assignment succeeds with no error, and `entity.equipment` subsequently reflects the
  newly assigned data

### Requirement: ACCESSORY is a bounded multi-item slot
The equipment contract SHALL treat `ACCESSORY` as a list-valued slot capped at
`ACCESSORY_MAX_SLOTS` items, distinct from the three single-item slots.

#### Scenario: Multiple accessories can be equipped up to the cap
- **WHEN** `world.rules.equipment.equip_item()` equips accessories up to `ACCESSORY_MAX_SLOTS`
- **THEN** `slot_contents(EquipmentSlot.ACCESSORY)` returns a list of exactly that many item keys

#### Scenario: Equipping beyond the accessory cap is rejected
- **WHEN** an entity already holds `ACCESSORY_MAX_SLOTS` accessories and `equip_item()` is called
  with one more
- **THEN** the call raises rather than silently exceeding the cap

### Requirement: Inventory remains a flat list of item-key strings behind one deterministic planning boundary
The read-only `world/skills/equipment.py` SHALL define `list_items(entity)`. The mutating
`world/rules/equipment.py` SHALL define `plan_inventory_delta(entity, additions=(), removals=())`,
`apply_inventory_plan(plan)`, and convenience `add_item(entity, item_key)` / `remove_item(entity,
item_key)` operations over `entity.db.inventory`, the same flat repeated-key list populated by the import
loader. Gameplay mutations SHALL validate item keys structurally (each key is a non-empty string, so
unregistered but syntactically valid keys like `iron_ore` remain acceptable — see the appending
scenario) and SHALL validate positive integer quantities, and SHALL use the planner. Import
construction MAY populate the initial raw list without emitting acquisition progress.

#### Scenario: add_item appends to the existing raw inventory list
- **WHEN** `entity.db.inventory` is `["healing_potion"]` and `add_item(entity, "iron_ore")` is called
- **THEN** the committed inventory becomes `["healing_potion", "iron_ore"]`

#### Scenario: add_item tolerates an entity with no inventory yet
- **WHEN** `entity.db.inventory` is `None` and `add_item(entity, "healing_potion")` is called
- **THEN** the committed inventory becomes `["healing_potion"]` rather than raising

#### Scenario: remove_item removes exactly one matching entry
- **WHEN** `entity.db.inventory` is `["healing_potion", "iron_ore"]` and `remove_item(entity,
  "iron_ore")` is called
- **THEN** the committed inventory becomes `["healing_potion"]`

#### Scenario: insufficient removal fails before mutation
- **WHEN** a plan requests removal of two potions but inventory contains one
- **THEN** planning raises a named inventory error and the raw list is unchanged

#### Scenario: list_items reflects change 4's already-populated inventory verbatim
- **WHEN** an entity was constructed by change 4's `instantiate_character()` with a non-empty
  `inventory` array
- **THEN** `list_items(entity)` returns that same array's contents, unmodified

### Requirement: Inventory plans compose with larger atomic operations
An InventoryPlan SHALL expose complete before/after item lists and positive additions without applying
them. Reward and shop operations SHALL be able to combine its inventory write and computed ACQUIRE
quest-log replacement with wallet, merit, claims, or merchant-stock effects in one outer transaction.
`apply_inventory_plan()` used alone SHALL provide its own atomic transaction and cache restoration.

#### Scenario: Planning has no side effects
- **WHEN** a valid additions/removals plan is created but not applied
- **THEN** inventory and quest log remain byte-for-byte unchanged

#### Scenario: Outer transaction owns composed commit
- **WHEN** a shop purchase composes an InventoryPlan with wallet and stock replacements
- **THEN** inventory is written exactly once inside the shop transaction rather than committed early

#### Scenario: Standalone application restores cache on failure
- **WHEN** a standalone plan's inventory or ACQUIRE quest-log write is fault-injected to fail
- **THEN** database and in-process inventory/quest-log values equal their pre-application state

### Requirement: The key list is the single canonical inventory record for registry items
For every item whose key exists in `ITEM_REGISTRY`, `actor.db.inventory` SHALL be the canonical
inventory representation consumed by economy (buy/sell), quest ACQUIRE progress, guild rewards, NPC
intent transfers, and the `背包` command; any registry item the player legitimately holds SHALL be
present in this list. The shop economy and the localized item commands SHALL keep the canonical list
mirrored by contained Evennia Objects: buy materializes one mirror per bought unit, sell removes the
mirrors of the sold units, and 拿/丟/給 move objects together with the key delta. Items granted through
key-only flows (quest rewards, guild rewards, NPC intent transfers) remain list-only until the player
first uses 拿/丟/給, which materializes the missing mirror object.

#### Scenario: Bought item appears in the canonical inventory
- **WHEN** a player buys an item from a shop
- **THEN** the item key is present in `db.inventory`, visible in `背包`, sellable, counted by ACQUIRE
  progress, and mirrored by a contained object

### Requirement: Localized item commands synchronize containment and the key list
`拿`, `丟`, and `給` SHALL move the Evennia Object's containment AND apply the matching key-list delta
through the deterministic inventory planner in one atomic step, so a held registry item is always
mirrored in `db.inventory` and vice versa. A `丟`/`給` on a key that has no contained object yet SHALL
first materialize the missing mirror object and then transfer the key in the same atomic step.

#### Scenario: Picked-up object is recorded in the canonical inventory
- **WHEN** a player uses `拿 <item>` on a room object whose key is in `ITEM_REGISTRY`
- **THEN** the object moves into the character's containment and its key is added to `db.inventory`
  in the same atomic operation

#### Scenario: Dropped object leaves the canonical inventory
- **WHEN** a player uses `丟 <item>` on an item they hold
- **THEN** the object moves to the room and its key is removed from `db.inventory` in the same atomic
  operation

#### Scenario: Given object leaves the canonical inventory
- **WHEN** a player uses `給 <item> = <target>` on an item they hold and the target is a player
  character or NPC
- **THEN** the object moves to the target, its key is removed from the giver's `db.inventory`, and the
  key is added to the target's `db.inventory` in the same atomic operation

#### Scenario: Bought item can be dropped and given
- **WHEN** a player who bought a `meal` uses `丟 meal` or `給 meal = <npc>`
- **THEN** the command resolves the materialized contained object and succeeds, removing the key from
  `db.inventory` and moving the object

#### Scenario: Key-only item materializes its mirror on drop or give
- **WHEN** a player holds a registry key in `db.inventory` without any contained object (e.g. from a
  quest reward) and uses `丟 <key>` or `給 <key> = <target>`
- **THEN** the command materializes the missing contained object (in the room, or at the target for
  give), removes the key from `db.inventory`, and adds it to a character-like target's `db.inventory`
  in the same atomic operation

#### Scenario: A failed transfer changes nothing
- **WHEN** an object move or key-list write fails mid-operation
- **THEN** neither the containment nor the key list changes (all-or-nothing)

#### Scenario: Non-registry objects remain containment-only
- **WHEN** a player uses `拿`/`丟`/`給` on an Evennia Object whose key is not in `ITEM_REGISTRY`
- **THEN** the object moves as today and no `db.inventory` entry is created or removed
