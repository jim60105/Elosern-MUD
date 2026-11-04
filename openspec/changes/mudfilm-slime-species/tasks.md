# Tasks

Future implementation only. Begin after `owned-kit-decision-coverage` and `affirmative-monster-prose-guidelines` are merged. Follow design.md verbatim; literals are authored once in their executable declarations.

## 1. Executable content

- [ ] 1.1 Add the species and variant rows (design D1, D2) and the roster-free docstring/comment wording (D8 first paragraph). Check: `world.lore.tests.test_monster_species_content` and `world.lore.tests.test_monster_visuals` pass under the focused command; importing `world.lore.monster_species` raises nothing.
- [ ] 1.2 Add the skill row, buff, modifier rule, status codes and narration row (design D3, D4) and the correspondence test `test_rule_mudfilm_shell_defense` plus the kit-contract tier assertion correction (design D7 items 1–2). Check: `AuthoredMonsterKitContractTests`, `CombatModifierTests` and `world.skills.tests` narration catalog tests pass; `construct_species_individual("mudfilm_slime", "mudbank_dweller")` succeeds in the representative smoke.
- [ ] 1.3 Add the AI binding and re-fingerprint the activation evidence (design D5). Check: `ActivationRecordTests`, `ActivationBindingTests` and `RollbackTests` pass, and `support_kit_mode_violations(MONSTER_AI_TUNING)` is empty in `ActivationBindingTests`.

## 2. Evidence and documentation

- [ ] 2.1 Add `world/rules/tests/test_mudfilm_slime_resource_skill.py` with its shard and freeze-ledger entries (design D7 item 3). Check: the module passes and `world.rules.tests.test_monster_composition_coverage` passes with `mudbank_dweller` as the new group's committed representative.
- [ ] 2.2 Add the bestiary header note, overview row and current section, and the ledger entry (design D6). Check: `world.lore.tests.test_bestiary_documentation` passes; the section names no skill key, buff id or resource field.
- [ ] 2.3 Record the non-gating expansion and role observations listed in design D8. Check: the review section lists them with the command used.
- [ ] 2.4 Create `docs/development/monster-content-expansion.md` with the slime section (design D8) and regenerate `content/map-reference-context.json`. Check: `uv run --locked python -m tools.map_reference_context --check` exits 0.

## 3. Handoff

- [ ] 3.1 Run every focused label listed in design.md Verification, `openspec validate mudfilm-slime-species --strict` and `uv run --locked python -m tools.contract_gate`; record commands and results in the review section. Check: all exit 0, the new module has exactly one shard owner, and no unexecuted check is reported as passed.
