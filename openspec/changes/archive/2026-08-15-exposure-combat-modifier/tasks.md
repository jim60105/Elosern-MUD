## 1. Rule table

- [x] 1.1 Add the `high_exposure_defense_penalty` row to `world/rules/rulebook/combat_modifiers.yaml`:
      `when: {field: exposure, gte: 高}`, `then: {defense: -15}` (a flat integer — **not** a
      percentage string; see design.md D-2 for why a percentage would crash `_adjusted_defense`).
      Place it immediately after `climax_in_progress_locks_actions` to keep the two sexual-field
      rows adjacent.
- [x] 1.1b Add the matching entry to `world/rules/rulebook/status_display.yaml`
      (`code: high_exposure_defense_penalty`, Traditional Chinese label in the `<level><trait>減損`
      shape, `severity: warning` like the two sibling sexual-field rows). Required by the
      import-time gate in `world/rules/status_display.py`, which fails closed unless every
      `combat_modifiers.yaml` rule ID has exactly one display entry (design.md D-5).
- [x] 1.2 Extend the three condition-context builders that feed `matched_combat_modifiers()` to
      expose `exposure` (design.md D-4 — required, not optional: without this the row from 1.1 can
      never match, because all three builders expose only `arousal`/`climax_phase` and
      `evaluate_condition()` treats an absent field as unsatisfied): import `EXPOSURE_LEVELS` from
      `world.lore.sexual_vocab`, add `("exposure", EXPOSURE_LEVELS)` to
      `build_no_create_condition_context()`'s field/levels loop and to
      `status_query.py::_sexual_condition_context()`'s loop, and add
      `context["exposure"] = sexual.exposure` to `_build_context()` alongside the existing
      `arousal`/`climax_phase` assignments. Do not touch `evaluate_condition()`, the adjustment
      machinery, or the buff/status presenter flow beyond the context builder.

## 2. Test

- [x] 2.1 Sync this change's delta spec into `openspec/specs/combat-modifier-table/spec.md` first
      (the ADDED requirement must be indexed before its id can be printed — per the
      `2026-08-09-npc-schedule-runtime` precedent, task 4.3: "`tools.spec_traceability list` after
      sync"; the change is additive and the archive-time re-sync is idempotent), then run
      `uv run --locked python -m tools.spec_traceability list` and confirm the new requirement id
      for `combat-modifier-table`'s added requirement
      ("high_exposure_defense_penalty prices raised exposure as a combat cost"). Do not guess the
      slug — use the literal id the tool prints.
- [x] 2.2 Add `test_rule_high_exposure_defense_penalty` to
      `world/rules/tests/test_combat_modifiers.py`, following `test_rule_high_arousal_agility_
      accuracy_penalty`'s shape immediately above it: construct an entity via the existing
      `_entity()` helper, set `entity.sexual.exposure.value = "高"`, assert
      `evaluate_combat_modifiers(entity) == {"defense": -15}`, then assert the row's condition
      evaluates `False` at `中等` and `True` at `極高` via `evaluate_condition(rule.when, ...)`
      against the loaded `RULES["high_exposure_defense_penalty"]`, matching the existing test's
      boundary-check pattern.
- [x] 2.3 Decorate the new test with `@covers_requirement(...)` using the literal id obtained in
      2.1 (and, if the boundary assertion also substantively exercises
      `rulebook-schema`'s opaque-then-clause requirement the way the arousal test's decorator does,
      the matching second id from the same `list` output).
- [x] 2.4 Add a second test, `test_rule_high_exposure_defense_penalty_below_threshold`, asserting
      `evaluate_combat_modifiers(entity)` returns no `defense` key when `exposure` is `低` — pinning
      the second delta-spec scenario (below-threshold).
- [x] 2.5 Add a third test asserting the row merges correctly alongside a buff-origin row (`poisoned`)
      and a skill-owned row (`defense_instinct`) in one `evaluate_combat_modifiers()` call, asserting
      the exact merged values `{"agility": "-10%", "defense": -10}` — pinning the third delta-spec
      scenario (merge-with-other-origins) and proving the flat-int merge actually combines rather
      than one value silently overwriting the other.
- [x] 2.6 **Required, not optional** — add `test_high_exposure_defense_penalty_applies_through_
      real_damage_resolution` (or extend an existing damage-resolution test), asserting that
      `world/rules/combat.py::_adjusted_defense(target)` returns `effective_value("defense") - 15`
      for a target whose `exposure` is at or above `高`, with no exception raised. This is the
      regression test that would have caught the original `"-20%"` draft's `TypeError` in
      `_adjusted_defense` (`float + str`) before it ever reached a live game — asserting only against
      `evaluate_combat_modifiers()`'s raw bundle (as 2.2 does) is not sufficient on its own, because
      that call never exercises the actual damage-resolution consumer.
- [x] 2.7 Add a no-create parity assertion: `evaluate_combat_modifiers_no_create(entity)` returns
      the same `{"defense": -15}` at `高` exposure (and nothing at `低`), pinning D-4's
      preview/resolution agreement — the stored `sexual_traits` dict is read without materializing
      the handler, so the stored ordinal must be picked up through the new
      `("exposure", EXPOSURE_LEVELS)` loop entry.
- [x] 2.8 Add `test_high_exposure_defense_penalty_appears_only_while_matched` to
      `world/rules/tests/test_status_query.py`, mirroring `test_sexual_threshold_appears_only_
      while_matched`: `build_status_read_model()` shows no `high_exposure_defense_penalty` entry
      below `高`, shows the entry with modifiers `{"defense": -15}`, warning severity, and the
      `status_display.yaml` label at `高`, and drops it again at `低` — pinning the delta spec's
      fifth scenario and the `webclient-status-presentation` matched-modifier contract (D-4).

## 3. Verification

- [x] 3.1 Run `uv run --locked python -m tools.spec_traceability check` and confirm the new
      requirement shows covered (its id is indexed because 2.1 synced it into the main spec), with
      no other requirement regressed.
- [x] 3.2 Run the focused test modules:
      `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
      world.rules.tests.test_combat_modifiers world.rules.tests.test_status_query
      world.rules.tests.test_rule_id_test_correspondence world.rules.tests.test_combat_modifiers_matched
      world.rules.tests.test_status_display`.
- [x] 3.3 Run `openspec validate exposure-combat-modifier --strict` and confirm it passes.
- [x] 3.4 Confirm the existing five `test_rule_<id>` correspondence check
      (`combat-modifier-table`'s "every rule ID has exactly one test" requirement's own mechanical
      check, wherever it lives in the test suite) still passes with the sixth rule and test added —
      this is the regression this proposal must not break.
