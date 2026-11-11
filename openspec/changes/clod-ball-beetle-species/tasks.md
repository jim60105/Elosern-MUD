# Tasks

Begin after `ore-nest-griffin-species` is merged. Follow design.md verbatim. Every zh-TW string is copied from design.md and never recomposed.

## 0. Environment

- [x] 0.1 Create the test environment file with `printf 'MUD_TEST_SETTINGS=1\n' > /tmp/mud-species.env`. Check: the file holds that single line.

## 1. Executable content

- [x] 1.1 Append the species and variant rows (design D1, D2). Check: `uv run --locked python -c "from world.lore.monster_species import MONSTER_VARIANT_REGISTRY"` exits 0; `world.lore.tests.test_monster_species_content` and `world.lore.tests.test_monster_visuals` pass.
- [x] 1.2 Append the skill rows and the docstring sentence (design D3), plus the rulebook and narration rows (design D4) and the D7 test. Check: `AuthoredMonsterKitContractTests`, `world.skills.tests.test_narration_catalog`, `world.rules.tests.test_monster_composition_coverage` and `world.rules.tests.test_sway_whistle_sparrow_resource_skill` pass, and so does `CombatModifierTests`; the narration rows sit in data_earth.py.
- [x] 1.3 Run the activation tests, expect `ActivationRecordTests` and `RollbackTests` to fail on the fingerprint comparison, and re-fingerprint with design D5 steps 1–4 (design D5). Check: `ActivationRecordTests`, `ActivationBindingTests` and `RollbackTests` pass, and `activated` and `activation_bindings` are unchanged.

## 2. Documentation

- [ ] 2.1 Add the overview row, the bestiary section and the ledger row (design D6), plus the sixth-batch approval notes (design D6a). Check: `world.lore.tests.test_bestiary_documentation` passes, and the section names no skill key, buff id or resource field.
- [ ] 2.2 Add the developer review section (design D8) and regenerate `content/map-reference-context.json`. Check: `uv run --locked python -m tools.map_reference_context --check` exits 0.

## 3. Handoff

- [ ] 3.1 Run every label in design.md Verification, `uv run --locked python -m tools.contract_gate --change clod-ball-beetle-species` and `openspec validate clod-ball-beetle-species --strict`. Check: all exit 0, and `.github/evennia-shards.json`, `tools/test_data_lint_seed.json` and `tools/test_data_freeze.json` are unchanged.
