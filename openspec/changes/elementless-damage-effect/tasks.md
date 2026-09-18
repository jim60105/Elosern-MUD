## 0. Prerequisites

- [ ] 0.1 Re-read the current damage parse branch (`world/skills/effects.py`, the `damage` prefix), the `DamageEffect` dataclass, and `SkillDef.__post_init__`'s existing validation loop, and confirm on the live tree that nothing reads `DamageEffect.element` (design.md Context lists the four near-miss consumers); if a consumer has appeared since authoring, STOP and re-decide before writing code.

## 1. Effect model

- [ ] 1.1 Widen `DamageEffect.element` to `str | None` and teach the `damage` parse branch that the element segment `none` yields `element=None`, leaving every other segment's parse byte-identical; verify by parsing `damage:none:physical`, `damage:none:magic` and one registry-element form in the new behavior module.
- [ ] 1.2 Add the one-directional consistency check to `SkillDef.__post_init__`: a definition declaring an element together with an elementless damage effect raises with the contradiction named. Do NOT add the reverse check (design.md D3). Verify with a constructed synthetic definition for each side — the contradiction raises, and a skill declaring no element with an element-bearing damage effect still constructs.
- [ ] 1.3 Convert `basic_attack` to the new form: `element=None` with `effects=["damage:none:physical"]`, changing no other field (key, label, zero cost, kind, target, category, faction constraint, `usable_out_of_combat`). Verify through a real resolution that it still deals physical damage off `atk_phys`, that its innate ownership and its monster-policy fallback are unaffected, and that the shipped registry imports with every entry's `parsed_effects` populated.
- [ ] 1.4 Move the two prose consumers off the converted row: the `_is_elemental_magic` docstring in `world/rules/progression.py` (its worked example becomes `light_sword_style`) and the skill-lineage requirement's parenthetical (carried by this change's delta). Leave `light_sword_style` itself untouched — its `light` is lore-true.

## 2. Behavioral evidence (synthetic only)

- [ ] 2.1 New module `world/skills/tests/test_elementless_damage.py` (`unittest.TestCase` plus the synthetic kit where a battlefield is needed), covering the delta's scenarios through real resolution, not dataclass field assertions: an elementless physical strike and an element-bearing twin of the same coefficient and policy settle to the same hp delta under the same fixed roll; the attacker's and target's declared affinities move neither result; an affinity-bearing actor and a neutral actor accrue the same practice on an elementless active skill; both construction outcomes of 1.2. No shipped key, label, cost or coefficient is named anywhere in the module (no data-contract test is added by this change).
- [ ] 2.2 Confirm no `.github/evennia-shards.json` edit is required — the `quests-skills-art-ai-lore` shard's package label `world.skills` already resolves every module under `world/skills/tests/` — and verify by running `tests.test_evennia_test_optimization_contract`.

## 3. Focused verification

```sh
uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests.test_elementless_damage world.skills.tests.test_skill_registry world.rules.tests.test_damage_state_feedback world.rules.tests.test_skill_lineage world.rules.tests.test_combat_view world.rules.tests.test_monster_behaviour_policy tests.test_evennia_test_optimization_contract
uv run --locked python -m tools.test_data_lint check
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.spec_traceability check
uv run --locked openspec validate elementless-damage-effect --strict
```

- [ ] 3.1 Run the focused labels and gates above and record the results. Pass `MUD_TEST_SETTINGS=1` through the tool environment, never as an inline shell prefix. No full suite, no browser run, no aggregate-coverage run.
- [ ] 3.2 Annotate the new behavior tests with the canonical requirement IDs from `uv run --locked python -m tools.spec_traceability list` at the separately authorized main-spec sync (the IDs read red until the delta syncs); no apply, archive, sync or merge happens in the proposal turn.
