# Tasks

Future implementation only. Begin after `reservoir-warden-variant` is merged. Follow design.md verbatim.

## 1. Executable content

- [x] 1.1 Add the species and variant rows (design D1, D2). Check: `world.lore.tests.test_monster_species_content` and `world.lore.tests.test_monster_visuals` pass.
- [x] 1.2 Add both skill rows and narration rows (design D3, D4) and the kit-contract freeform assertion correction (design D7 item 1). Check: `AuthoredMonsterKitContractTests` passes, magic tiers resolve for both skills, and `ActivationRecordTests` passes with `activation.json` unchanged.

## 2. Evidence and documentation

- [x] 2.1 Add `world/rules/tests/test_ember_bristle_boar_resource_skill.py` with shard and freeze entries (design D7 item 2). Check: it passes and `world.rules.tests.test_monster_composition_coverage` finds `warm_den_boar` as the new group's only representative.
- [x] 2.2 Add the `## 高階魔物` heading, boar section, overview row, ledger row and review section (design D5, D6); regenerate `content/map-reference-context.json`. Check: `world.lore.tests.test_bestiary_documentation` passes and `uv run --locked python -m tools.map_reference_context --check` exits 0.

## 3. Handoff

- [x] 3.1 Run the design.md Verification labels, `openspec validate ember-bristle-boar-species --strict` and `uv run --locked python -m tools.contract_gate`; record results and one non-blocking role observation in the review section. Check: all exit 0 and the new module has exactly one shard owner.
