## 1. Rule table

- [ ] 1.1 Add the `high_exposure_defense_penalty` row to `world/rules/rulebook/combat_modifiers.yaml`:
      `when: {field: exposure, gte: 高}`, `then: {defense: -15}` (a flat integer — **not** a
      percentage string; see design.md D-2 for why a percentage would crash `_adjusted_defense`).
      Place it immediately after `climax_in_progress_locks_actions` to keep the two sexual-field
      rows adjacent.

## 2. Test

- [ ] 2.1 Run `uv run --locked python -m tools.spec_traceability list` and confirm the new
      requirement id for `combat-modifier-table`'s added requirement
      ("high_exposure_defense_penalty prices raised exposure as a combat cost"). Do not guess the
      slug — use the literal id the tool prints.
- [ ] 2.2 Add `test_rule_high_exposure_defense_penalty` to
      `world/rules/tests/test_combat_modifiers.py`, following `test_rule_high_arousal_agility_
      accuracy_penalty`'s shape immediately above it: construct an entity via the existing
      `_entity()` helper, set `entity.sexual.exposure.value = "高"`, assert
      `evaluate_combat_modifiers(entity) == {"defense": -15}`, then assert the row's condition
      evaluates `False` at `中等` and `True` at `極高` via `evaluate_condition(rule.when, ...)`
      against the loaded `RULES["high_exposure_defense_penalty"]`, matching the existing test's
      boundary-check pattern.
- [ ] 2.3 Decorate the new test with `@covers_requirement(...)` using the literal id obtained in
      2.1 (and, if the boundary assertion also substantively exercises
      `rulebook-schema`'s opaque-then-clause requirement the way the arousal test's decorator does,
      the matching second id from the same `list` output).
- [ ] 2.4 Add a second test, `test_rule_high_exposure_defense_penalty_below_threshold`, asserting
      `evaluate_combat_modifiers(entity)` returns no `defense` key when `exposure` is `低` — pinning
      the second delta-spec scenario (below-threshold).
- [ ] 2.5 Add a third test asserting the row merges correctly alongside a buff-origin row (`poisoned`)
      and a skill-owned row (`defense_instinct`) in one `evaluate_combat_modifiers()` call, asserting
      the exact merged values `{"agility": "-10%", "defense": -10}` — pinning the third delta-spec
      scenario (merge-with-other-origins) and proving the flat-int merge actually combines rather
      than one value silently overwriting the other.
- [ ] 2.6 **Required, not optional** — add `test_high_exposure_defense_penalty_applies_through_
      real_damage_resolution` (or extend an existing damage-resolution test), asserting that
      `world/rules/combat.py::_adjusted_defense(target)` returns `effective_value("defense") - 15`
      for a target whose `exposure` is at or above `高`, with no exception raised. This is the
      regression test that would have caught the original `"-20%"` draft's `TypeError` in
      `_adjusted_defense` (`float + str`) before it ever reached a live game — asserting only against
      `evaluate_combat_modifiers()`'s raw bundle (as 2.2 does) is not sufficient on its own, because
      that call never exercises the actual damage-resolution consumer.

## 3. Verification

- [ ] 3.1 Run `uv run --locked python -m tools.spec_traceability check` and confirm the new
      requirement shows covered, with no other requirement regressed.
- [ ] 3.2 Run the focused test module:
      `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
      world.rules.tests.test_combat_modifiers`.
- [ ] 3.3 Run `openspec validate exposure-combat-modifier --strict` and confirm it passes.
- [ ] 3.4 Confirm the existing five `test_rule_<id>` correspondence check
      (`combat-modifier-table`'s "every rule ID has exactly one test" requirement's own mechanical
      check, wherever it lives in the test suite) still passes with the sixth rule and test added —
      this is the regression this proposal must not break.
