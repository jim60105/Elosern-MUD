## ADDED Requirements

### Requirement: EquipmentSlot defines four slots sized to the sample cards' own equipment shapes
`world/skills/equipment.py` SHALL define an `EquipmentSlot` `StrEnum` with exactly the members
`WEAPON_MAIN`, `WEAPON_OFF`, `ARMOR`, and `ACCESSORY`, borrowing evadventure's wield-location slot
structure (design doc §4: reference only, not its d20 formulas).

#### Scenario: EquipmentSlot has exactly the four documented members
- **WHEN** `EquipmentSlot` is inspected
- **THEN** it has exactly the members `WEAPON_MAIN`, `WEAPON_OFF`, `ARMOR`, `ACCESSORY` and no others

#### Scenario: A dual-wielded weapon pair occupies both weapon slots at once
- **WHEN** an `EquipmentHandler` equips one weapon into `WEAPON_MAIN` and a second into `WEAPON_OFF`
- **THEN** `slot_contents(EquipmentSlot.WEAPON_MAIN)` and `slot_contents(EquipmentSlot.WEAPON_OFF)`
  each return their own distinct item key, and neither slot's assignment affects the other

### Requirement: EquipmentHandler is mounted directly as entity.equipment
`LivingEntity` SHALL expose `entity.equipment` as an `EquipmentHandler` instance bound to that
entity — per design doc §5.2, `equipment` **is** the `EquipmentHandler`, the same relationship
`traits` has to `TraitHandler` — replacing change 3's placeholder `AttributeProperty`. The handler
SHALL read and write the private `entity.db.equipment` attribute, holding the raw dict change 4's
loader writes there (`entity.db.equipment = record["equipment"]`).

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
- **WHEN** code assigns `entity.db.equipment = {...}` directly, the way change 4's
  `instantiate_character()` is expected to (once adjusted per this change's design.md D-10)
- **THEN** the assignment succeeds with no error, and `entity.equipment` subsequently reflects the
  newly assigned data

### Requirement: ACCESSORY is a bounded multi-item slot
`EquipmentHandler` SHALL treat `ACCESSORY` as a list-valued slot capped at `ACCESSORY_MAX_SLOTS`
items, distinct from the three single-item slots.

#### Scenario: Multiple accessories can be equipped up to the cap
- **WHEN** an `EquipmentHandler` equips accessories up to `ACCESSORY_MAX_SLOTS`
- **THEN** `slot_contents(EquipmentSlot.ACCESSORY)` returns a list of exactly that many item keys

#### Scenario: Equipping beyond the accessory cap is rejected
- **WHEN** an `EquipmentHandler` already holds `ACCESSORY_MAX_SLOTS` accessories and `.equip()` is
  called with one more
- **THEN** the call raises rather than silently exceeding the cap

### Requirement: Inventory remains a flat list of item-key strings, compatible with entity.db.inventory
`world/skills/equipment.py` SHALL define `add_item(entity, item_key)`, `remove_item(entity,
item_key)`, and `list_items(entity)` operating directly on `entity.db.inventory` — the same raw
attribute change 4's loader already writes (`entity.db.inventory = record["inventory"]`) with no
additional seam declaration required.

#### Scenario: add_item appends to the existing raw inventory list
- **WHEN** `entity.db.inventory` is `["healing_potion"]` and `add_item(entity, "iron_ore")` is called
- **THEN** `entity.db.inventory` becomes `["healing_potion", "iron_ore"]`

#### Scenario: add_item tolerates an entity with no inventory yet
- **WHEN** `entity.db.inventory` is `None` and `add_item(entity, "healing_potion")` is called
- **THEN** `entity.db.inventory` becomes `["healing_potion"]` rather than raising

#### Scenario: remove_item removes exactly one matching entry
- **WHEN** `entity.db.inventory` is `["healing_potion", "iron_ore"]` and `remove_item(entity,
  "iron_ore")` is called
- **THEN** `entity.db.inventory` becomes `["healing_potion"]`

#### Scenario: list_items reflects change 4's already-populated inventory verbatim
- **WHEN** an entity was constructed by change 4's `instantiate_character()` with a non-empty
  `inventory` array
- **THEN** `list_items(entity)` returns that same array's contents, unmodified
