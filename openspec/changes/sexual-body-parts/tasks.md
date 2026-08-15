## 1. Vocabulary constants

- [ ] 1.1 In `world/lore/sexual_vocab.py`, add `BODY_PARTS = ("口唇", "頸項", "耳朵", "乳房",
      "腰腹", "臀部", "大腿", "足部", "私處", "後庭")`.
- [ ] 1.2 Add `GENERIC_BODY_PART = "軀體"`.
- [ ] 1.3 Add both new names to the module's `__all__` list.
- [ ] 1.4 Update the module docstring: keep the existing statement naming `CHARACTER_SCHEMA_V1` as
      the current consumer of the six ordered-level tuples and a future `sexual-state` change as
      their expected future consumer; add a new statement that `BODY_PARTS` and `GENERIC_BODY_PART`
      have no current consumer and name the future `sexual-act-registry` and `sexual-act-effects`
      capabilities as their expected first consumers.
- [ ] 1.5 Add a module-level `assert GENERIC_BODY_PART not in BODY_PARTS` immediately after both
      constants are defined, so the non-membership invariant fails at import time — not only when
      the test suite happens to run — if a future edit to `BODY_PARTS` ever adds `"軀體"`.

## 2. Tests

- [ ] 2.1 In `world/lore/tests/test_sexual_vocab.py`, add a test asserting `BODY_PARTS` equals the
      exact 10-tuple in order.
- [ ] 2.2 Add a test asserting `GENERIC_BODY_PART` equals `"軀體"`.
- [ ] 2.3 Add a test asserting `GENERIC_BODY_PART not in BODY_PARTS`.
- [ ] 2.4 Confirm the existing "no import of a rules or imports module" test still covers the file
      as a whole (no per-symbol exemption needed — the constants introduce no new import).
- [ ] 2.5 Confirm every existing assertion for the six original tuples is unchanged and still
      passes.
- [ ] 2.6 Add a new test that reads `sexual_vocab.__doc__` directly and asserts it contains the
      required content for the expanded second requirement: mentions of `BODY_PARTS` and
      `GENERIC_BODY_PART`, a statement that they have no current consumer, and both
      `sexual-act-registry` and `sexual-act-effects` named as expected future consumers. This test,
      not the value-assertion test in 2.1, is the one that carries the second requirement's
      `covers_requirement` annotation (see 3.1) — a value assertion does not verify docstring
      content, and the traceability checker only validates that an annotation names a real
      requirement, not that the annotated test actually exercises it.

## 3. Traceability and validation

- [ ] 3.1 Run `uv run --locked python -m tools.spec_traceability list` to get the current requirement
      IDs, then:
      - Update the existing `covers_requirement` decorator on
        `test_all_vocabularies_match_the_design_in_order` (currently
        `"sexual-vocabulary::world-lore-sexual-vocab-py-defines-the-six-ordered-level-name-vocabularies-from-design-doc-s6-4"`)
        to the **new** ID produced by Requirement 1's renamed heading in the delta spec — renaming
        the heading changes its slug, so the old string will fail as an unknown requirement ID once
        the delta lands. Confirm the new ID with the `list` output rather than hand-deriving it.
      - Add a `covers_requirement` decorator for Requirement 1's two new scenarios
        (`BODY_PARTS matches the documented set in order`, `GENERIC_BODY_PART is not a member of
        BODY_PARTS`) to the tests added in 2.1–2.3 — the same requirement ID as the updated
        decorator above, since both new scenarios belong to the (single, renamed) first
        requirement.
      - Add a `covers_requirement` decorator for the second requirement ("module documents itself
        as the single canonical source for every vocabulary it defines") to the docstring-content
        test added in 2.6.
- [ ] 3.2 Run `uv run --locked python -m tools.spec_traceability check` and confirm zero unknown-ID
      and zero uncovered-requirement errors.
- [ ] 3.3 Run `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
      world.lore`.
- [ ] 3.4 Run `openspec validate sexual-body-parts --strict`.
