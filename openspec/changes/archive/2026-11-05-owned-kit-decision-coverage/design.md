# Design

## Context

See proposal.md (Why). Current code at `1b1be7b8`:

- `world/rules/monster_behaviour.py::_owned_damage_skills(entity)` filters owned keys to `SkillKind.ACTIVE`, `can_use_skill`, affordable, and `any(effect.startswith("damage:") for effect in skill.effects)`. `_legacy_action` only proposes those skills, so an active without a damage effect is unreachable in legacy mode.
- The utility path (`world/rules/monster_ai/candidates.py::_is_candidate_skill`) already proposes `SELF_ONLY` support skills through the implicit binding, and the estimator values `defense`, `agility`, `agility_flat` and `accuracy` mounts as control.
- `MONSTER_AI_TUNING: MonsterAITuning` carries `behaviour_profiles`, `tier_defaults`, `variant_decision_mode`. `_validate_utility_coverage` resolves a variant's archetype as `variant.behaviour_profile_key` or `defaults[variant.threat_tier]` and its mode as `modes.get(key, profile.decision_mode)`.
- `world/rules/tests/test_monster_ai_activation.py` (data-contract module) holds `ActivationBindingTests` and `RollbackTests`; `_legacy_edited_tuning()` reloads the shipped rulebook with `variant_decision_mode = {}`.

## Goals / Non-Goals

**Goals:** detect, over the shipped startup tuning, a variant whose owned kit contains an active its effective mode can never select.

**Non-Goals:** rejecting any tuning at load time; changing the legacy body, utility scoring, archetypes, modes or intelligence; kit-reference validation (construction owns it in `world/rules/monster_individual.py::_validate_variant_kit_and_behaviour`); reachability of second single-target or area damage skills under legacy (reachable when earlier choices are unaffordable or by area preference).

## Decisions

### D1. Shared damage predicate

Add `def _has_damage_effect(skill: SkillDef) -> bool: return any(effect.startswith("damage:") for effect in skill.effects)` and use it inside `_owned_damage_skills` instead of the inline expression. Legacy behaviour is byte-identical.

### D2. Pure violation helper

Add and export:

```python
def support_kit_mode_violations(
    tuning: MonsterAITuning,
    variants: Mapping[str, Any] | None = None,
    skills: Mapping[str, SkillDef] | None = None,
) -> tuple[tuple[str, str], ...]:
    """(variant_key, skill_key) for each owned support active its mode cannot select."""
```

Defaults: `MONSTER_VARIANT_REGISTRY`, `SKILL_REGISTRY`. For each variant in key order: archetype key = `variant.behaviour_profile_key` if not `None` else `tuning.tier_defaults.get(variant.threat_tier)`; profile = `tuning.behaviour_profiles.get(archetype_key)` (skip the variant when `None`; that case is already a startup error elsewhere); mode = `tuning.variant_decision_mode.get(key, profile.decision_mode)`. For each `skill_key` in `variant.active_skill_keys` present in `skills` whose skill is `SkillKind.ACTIVE` and not `_has_damage_effect`, append `(key, skill_key)` when mode is not `DecisionMode.UTILITY`. Return a tuple sorted by `(variant_key, skill_key)`. It reads nothing else and writes nothing.

Alternative rejected: a loader rejection inside `_load_ai_tuning`. It would make `RollbackTests._legacy_edited_tuning()` raise once any support-kit variant is activated, breaking the shipped rollback contract.

### D3. Tests

- `world/rules/tests/test_monster_ai_tuning.py`: new class `SupportKitModeTests` using the module's synthetic `_tuning(...)`, `_VARIANT_ROWS` and `make_skill` from `world.tests.synthetic_data` (a `SELF_ONLY`/`TargetSpec.SELF` skill with effects `["self_buff_apply:t_support_shell"]`, and a damage skill with `["damage:none:physical"]`), passing `variants=` and `skills=` explicitly.
- `world/rules/tests/test_monster_ai_activation.py`: in `ActivationBindingTests` add `test_every_shipped_support_kit_binds_utility` asserting `support_kit_mode_violations(MONSTER_AI_TUNING) == ()`; in `RollbackTests` add an assertion that `_legacy_edited_tuning()` returns a tuning (no exception). The first-line data-contract tag and its `tools/test_data_freeze.json` reason stay verbatim.

### D4. Documentation

In `docs/development/monster-ai.md` section 決策模式與執行期解析 add one Traditional Chinese paragraph: legacy proposes only damage-bearing actives; a shipped variant owning a support active must bind utility, checked over the shipped tuning; a rollback to legacy remains loadable and the support active is idle while rolled back. Append one 變更紀錄 line.

## Risks / Trade-offs

- [Rolled-back support variant loses its guard] → documented degradation; rollback is an emergency seam and the variant keeps its innate attack.
- [Utility variants never choose flee] → existing `monster-flee-policy`; content changes that bind utility record it in their review section.

## Verification

Create `/tmp/mud-field-tests.env` with `MUD_TEST_SETTINGS=1`. Run `uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_monster_ai_tuning.SupportKitModeTests`, then `...test_monster_ai_activation.ActivationBindingTests` and `...test_monster_ai_activation.RollbackTests`. Canonical IDs from `uv run --locked python -m tools.spec_traceability list --repo-root <merged tree>`. Handoff: `uv run --locked python -m tools.map_reference_context --check`, `openspec validate owned-kit-decision-coverage --strict`, `uv run --locked python -m tools.contract_gate`.
