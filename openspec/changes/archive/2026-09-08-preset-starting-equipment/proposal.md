## Why

A preset can declare what a character carries but not what it wears. Activation
hard-writes the four-slot equipment map as all-`None`, so every shipped
signature character starts naked with its gear in the pack — `yuka_darknight`
begins holding two 影刃 and a set of ninja garb it is not wearing. The import
card has had an `equipment` field since `import-contract`; the preset registry
never gained one.

This is not merely cosmetic. Worn equipment feeds the combat modifier table,
the gauge ceilings (`sync_equipment_gauge_limits`), and the attached-buff set,
so an unequipped preset character is mechanically weaker than the card's
authored intent and than the equivalent imported NPC.

## What Changes

- `PlayerPreset` gains a keyword-only `starting_equipment` field: a tuple of item
  keys that MUST be a subset of `starting_items`.
- A load-time validator rejects a key absent from `starting_items`, a key whose
  `ItemDefinition.equipment_slot` is `None`, a repeated key, two keys claiming
  the same singleton slot, or more than `ACCESSORY_MAX_SLOTS` accessory keys.
  Each of these would otherwise be a silent authoring bug, because
  `toggle_equipment` toggles rather than equips and silently replaces a
  singleton occupant.
- Preset activation applies each declared key through
  `world/rules/equipment.py::toggle_equipment` — the sole equipment writer —
  after `inventory` is written (the toggle's preflight requires canonical
  ownership) and after traits are applied (the toggle recomputes gauge
  ceilings).
- A rejected toggle raises `CharacterCreationError` so the whole activation
  rolls back. A silently skipped item would leave a character mismatched with
  its own card.
- `_CREATION_ATTRIBUTE_KEYS` gains `buffs`, because the toggle applies
  attached-buff instances and the idmapper attribute cache is not
  transaction-aware: without the snapshot, a rolled-back activation would leave
  buff state readable in-process.
- Custom mode is unchanged: subrace basic kits are still granted unequipped.

No backward compatibility or data migration: the project has no released users.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `player-character-creation`: the preset starting-inventory requirement loses
  its "granted unequipped" clause for declared equipment and gains the
  registry field, its load-time validation, and the toggle-based application
  with its ordering and failure semantics.

## Impact

- `world/lore/player_presets.py` — the `starting_equipment` field and its
  validator, importing `EquipmentSlot`/`ACCESSORY_MAX_SLOTS` from
  `world/skills/equipment.py` (lore already depends on `world/skills/`).
- `world/rules/character_creation.py` — the activation write order and the
  toggle loop; `_CREATION_ATTRIBUTE_KEYS` gains `buffs`.
- `world/rules/equipment.py` — read-only; `toggle_equipment` is reused, not
  modified.
- `world/lore/tests/test_player_presets.py`,
  `world/rules/tests/test_character_creation.py`.
- Unaffected: the equipment command surface, the WebClient equipment panel,
  custom creation, and the import path.
