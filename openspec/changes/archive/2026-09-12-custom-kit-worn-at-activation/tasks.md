# Tasks: custom kit worn at activation

## 1. Validator hardening (load-time wearability)

- [x] 1.1 Extract the wearable-set rules (duplicate keys, `equipment_slot is None`, two keys
      claiming one singleton slot, more accessories than `ACCESSORY_MAX_SLOTS`) from
      `world/lore/player_presets.py::_validate_preset_starting_equipment` into one shared
      module-level helper in `world/lore/starting_kits.py` (design D3) reading
      `ACCESSORY_MAX_SLOTS`/`EquipmentSlot` from `world.skills.equipment` and taking an owner
      label for stable error messages; verify by importing both modules cleanly
  (`uv run --locked python -c "import world.lore.player_presets"`).
- [x] 1.2 Make `_validate_starting_kit` (`world/lore/starting_kits.py`) call the helper after its
      entry-shape/unknown-key/equipment-only/quantity checks, folding its inline `seen` duplicate
      check into the helper — the four-rule checklist for a kit is now: every key is equipment,
      no duplicate keys, no singleton-slot collision, at most `ACCESSORY_MAX_SLOTS` accessories.
      The helper must reproduce the existing stable message shapes with the owner label
      substituted, so the existing kit cases still match by regex (notably
      `declares duplicate item` in
      `test_kit_validation_rejects_malformed_unknown_and_non_equipment_entries`). Verify:
      importing `world.lore.starting_kits` still passes on all 15 shipped kits (audit
      fact: all are collision-clean, including Change 1's 濱海民/平原民/山地民).
- [x] 1.3 Refactor `_validate_preset_starting_equipment` to keep its malformed-entry guards and
      the subset-of-`starting_items` rule while delegating duplicates/equipment/collision/cap to
      the same helper; verify observable preset behavior is unchanged — the existing
      `test_starting_equipment_validation_rejects_the_five_invalid_declarations` in
      `world/lore/tests/test_player_presets.py` still passes without edits.

## 2. Wear the kit at custom activation

- [x] 2.1 Replace `starting_equipment: tuple[str, ...] = ()` at
      `world/rules/character_creation.py:645-646` with the derivation from the resolved kit
      (`tuple(key for key, _ in kit.items)`, moved after the guarded kit lookup), and delete the
      retired "preset-starting-equipment non-goal" comment (the non-goal is reversed); verify by
      reading the custom branch — no behavior code beyond the derivation changed.
- [x] 2.2 Confirm snapshot-set completeness for the custom path rather than assuming it:
      `_CREATION_ATTRIBUTE_KEYS` (`character_creation.py:30-48`) names `equipment` and `buffs`,
      and gauge ceilings ride `snapshot_traits` — verify by reading the tuple; if either key is
      absent, add it as part of this change.
- [x] 2.3 Confirm the shared toggle loop (~line 733), the `write_observer("starting_equipment")`
      stage, and `toggle_equipment` are all UNCHANGED —
      preset and custom activation keep one implementation of wearing, buff attachment, and
      gauge-ceiling recomputation; verify with `git diff` showing no edits to that region.

## 3. Tests (canonical Evennia runner, design §8)

- [x] 3.1 Replace `test_custom_activation_leaves_every_equipment_slot_empty` in
      `world/rules/tests/test_character_creation.py` (it pins the reversed behavior) with a test
      for the modified scenario "A custom character wakes with its subrace kit": a custom
      activation wears its whole kit — every item in the slot its `ItemDefinition.equipment_slot`
      resolves to, its attached buffs present, and gauge ceilings reflecting the worn set — under
      the existing slug
      `player-character-creation::custom-activation-grants-the-chosen-subrace-s-basic-starting-kit`
      (scenario-under-existing-requirement; no new IDs — confirm via
      `uv run --locked python -m tools.spec_traceability list`).
      Because `toggle_equipment` toggles and custom kits exercise it for the first time, assert
      buffs are attached exactly once per item for a multi-item kit (design D2, idempotence).
- [x] 3.2 Add the load-failure test to `world/lore/tests/test_starting_kits.py`: a deliberately
      colliding kit (two `weapon_main` keys) and a sixth-accessory kit each raise when
      `_validate_starting_kit` runs at registry load (the scenario is pinned in terms of the
      import raising), under the existing slug for the `:308`
      requirement's new "A colliding or accessory-overflowing kit fails at registry load"
      scenario.
- [x] 3.3 Verify the existing custom-kit tests whose assertions stay true —
      `test_custom_activation_grants_each_subrace_starting_kit` (inventory equality) — still pass
      with the kit worn (worn items remain in inventory); adjust only if an assertion observed the
      emptiness itself.
- [x] 3.4 Run the canonical suite plus traceability and data lint, all green:
      `MUD_TEST_SETTINGS=1 uv run --locked python -m evennia test --settings test_settings.py
      --noinput world.lore world.rules`,
      `uv run --locked python -m tools.spec_traceability check`,
      `uv run --locked python -m tools.test_data_lint check`.
      No test modules are added or renamed, so `.github/evennia-shards.json` needs no update
      (`world.rules` and `world.lore` are already registered shards).

## 4. Docs sweep

- [x] 4.1 Grep `docs/` and openspec-adjacent docs for "entirely unequipped", "unequipped", and the
      preset-starting-equipment non-goal wording; update any player/developer doc that states
      custom characters start unequipped (survey at proposal time found the claim only in the
      design doc itself — a historical record — and `docs/development/adding-player-presets.md`,
      which describes only preset behavior and stays correct; verify the sweep reports no other
      hit needing an edit).
- [x] 4.2 State in the change notes that the command surface does not change, so
      `docs/game/commands.md` and `docs/game/command-reference.md` need no update (equipment is
      written by activation through the existing machinery; no command gains or loses behavior).
