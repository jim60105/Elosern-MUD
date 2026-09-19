## 0. Prerequisites

- [ ] 0.1 Re-read the live `parse_effect` `damage` branch, `_parse_damage_effect`, and both its call
  sites (`_handle_damage` in `world/rules/combat.py`, `_damage_school` in
  `world/rules/monster_behaviour.py`), and re-run the repo-wide grep for every `damage:` string — both
  literal (`grep -rhoE '"damage:[^"]*"' --include="*.py" .`) and dynamically constructed
  (`grep -rn 'f"damage:\|"damage:".*+\|damage:.*\.format(' --include="*.py" .`) — to confirm no
  fixture added since authoring uses a school outside `{"physical", "magic"}` in a position expected
  to construct successfully (the dynamic-construction sweep matters because a literal-only grep cannot
  see an interpolated school segment; design.md's Risks section found several f-string-built damage
  effects today, all with a hardcoded school literal and only the element interpolated — re-verify
  that still holds). If a fixture with a dynamic, non-closed-set school has appeared, STOP and
  re-decide before writing code.

## 1. Unify the parser

- [ ] 1.1 Add the school-membership check to `parse_effect`'s `damage` branch
  (`world/skills/effects.py`): reject a school outside `{"physical", "magic"}` with `ValueError`,
  leaving every other segment's parse byte-identical. Verify by parsing `damage:fire:physical`,
  `damage:fire:magic`, `damage:none:physical` and `damage:fire:sonic` (the last raises) in the
  existing `world/skills/tests/test_effects.py`.
- [ ] 1.2 Re-implement `_parse_damage_effect` in `world/rules/combat.py` as a thin wrapper: call
  `parse_effect`, assert `isinstance(parsed, DamageEffect)`, raise if a non-`None` `parsed.element` is
  not a key in `ELEMENT_REGISTRY`, and return the `DamageEffect` (not a tuple). Import `DamageEffect`
  from `world.skills.effects` (already imports `parse_effect` and `ELEMENT_REGISTRY`). Verify with
  `inspect.getsource` on the function containing no `.split(":")` or `.partition(":")` call of its
  own.
- [ ] 1.3 Update `_handle_damage`'s one call site (`_, school = _parse_damage_effect(effect_id)` →
  `school = _parse_damage_effect(effect_id).school`). Verify a real cast of a `damage:*:physical` and
  a `damage:*:magic` synthetic skill still reads `atk_phys`/`magic_power` respectively, through
  `ActionResolver.resolve()`.
- [ ] 1.4 Update `_damage_school`'s one call site in `world/rules/monster_behaviour.py`
  (`_, school = combat._parse_damage_effect(effect)` → `school = combat._parse_damage_effect(effect).school`).
  Verify monster skill-selection scoring by school is unchanged through the existing
  `test_monster_behaviour_selection` suite.

## 2. Behavioral evidence (synthetic only)

- [ ] 2.1 Extend `world/skills/tests/test_effects.py`'s `test_malformed_damage_raises` with a
  same-shape-but-invalid-school case (e.g. `"damage:fire:sonic"`) asserting `ValueError` at
  `parse_effect`, and add one assertion (in the same file or a new small test) that a `SkillDef`
  declaring such an effect fails at construction, not only at parse — matching the "fails at import,
  not at use" contract every other malformed prefix already gets.
- [ ] 2.2 Add a small architectural test (`world/rules/tests/`, colocated with existing `combat.py`
  behavior tests) asserting `inspect.getsource` of `world.rules.combat._parse_damage_effect` contains
  no `split(":")` or `partition(":")` token — pinning the "exactly one parser" requirement the same
  way `test_progression.py::test_magic_xp_engine_is_absent_from_progression_source` pins an absent-API
  contract today.
- [ ] 2.3 Add one real-resolution regression test resolving a synthetic elementless
  (`damage:none:physical`) skill through `ActionResolver.resolve()` and asserting `outcome ==
  "success"` — pinning the thin wrapper's `None`-legality behavior (design.md D1/D4) so a future edit
  to the cast-time wrapper cannot silently regress it. No shipped key, label, cost, or coefficient is
  named anywhere in this module.

## 3. Focused verification

```sh
uv run --locked evennia test --settings test_settings.py --keepdb world.skills.tests.test_effects world.skills.tests.test_skill_registry world.rules.tests.test_combat_view world.rules.tests.test_conditional_damage world.rules.tests.test_monster_behaviour_selection world.rules.tests.test_monster_behaviour_policy world.skills.tests.test_elementless_damage
uv run --locked python -m tools.test_data_lint check
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.spec_traceability check
uv run --locked openspec validate unify-damage-effect-parsers --strict
```

- [ ] 3.1 Run the focused labels and gates above and record the results. Pass `MUD_TEST_SETTINGS=1`
  through the tool environment, never as an inline shell prefix. No full suite, no browser run, no
  aggregate-coverage run.
- [ ] 3.2 Annotate the new tests with the canonical requirement IDs from
  `uv run --locked python -m tools.spec_traceability list` at the separately authorized main-spec
  sync (the IDs read red until the delta syncs); no apply, archive, sync, or merge happens in the
  proposal turn.
