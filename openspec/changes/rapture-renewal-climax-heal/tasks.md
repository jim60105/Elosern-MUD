## 1. The passive

- [ ] 1.1 Add the `rapture_renewal` (歡愉回生) row to `world/skills/registry.py`: `SkillKind.PASSIVE`, `TargetSpec.NONE`, empty cost, `usable_out_of_combat=True`, `element="light"`, `category=SkillCategory.ENHANCEMENT`, `group=None`, no effect string (it is a qualifier row like `pain_to_pleasure`). Verify the registry imports and the row resolves.
- [ ] 1.2 Add the key to the `ENHANCEMENT` census set in `world/skills/tests/test_skill_registry.py`. Verify `world.skills.tests.test_skill_registry` is green, including the closed display-tag vocabulary assertion (the row declares `group is None`).

## 2. Phase-reaction self-recovery action

- [ ] 2.1 Extend the rule loader to recognize the self-recovery action in a phase rule's `then`, validating its fraction as a finite number in `(0, 1]` and raising fail-closed naming the rule id otherwise. Verify with synthetic rule tables covering an accepted fraction and each rejected form (zero, above one, non-finite, non-numeric).
- [ ] 2.2 Execute the action in `dispatch_phase_reaction`: compute `floor(max_hp × fraction)`, clamp to the HP gap, skip entirely when current HP is at or below zero or maximum HP is unreadable or not positive. Verify with synthetic entities that a deeply wounded holder gains the floored fraction, a lightly wounded holder rises to exactly maximum, and a downed holder gains nothing.
- [ ] 2.3 Verify the once-per-climax property falls out of the dispatcher rather than a flag: a synthetic holder entering the in-progress phase heals once, and a further pleasure gain while already in that phase heals nothing.

## 3. Rule and transaction integrity

- [ ] 3.1 Add the rule to `world/rules/rulebook/state_reactions.yaml` reusing the shipped `climax_in_progress_empowerment` condition shape — `field: climax_phase, equals: 進行中` plus `skill_qualified: rapture_renewal` — with the authored fraction from design D3. Do NOT author a `to_phase` key: it is absent from `_RECOGNIZED_WHEN_KEYS` and fails at load. Verify a qualified holder heals on entry and an unqualified holder does not.
- [ ] 3.2 Confirm every caller of `dispatch_phase_reaction` sits inside a face whose snapshot covers HP as well as buffs (design D6); extend the snapshot coverage where it does not. Verify that a settlement failing after the heal restores HP, climax phase and the pleasure gauge together.

## 4. Traceability and gates

- [ ] 4.1 Annotate the new tests with `@covers_requirement("damage-state-feedback::<normalized-name>")` for the added requirement, taking the id from `uv run --locked python -m tools.spec_traceability list`.
- [ ] 4.2 Verify `uv run --locked python -m tools.test_data_lint check` passes: the new behavior tests use synthetic entities and synthetic rule tables, and the only shipped-content edit is the existing census entry.
- [ ] 4.3 Run `openspec validate rapture-renewal-climax-heal --strict` and the focused labels `world.skills.tests.test_skill_registry` and `world.rules.tests.test_state_reactions`, and confirm both are green.
