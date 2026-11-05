# Tasks

Future implementation only. Follow design.md verbatim.

## 1. Helper and tests

- [x] 1.1 Add `_has_damage_effect` and route `_owned_damage_skills` through it (design D1). Check: `world.rules.tests.test_monster_behaviour_policy` passes unchanged under the focused command.
- [x] 1.2 Add `support_kit_mode_violations` (design D2) and `SupportKitModeTests` (design D3): legacy-bound support owner reported as `(variant, skill)`; utility override with intelligence → nothing; utility archetype → nothing; damage-only legacy owner → nothing. Annotate with the added requirement ID from the merged-tree traceability list. Check: the class passes.
- [x] 1.3 Add the shipped check and the rollback-loads assertion to `world/rules/tests/test_monster_ai_activation.py` (design D3). Check: `ActivationBindingTests` and `RollbackTests` pass and `docs/development/monster-ai-activation-evidence/activation.json` is unchanged.

## 2. Documentation and handoff

- [x] 2.1 Apply design D4 and regenerate `content/map-reference-context.json`. Check: `uv run --locked python -m tools.map_reference_context --check` exits 0.
- [x] 2.2 Run `openspec validate owned-kit-decision-coverage --strict` and `uv run --locked python -m tools.contract_gate`. Check: both exit 0 and no new test module or shard entry was added.
