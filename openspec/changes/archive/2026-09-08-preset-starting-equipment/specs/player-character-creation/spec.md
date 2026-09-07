# player-character-creation delta

## MODIFIED Requirements

### Requirement: Preset activation grants the preset's declared starting inventory
Preset mode SHALL additionally grant the selected preset's declared starting inventory: the
activated character's `inventory` SHALL equal the preset's `(item_key, quantity)` pairs flattened
into the flat repeated-key list shape in declared order, written inside the same all-or-nothing
activation transaction. A preset's declared inventory SHALL NOT be overridden by the chosen
subrace's basic starting kit. Custom mode SHALL instead start with the chosen subrace's basic
starting kit as defined by the `Custom activation grants the chosen subrace's basic starting kit`
requirement. A starting kit SHALL reference only keys that exist in `ITEM_REGISTRY`, with a
positive integer quantity per key and no repeated key — an invalid kit SHALL fail at registry
load, never at player activation.

A preset MAY additionally declare `starting_equipment`, a tuple of item keys that SHALL be a subset
of its `starting_items`. Every declared key SHALL be worn on the activated character, applied
through `world/rules/equipment.py::toggle_equipment` — the sole equipment writer — so the worn set,
the gauge ceilings recomputed by `sync_equipment_gauge_limits`, and the attached-buff instances are
all produced by the existing capability rather than a parallel implementation. The toggles SHALL run
inside the same all-or-nothing activation transaction, after the trait config is applied and after
`inventory` is written, because the toggle preflight requires canonical inventory ownership and the
ceiling recomputation reads the final trait values. A toggle that returns a rejected outcome SHALL
raise and roll the whole activation back, naming the item key and the stable rejection reason; a
rejected item SHALL NOT be silently skipped. Because the toggle writes `db.buffs`, `buffs` SHALL
join the activation attribute snapshot set, so a rolled-back activation leaves no readable
equipment, buff, or gauge-ceiling residue in the in-process attribute cache.

A `starting_equipment` declaration SHALL fail at registry load, never at player activation, when it
names a key absent from `starting_items`, a key whose `ItemDefinition.equipment_slot` is `None`,
the same key twice, two keys claiming the same singleton slot, or more accessory keys than
`ACCESSORY_MAX_SLOTS`. Each of these is an authoring mistake with no useful runtime meaning:
`toggle_equipment` toggles rather than equips, and it silently replaces a singleton occupant.

Items a preset carries but does not declare as `starting_equipment` are granted unequipped, and
custom-mode subrace kits are granted entirely unequipped; the player equips those through the
ordinary equipment surface.

#### Scenario: A preset activation grants the declared starting items
- **WHEN** a pending player activates a shipped preset that declares `starting_items`
- **THEN** the activated character's `db.inventory` equals the declared pairs flattened by
  quantity in declared order, written atomically with the rest of the activation state, and the
  preset's subrace basic starting kit grants nothing extra

#### Scenario: Declared starting equipment is worn at activation
- **WHEN** a pending player activates a preset declaring `starting_equipment`
- **THEN** the activated character's `db.equipment` names every declared key in its resolved slot, the corresponding attached buffs are present, and the gauge ceilings reflect the worn set

#### Scenario: Undeclared items stay in the pack
- **WHEN** a preset declares `starting_items` containing an equippable key that is not in `starting_equipment`
- **THEN** that key remains in `db.inventory` and no equipment slot names it

#### Scenario: A rejected toggle rolls activation back
- **WHEN** a declared equipment toggle returns a rejected outcome during activation
- **THEN** activation raises naming the item key and the stable reason, rolls back entirely, and the character remains pending

#### Scenario: A failed activation leaves no equipment or buff residue
- **WHEN** a write failure is injected after the equipment toggles of a preset activation
- **THEN** `equipment`, `buffs`, and the gauge ceilings all read back at their pre-activation values, and the character remains pending

#### Scenario: Custom activation starts with its subrace kit
- **WHEN** a pending player completes the custom creation flow with a registered subrace
- **THEN** the activated character's `db.inventory` equals that subrace's basic starting kit
  flattened by quantity, never the empty list, and every equipment slot is empty

#### Scenario: A preset kit with a registry-invalid item is rejected at load
- **WHEN** a preset declares an item key absent from `ITEM_REGISTRY`, a non-positive or
  non-integer quantity, or the same item key twice
- **THEN** importing `world.lore.player_presets` raises, so the invalid kit can never reach a
  player's activation

#### Scenario: An invalid starting-equipment declaration is rejected at load
- **WHEN** a preset declares a `starting_equipment` key absent from its `starting_items`, a key that is not equipment, the same key twice, two keys claiming one singleton slot, or more accessories than `ACCESSORY_MAX_SLOTS`
- **THEN** importing `world.lore.player_presets` raises, so the invalid loadout can never reach a player's activation
