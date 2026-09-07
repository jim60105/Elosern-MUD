## 1. Registry field

- [x] 1.1 Add keyword-only `starting_equipment: tuple[str, ...] = ()` to `PlayerPreset`
- [x] 1.2 Write `_validate_preset_starting_equipment(registry)` rejecting: a key absent from `starting_items`, a key whose `ItemDefinition.equipment_slot` is `None`, a repeated key, two keys resolving to the same singleton slot, and more than `ACCESSORY_MAX_SLOTS` accessory keys
- [x] 1.3 Import `EquipmentSlot` and `ACCESSORY_MAX_SLOTS` from `world/skills/equipment.py` (lore already depends on `world/skills/`; still no `world.rules` import)
- [x] 1.4 Register the validator with the existing validators at module bottom

## 2. Activation

- [x] 2.1 Add `"buffs"` to `_CREATION_ATTRIBUTE_KEYS` in `world/rules/character_creation.py`
- [x] 2.2 Inside the activation `transaction.atomic()`, after `_apply_trait_config` and after the `inventory` attribute write, loop over `preset.starting_equipment` calling `toggle_equipment(character, item_key)`
- [x] 2.3 Raise `CharacterCreationError` naming the item key and `result.reason` when a toggle returns `outcome == "rejected"`, so the whole activation rolls back
- [x] 2.4 Confirm the toggles run before `finalize_player_portrait` and before the draft clear, keeping the existing write ordering otherwise intact
- [x] 2.5 Confirm custom mode never enters the loop

## 3. Tests

- [x] 3.1 `world/lore/tests/test_player_presets.py`: the validator rejects each of the five invalid declarations (not carried, not equipment, duplicate, singleton-slot collision, accessory overflow)
- [x] 3.2 `world/rules/tests/test_character_creation.py`: a preset declaring `starting_equipment` activates with every declared key in its slot
- [x] 3.3 `world/rules/tests/test_character_creation.py`: the attached buffs for the declared items are present after activation
- [x] 3.4 `world/rules/tests/test_character_creation.py`: gauge ceilings reflect the worn set, computed from the final trait values
- [x] 3.5 `world/rules/tests/test_character_creation.py`: an equippable starting item not listed in `starting_equipment` stays in the pack and occupies no slot
- [x] 3.6 `world/rules/tests/test_character_creation.py`: a rejected toggle raises and rolls back, leaving the character pending
- [x] 3.7 `world/rules/tests/test_character_creation.py`: a failure injected **after** the toggles restores `equipment`, `buffs`, and the gauge ceilings to their pre-activation values in the in-process cache
- [x] 3.8 `world/rules/tests/test_character_creation.py`: custom activation leaves every equipment slot empty
- [x] 3.9 Annotate the tests with `covers_requirement` using IDs from `uv run --locked python -m tools.spec_traceability list`

## 4. Verification

- [x] 4.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.lore.tests.test_player_presets world.rules.tests.test_character_creation`
- [x] 4.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_equipment` confirming the equipment writer is untouched
- [x] 4.3 `uv run --locked python -m tools.spec_traceability check`
- [x] 4.4 `openspec validate preset-starting-equipment --strict`
