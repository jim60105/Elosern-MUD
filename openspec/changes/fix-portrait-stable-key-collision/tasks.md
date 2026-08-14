## 1. Shared digit-only reservation rule

- [ ] 1.1 Add `DIGITS_ONLY_KEY_PATTERN = r"[0-9]+"` and `is_reserved_player_stable_key(key)` (a `re.fullmatch` predicate) to `world/art/subjects.py` beside the existing shared constants, with a docstring stating that the digit-only region of the `portrait:character:` keyspace is reserved for player pks (`str(pk)`), per design D1
- [ ] 1.2 Add unit tests for the predicate in `world/art/tests/test_subjects.py`: digit-only strings are reserved, while non-digit keys, alphanumeric keys, empty strings, and Unicode-digit strings are not reserved

## 2. Import contract (schema + validator)

- [ ] 2.1 Extend `_ENTITY_KEY_RULES["pattern"]` in `world/imports/schema.py` with a digit-only negative lookahead derived from the shared `DIGITS_ONLY_KEY_PATTERN` (preserving the absolute `\A`/`\Z` anchors), so character and world-entry keys are both covered, per design D2
- [ ] 2.2 Mirror the rejection in `world/imports/validate.py::_check_entity_key_contract` using `is_reserved_player_stable_key`, with a rejection naming the reserved digit-only region (e.g. "digit-only entity keys are reserved for player characters")
- [ ] 2.3 Add schema-level tests in `world/imports/tests/test_schema.py`: digit-only character keys and digit-only world-entry keys fail structural validation; alphanumeric keys with digits (e.g. `bandit_02`) pass; annotate with `covers_requirement("import-schema::imported-entity-keys-use-a-safe-character-set")`
- [ ] 2.4 Add validator-level tests in `world/imports/tests/test_validation_semantics.py`: a batch with a digit-only key rejects and no entity is instantiated; annotate with `covers_requirement("import-validation::key-charset-is-checked-at-import-validation")`

## 3. Quest characterization contract

- [ ] 3.1 Add the digit-only rejection to the `portrait.stable_key` branch of `world/quests/characterization.py::characterize_errors` using the shared predicate, so the scenario-director guardrail and the compile boundary both reject digit-only keys through the one helper, per design D2
- [ ] 3.2 Add tests in `world/quests/tests/test_characterization.py` covering the new rejection (digit-only `stable_key` rejects; alphanumeric keys still pass), and verify `tests/test_characterization_boundary.py` stays green (no inline rule copy in either layer)
- [ ] 3.3 Add a blueprint-level test in `world/ai/tests/test_scenario_director.py` (guardrail rejection of a digit-only `portrait.stable_key`) and a compile-level test in `world/quests/tests/test_compile.py` (digit-only stable key rejects at compile), and confirm the template pool (`world/ai/director_templates.py`) still validates; annotate with `covers_requirement("blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization")` on the tests that substantively verify the modified requirement
- [ ] 3.4 Confirm existing behavior tests stay green: player activation tests (`world/rules/tests/test_character_creation.py:365-417`, `commands/tests/test_character_creation.py`) keep asserting `str(pk)` policies, and art tests that use digit-only keys as player-style keys (`world/art/tests/test_subjects.py:170-189`, `world/art/tests/test_presenter.py:113-143`) still pass

## 4. Repository-wide consistency and verification

- [ ] 4.1 Grep the repository for digit-only entity keys or portrait stable keys in fixtures, examples, and browser seeds (expected: none; the browser seed already uses the `browser-` prefix); add any fixture to this change only if it exists and update it
- [ ] 4.2 Note the dev-database cleanup in the change report: delete any pre-existing `art:portrait:character:<digits>` Script in a dev DB so the player's next ensure recreates the record from the player's own description (no migration, no code path — design D5)
- [ ] 4.3 Run `uv run --locked python -m compileall -q world typeclasses commands server`, the affected package tests (art, imports, quests, ai, rules creation), `uv run --locked python -m tools.spec_traceability check`, and the full Evennia suite before handoff
