# Proposal

## Why

The content-expansion design (§5, §6, §9) adds kits whose active skills carry no damage effect: a self film guard, a self agility improvement and an MP-funded self guard. The permanent legacy decision body only proposes affordable actives with a `damage:` effect (`world/rules/monster_behaviour.py::_owned_damage_skills`), so a variant whose effective decision mode is legacy would own such a skill and never use it. The design says an unusable claimed kit is not a completed delivery and that AI bindings are validated before publication. Nothing detects that binding today.

The check cannot be a loader rejection: the shipped legacy rollback (`monster-ai-rollout::legacy-mode-rollback-is-demonstrated`, exercised by `world/rules/tests/test_monster_ai_activation.py::RollbackTests`) loads the shipped rulebook with `variant_decision_mode: {}`, and a loader rejection would make that rollback impossible as soon as a support-kit variant is activated. The rule therefore applies to the shipped startup tuning as a production integrity check.

## What Changes

- Add a pure helper that reports every registered variant owning an active skill without a damage effect whose effective decision mode under a given tuning is not `utility`, using the same damage predicate the legacy body uses.
- A data-contract check asserts the helper reports nothing for the shipped startup tuning; synthetic tests establish the helper's behaviour. An edited rollback tuning still loads; its support-kit variants fall back to the innate attack while rolled back, which is documented.
- No shipped data changes; the startup tuning and its fingerprint are unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `monster-behaviour-profile`: add a requirement that the shipped startup tuning binds every owned support active to an effective utility decision mode, without blocking rollback tunings.

## Impact

Code: `world/rules/monster_behaviour.py` (shared `_has_damage_effect`, public `support_kit_mode_violations`). Tests: `world/rules/tests/test_monster_ai_tuning.py` (synthetic), `world/rules/tests/test_monster_ai_activation.py` (shipped check, existing data-contract module). Documentation: `docs/development/monster-ai.md`. Regenerated: `content/map-reference-context.json`.

Human review: none beyond code review. Pre-release: no compatibility path.

## Batch:

depends-on: none

Batch 1, parallel with `activity-group-formation` and `affirmative-monster-prose-guidelines` (disjoint files).

Code conflicts:
- `mudfilm-slime-species`, `wax-pouch-rat-species` and `reservoir-warden-variant` rely on this check and edit `world/rules/rulebook/monster_behaviour.yaml` and the activation evidence; they land after this change.
- `content/map-reference-context.json` conflicts mechanically with any parallel lore/rules change; rerun `uv run --locked python -m tools.map_reference_context` after rebase.
