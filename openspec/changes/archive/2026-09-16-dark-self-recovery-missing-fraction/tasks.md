## Batch order (dark wave — integration contract in ../dark-spell-catalog/design.md)

0. Predecessors (ALL archived and merged): the light+water waves shipped the effect/policy/handler surfaces this extension rides (`_handle_self_heal`, `_heal_magnitude`, `_restored_amount`, the freeform scale table, the per-effect potency validation). INDEPENDENT of `dark-erosion-leech` (no shared files — batch order does not constrain this change). `dark-spell-catalog` lands AFTER this change (it authors `void_annihilation`/`abyssal_apotheosis` over the new grammar).

## 1. Grammar + typed effect

- [x] 1.1 Inspect `parse_effect`'s `self_heal` branch, `SelfHealEffect`, `_handle_self_heal`, `_heal_magnitude`, `_restored_amount`/`_apply_heal`, the registry coefficient whitelist (`SkillDef.__post_init__`) and `_FREEFORM_SCALABLE_PREFIXES` before editing; confirm no missing-fraction support exists anywhere on the self-heal path (verdict baseline).
- [x] 1.2 Widen `SelfHealEffect` with a validated closed basis (`"stat"` default; `"missing_fraction"` carrying a finite fraction in (0, 1]) and parse `self_heal:missing_fraction:<f>` accordingly; the bare form keeps returning the defaulted instance so every shipped row and the existing arity-boundary tests (`self_heal:`, `self_heal:single`) are untouched; every other payload keeps raising.
- [x] 1.3 Narrow the registry potency-coefficient whitelist so a non-identity coefficient composes only with the stat basis (plus `damage`/`heal` unchanged); a `missing_fraction` occurrence with coefficient ≠ 1.0 raises at construction.

## 2. Handler magnitude leg

- [x] 2.1 In `_handle_self_heal`, branch on the parsed basis: missing-fraction computes `round((max_hp − current_hp) × fraction)` from the caster's stored gauge at staging time, scaled by `scale` through the existing `scaled_magnitude` leg, WITHOUT `heal_gain` amplification; the stat basis keeps `_heal_magnitude` verbatim. Both bases flow through the unchanged `_restored_amount` staging clamp and `_apply_heal` commit guard (alive-only, max-clamped). No dark/element key read; no `heal` (target-audience) change.

## 3. Behavioral evidence and integration

- [x] 3.1 Behavior tests in the existing registered modules (extend `world/rules/tests/test_heal_effect_handler.py` handler-level coverage and its settlement class; add parse-arity cases to `world/skills/tests/test_effects.py`): fraction reads the caster's gap not the target's; exact rounded amount at known gaps; max clamp; dead-caster zero stage/commit (no revival); scale composition matching the existing scaled-heal contract; heal_gain absent on the missing-fraction amount and present on the stat amount (pinning the D3 decision); construction rejects the coefficient pairing; every malformed payload raises. Bare-form suite stays green unchanged (regression pin). Tests must fail on target-gap reads, clamp escapes, heal_gain folding, revival.
- [x] 3.2 If any NEW module is created (not expected — prefer the registered ones), register it in exactly one shard in `.github/evennia-shards.json`; otherwise verify the ownership-contract test still passes.
- [x] 3.3 Run the focused labels below; `tools.observability_lint check`; `tools.test_data_lint check`; `tools.spec_traceability check`; `openspec validate dark-self-recovery-missing-fraction --strict`. Canonical IDs via `uv run --locked python -m tools.spec_traceability list` at the separately authorized main-sync; annotate exactly the tests establishing the superseded `skill-effect-model`/`heal-effect-handler` IDs.

### Focused invocation

```sh
uv run --locked evennia test --settings test_settings.py --keepdb world.rules.tests.test_heal_effect_handler world.skills.tests.test_effects world.rules.tests.test_freeform_casting world.rules.tests.test_effect_potency
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.test_data_lint check
uv run --locked python -m tools.spec_traceability check
uv run --locked openspec validate dark-self-recovery-missing-fraction --strict
```

Pass `MUD_TEST_SETTINGS=1` through the tool environment, never a shell prefix. No new test module is planned; existing registered modules carry the proof. No full local suite/browser/aggregate-coverage run; no command above ten minutes. No apply, archive, main-spec sync or merge in the proposal turn.
