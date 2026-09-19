## 1. Scoped growth_rate grammar

- [ ] 1.1 Add a `scope` field to `GrowthRateEffect` in `world/skills/effects.py` and rewrite the `growth_rate` parse branch to require four segments, validating `<stat>` is `practice`, `<multiplier>` is finite and non-negative, and `<scope>` is a key of `ELEMENT_REGISTRY`. Verify `growth_rate:practice:5:wind` parses with all three fields populated.
- [ ] 1.2 Make every other payload fail closed — the three-segment form, the retired `magic` stat, an unknown scope, a negative multiplier — each raising `ValueError`. Verify with one assertion per rejected form in `world/skills/tests/test_effects.py`, replacing the existing `growth_rate:practice:100` assertion rather than adding beside it.

## 2. The practice-growth consumer

- [ ] 2.1 Add the owned-skill growth factor to `world/rules/progression.py`: walk the actor's owned keys, read each resolvable skill's `parsed_effects`, and multiply every `GrowthRateEffect` whose `scope` equals the practised skill's element, using the existing `_is_elemental_magic()` predicate to decide whether the practised skill has a matching element at all. Verify a synthetic passive scoped to one element accelerates a synthetic spell of that element and leaves another element's spell at `1.0`.
- [ ] 2.2 Raise on a single skill declaring two `growth_rate` effects for the same scope, mirroring `_matching_multiplier()`'s duplicate guard, and multiply across separate owned skills. Verify both with synthetic skills.
- [ ] 2.3 Multiply the new factor into `_practice_growth_factors()` so both practice entry points inherit it, keeping the existing finite/non-negative validation as the last gate. Verify the owned-skill factor and an active `conferred_growth_rate` buff compose multiplicatively, and that a non-elemental skill takes `1.0`.

## 3. Registry data alignment

- [ ] 3.1 Re-author `reincarnation_boon_elosia` to `effects=["growth_rate:practice:5:wind"]` in `world/skills/registry.py`, confirming the scope choice from design D4 with the user first. Verify the registry imports and the row's `parsed_effects` carries the scoped dataclass.
- [ ] 3.2 Remove the inert `cost` from `flight` and `flash_step` so both declare an empty cost, and update the `flight.cost` assertion inside `test_rehomed_acquired_passives_keep_their_mechanics` to the corrected value. Verify `world.skills.tests.test_skill_registry` is green.

## 4. Traceability and gates

- [ ] 4.1 Update the `@covers_requirement` annotations on every test touched by the three modified requirements, taking the ids from `uv run --locked python -m tools.spec_traceability list` (renamed or reworded requirements take new ids).
- [ ] 4.2 Verify no new data-contract entry was needed: `uv run --locked python -m tools.test_data_lint check` passes with `tools/test_data_freeze.json` unchanged.
- [ ] 4.3 Run `openspec validate enhancement-catalog-alignment --strict` and the focused labels `world.skills.tests.test_effects`, `world.skills.tests.test_skill_registry` and `world.rules.tests.test_progression`, and confirm all are green.
