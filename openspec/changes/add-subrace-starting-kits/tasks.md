# Tasks: add-subrace-starting-kits

## 1. Item catalog expansion

- [x] 1.1 Add the six new basic equipment `ItemDefinition` entries from design D3 (`wooden_club`, `gilded_saber`, `great_axe`, `ashen_scimitar`, `steel_fang_dagger`, `prism_charm`) to `ITEM_REGISTRY` in `world/lore/items.py`, each carrying an `equipment_slot`, reusing existing `PRICE_TABLE` keys (`mundane_weapon` / `magic_accessory`), closed presentation vocabularies, common/uncommon rarity, and single-line Traditional Chinese summaries
- [x] 1.2 Extend the expected key set of the EXISTING closed-catalog contract test `world/lore/tests/test_items.py::test_every_registered_item_resolves_complete_metadata` and the existing catalog-size pin `len(ITEM_REGISTRY) == 42` in `world/rules/tests/test_guild_config.py` (both are maintenance of pre-existing closed-catalog contracts, not new data tests) and verify with `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.lore.tests.test_items world.rules.tests.test_guild_config`

## 2. Subrace starting-kit lore registry

- [x] 2.1 Create `world/lore/starting_kits.py`: frozen `SubraceStartingKit` dataclass (`subrace_key`, `items: tuple[tuple[str, int], ...]`, `inventory_list()` mirroring `PlayerPreset.inventory_list`), `SUBRACE_STARTING_KIT_REGISTRY` keyed by subrace with the design D3 kit table, and a load-time validator mirroring `_validate_preset_starting_items` that additionally requires total coverage and equipment-only contents — rejecting: a registered subrace with no kit, a kit for an unknown subrace, a kit whose `subrace_key` mismatches its registry key, an entry that is not a `SubraceStartingKit` or whose `items` is not a tuple, an empty kit, an item key absent from `ITEM_REGISTRY` (non-string keys rejected as invalid before the membership lookup so the failure type is stable), an item whose definition has no `equipment_slot`, a duplicate item key in one kit, and a non-positive or boolean quantity. Split the validator into entry-level `_validate_starting_kit(registry_key, kit)` and `_validate_starting_kit_coverage(registry)` so tests can drive broken shapes directly
- [x] 2.2 Add `world/lore/tests/test_starting_kits.py` with `unittest.TestCase` tests, all registry-driven and free of hard-coded subrace→item mappings: kit keys exactly cover `SUBRACE_REGISTRY`; every kit is non-empty and every kit item resolves in `ITEM_REGISTRY` with a non-null `equipment_slot`; the same item key appearing in multiple kits is valid; and the validator raises on each rejection shape (build broken mappings and call the validator directly, following the `world/lore/tests/test_player_presets.py` precedent). Do NOT add `covers_requirement` annotations yet — the two new requirement IDs do not exist in the main-spec index until the delta is synced (design D4 traceability ordering)

## 3. Custom activation grants the subrace kit

- [ ] 3.1 In `world/rules/character_creation.py::activate_player_character`, resolve `inventory_value` for custom mode from `SUBRACE_STARTING_KIT_REGISTRY[validated.subrace].inventory_list()` before the transaction opens, raising `CharacterCreationError` (not `KeyError`) on an unresolvable kit; leave preset mode reading `PLAYER_PRESET_REGISTRY[preset_key].inventory_list()` untouched
- [ ] 3.2 Update `world/rules/tests/test_character_creation.py::test_activation_persists_identity_traits_and_empty_mechanical_state`: replace the `inventory == []` assertion with equality against the `human_commoner` kit's `inventory_list()` read from the registry (no hard-coded item list)
- [ ] 3.3 Add behavior tests to `world/rules/tests/test_character_creation.py`, unannotated for now (see 5.1): every registered subrace custom-activates to exactly its kit's expanded list in one test using `subTest` per subrace with contents read from the registry; preset activation is unchanged by subrace kits; and the existing write-failure rollback coverage additionally asserts the pending character's `inventory` was never granted. The imported-character clause is already covered by `world/imports/tests/test_loader_trait_values.py` (`entity.db.inventory == record["inventory"]`) — do not add a duplicate import test

## 4. Verification gates

- [ ] 4.1 Run the focused Evennia labels: `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb world.lore world.rules.tests.test_character_creation world.imports` and confirm green
- [ ] 4.2 Run `uv run --locked python -m tools.spec_traceability check` (must stay green with NO annotations for the not-yet-synced requirement IDs) and `uv run --locked python -m compileall -q world typeclasses commands server`, and confirm both are clean
- [ ] 4.3 Run `openspec validate add-subrace-starting-kits --strict` and confirm the change artifacts stay mutually consistent (no player command surface change, so `docs/game/commands.md` is intentionally untouched)

## 5. Post-sync traceability (execute during the archive/sync workflow, after the delta is merged into `openspec/specs/`)

- [ ] 5.1 After the delta requirements exist in the main spec, obtain their exact IDs with `uv run --locked python -m tools.spec_traceability list` and add literal-ID `covers_requirement` annotations to the tests from tasks 2.2 (kit-coverage requirement) and 3.3 (custom-activation requirement)
- [ ] 5.2 Re-run `uv run --locked python -m tools.spec_traceability check` and the focused Evennia labels from 4.1 and confirm both are green with the annotations in place
