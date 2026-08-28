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
- **WHEN** `world.rules.equipment.toggle_equipment()` equips one held registry weapon declared for
  `WEAPON_MAIN` and a second held registry weapon declared for `WEAPON_OFF`
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
The equipment contract SHALL treat `ACCESSORY` as a list-valued slot capped at exactly five items by `ACCESSORY_MAX_SLOTS`, distinct from the three single-item slots. The cap SHALL be read from the read-only equipment package by every deterministic writer and presenter rather than duplicated.

#### Scenario: Multiple accessories can be equipped up to the cap
- **WHEN** `world.rules.equipment.toggle_equipment()` equips five distinct held accessories
- **THEN** `slot_contents(EquipmentSlot.ACCESSORY)` returns those five item keys in deterministic equip order

#### Scenario: Equipping beyond the accessory cap is rejected
- **WHEN** an entity already holds five equipped accessories and equipment toggle is called with one more unequipped accessory
- **THEN** the call raises the named accessory-cap rejection and equipment remains byte-for-byte unchanged

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
For every item whose key exists in `ITEM_REGISTRY`, `actor.db.inventory` SHALL be the canonical inventory representation consumed by economy, quests, rewards, NPC transfers, item use, and the `背包` command; any registry item the player legitimately holds SHALL be present in this list. Shop economy and localized item transfer commands SHALL maintain contained Evennia Object mirrors. A consumable use SHALL remove one existing matching contained mirror together with its one-key delta; a key-only item granted through a key-only flow SHALL be consumed without fabricating a mirror. Reusable use and equipment toggling SHALL leave both key quantity and mirrors unchanged.

#### Scenario: Bought item appears in the canonical inventory
- **WHEN** a player buys an item from a shop
- **THEN** the item key is present in canonical inventory, visible in the bag, sellable, counted by ACQUIRE progress, and mirrored by a contained object

#### Scenario: Consuming a bought item removes its mirror
- **WHEN** a player successfully consumes a bought registry item with a contained mirror
- **THEN** one canonical key and exactly one matching contained object are removed in the same atomic settlement

#### Scenario: Consuming a key-only reward fabricates nothing
- **WHEN** a player successfully consumes a registry key granted without a contained mirror
- **THEN** one canonical key is removed and no object is created or unrelated mirror removed


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

### Requirement: Equipment toggle revalidates ownership and registry slot
The deterministic equipment service SHALL expose a side-effect-free preflight shared by presentation and settlement. It SHALL accept only an entity and item key, resolve the item's exact slot from immutable registry mechanics, verify current canonical inventory ownership, compute the exact replacement or removal, and return stable reasons without writing. Mutation SHALL repeat this preflight and atomically apply its immutable plan. Unknown, inspect-only, usable-only, malformed, or unheld items SHALL reject without mutation. The caller SHALL NOT supply a slot. Equipped items SHALL remain in canonical inventory.

#### Scenario: Client-supplied slot is unnecessary
- **WHEN** a held main-hand weapon key is toggled
- **THEN** its registry definition alone selects `WEAPON_MAIN` and the operation accepts no alternate slot input

#### Scenario: Unheld equipment is rejected
- **WHEN** an entity attempts to toggle registered equipment absent from canonical inventory
- **THEN** the operation rejects with `item_not_held` and equipment remains unchanged

#### Scenario: Presenter preflight writes nothing
- **WHEN** presentation checks whether a sixth accessory can be equipped
- **THEN** preflight returns `accessory_slots_full` while inventory and equipment remain byte-for-byte unchanged

Stored equipment SHALL normalize fail-closed before any decision or projection: the mapping must carry exactly the three singleton keys and an `accessories` sequence, each key may hold at most one occurrence across all slots, and every stored key must be registry-declared equipment whose declared slot matches where it is stored. Presentation SHALL derive visible equipped truth from this same normalization; a mapping that fails it is reported as malformed (section unavailable or `malformed_equipment` refusal) and SHALL NOT yield partially trusted equipped flags.

#### Scenario: Cross-slot duplicate fails closed everywhere
- **WHEN** stored equipment holds one key in both a singleton slot and the accessory list
- **THEN** the toggle rejects with `malformed_equipment` and the services inventory section reports `malformed_equipment` instead of publishing equipped flags

#### Scenario: Slot mismatch against the registry fails closed
- **WHEN** a stored key is registry-declared for a different slot than the one holding it, or is not registry equipment at all
- **THEN** normalization returns malformed and neither toggle nor presentation accepts the stored state

### Requirement: Singleton equipment toggles and replaces atomically
For `WEAPON_MAIN`, `WEAPON_OFF`, and `ARMOR`, toggling the item already in its declared slot SHALL clear that slot. Toggling a held unequipped item SHALL atomically assign it to its declared slot and replace any prior occupant; the prior item SHALL remain held and become unequipped. Planning or write failure SHALL restore the complete prior equipment mapping.

#### Scenario: Second click unequips a singleton
- **WHEN** the currently equipped main-hand item is toggled again
- **THEN** the main-hand slot becomes empty and the item remains in canonical inventory

#### Scenario: New singleton replaces the old one
- **WHEN** one main-hand item is equipped and a different held main-hand item is toggled
- **THEN** the new item occupies the slot, the old item is unequipped but still held, and no intermediate empty state is externally visible

#### Scenario: Replacement failure rolls back
- **WHEN** a fault occurs while committing a singleton replacement
- **THEN** the original occupant and complete equipment mapping are restored

### Requirement: Accessory toggle removes only the selected item
Accessory equipment SHALL contain at most one occurrence of a given item key. Toggling an equipped accessory SHALL remove that exact key regardless of its list position. Toggling an unequipped held accessory below the cap SHALL append it. At the cap, toggling an unequipped accessory SHALL reject without automatically replacing or removing any equipped accessory; the player must explicitly toggle an equipped accessory off first.

#### Scenario: Named accessory removal preserves later items
- **WHEN** accessories `[ring_a, ring_b, ring_c]` are equipped and `ring_b` is toggled
- **THEN** accessory storage becomes `[ring_a, ring_c]` and neither neighbor is removed

#### Scenario: Full accessories require manual removal
- **WHEN** five accessories are equipped and the player requests a sixth
- **THEN** the request is rejected, all five remain equipped, and no replacement is selected

#### Scenario: Duplicate equipped accessory is impossible
- **WHEN** an accessory item key is already equipped and its aggregated inventory tile is activated again
- **THEN** the existing occurrence is removed rather than appending a duplicate

### Requirement: Equipment toggling consumes neither a combat turn nor world time
A successful or rejected equipment toggle SHALL not advance the world clock or active combat round. The operation SHALL still publish canonical equipment and derived combat presentation so subsequent actions use the new equipment state.

#### Scenario: Combat equipment replacement is a free action
- **WHEN** a player in active combat replaces a held main-hand item
- **THEN** canonical equipment changes, but no participant acts and the combat round count and world clock remain unchanged
