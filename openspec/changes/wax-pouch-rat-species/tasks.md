# Tasks

Future implementation only. Begin after `mudfilm-slime-species` is merged. Follow design.md verbatim.

## 1. Executable content

- [x] 1.1 Add the species and variant rows (design D1, D2). Check: `world.lore.tests.test_monster_species_content` and `world.lore.tests.test_monster_visuals` pass.
- [x] 1.2 Add the skill, buff, rule, status codes, narration row and `test_rule_wax_slip_agility_flat` (design D3, D4, D7). Check: `AuthoredMonsterKitContractTests`, `CombatModifierTests` and `world.rules.tests.test_monster_composition_coverage` pass with no new representative declaration.
- [x] 1.4 Add `SelfSupportGroupMemberTests` (design D7). Check: it passes for every derived group member, including `wax_cache_forager`.
- [x] 1.3 Add the AI binding and re-fingerprint the activation evidence (design D5). Check: `ActivationRecordTests`, `ActivationBindingTests`, `RollbackTests` and `world.rules.tests.test_mudfilm_slime_resource_skill` pass.

## 2. Documentation

- [x] 2.1 Add the bestiary overview row and section, the ledger row and the review section (design D6); regenerate `content/map-reference-context.json`. Check: `world.lore.tests.test_bestiary_documentation` passes and `uv run --locked python -m tools.map_reference_context --check` exits 0.

## 3. Handoff

- [x] 3.1 Run the design.md Verification labels, `openspec validate wax-pouch-rat-species --strict` and `uv run --locked python -m tools.contract_gate`; record results in the review section. Check: all exit 0 and `.github/evennia-shards.json` is unchanged.
