# Tasks

Future implementation only. Begin after `sticky-palm-goblin-species` and `owned-kit-decision-coverage` are merged. Follow design.md verbatim.

## 1. Executable content

- [ ] 1.1 Add the `reservoir_warden` row (design D1). Check: `world.lore.tests.test_monster_species_content` passes, including construction and reload of every shipped variant.
- [ ] 1.2 Add `reservoir_guard`, its buff, rule, status codes, narration row and `test_rule_reservoir_film_defense` (design D2, D3). Check: `AuthoredMonsterKitContractTests` (magic tier resolves for this elemental MP skill) and `CombatModifierTests` pass.
- [ ] 1.3 Add the AI binding and re-fingerprint the activation evidence (design D4). Check: `ActivationRecordTests`, `ActivationBindingTests` (support-kit check empty) and `RollbackTests` pass.

## 2. Evidence and publication

- [ ] 2.1 Add `world/rules/tests/test_reservoir_warden_resource_skill.py` with shard and freeze entries (design D6). Check: it passes, `world.rules.tests.test_crocodile_resource_skill` still passes, and `world.rules.tests.test_monster_composition_coverage` finds exactly one representative for the new group.
- [ ] 2.2 Apply the affirmative crocodile publication, bestiary block, variant passages, overview row, ledger update and review section (design D5); regenerate `content/map-reference-context.json`. Check: `world.lore.tests.test_bestiary_documentation` passes, the section names no key or field, and `uv run --locked python -m tools.map_reference_context --check` exits 0.

## 3. Handoff

- [ ] 3.1 Run the design.md Verification labels, `openspec validate reservoir-warden-variant --strict` and `uv run --locked python -m tools.contract_gate`; record results and the non-blocking role observation. Check: all exit 0 and the new module has exactly one shard owner.
