## MODIFIED Requirements

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

### Requirement: ACCESSORY is a bounded multi-item slot
The equipment contract SHALL treat `ACCESSORY` as a list-valued slot capped at exactly five items by `ACCESSORY_MAX_SLOTS`, distinct from the three single-item slots. The cap SHALL be read from the read-only equipment package by every deterministic writer and presenter rather than duplicated.

#### Scenario: Multiple accessories can be equipped up to the cap
- **WHEN** `world.rules.equipment.toggle_equipment()` equips five distinct held accessories
- **THEN** `slot_contents(EquipmentSlot.ACCESSORY)` returns those five item keys in deterministic equip order

#### Scenario: Equipping beyond the accessory cap is rejected
- **WHEN** an entity already holds five equipped accessories and equipment toggle is called with one more unequipped accessory
- **THEN** the call raises the named accessory-cap rejection and equipment remains byte-for-byte unchanged

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

## ADDED Requirements

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
