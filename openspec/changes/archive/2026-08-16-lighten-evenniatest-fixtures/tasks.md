# Tasks: Lighten EvenniaTest Fixtures

## 1. Candidate inventory

- [x] 1.1 Run the read-only AST scan (from `plans/002-lighten-evenniatest-fixtures.md` Step 1, adapted to current paths) producing the candidate list; confirm the count is 200–210 classes
- [x] 1.2 Manual exclusion pass, recording each exclusion with its reason in a
      committed section of this change's `design.md` (appendix "Exclusion
      record"): drop `ExamStartTests` and `CombatSessionIdTests`
      (contract-pinned), classes with `EvenniaCommandTestMixin`, classes
      whose parent class uses mixin fixtures, classes whose code under test
      depends on `SESSION_HANDLER` or a default session, and any regex-missed
      fixture use; when in doubt, skip the class

## 2. Per-package conversion

- [x] 2.1 For each package (`world/rules`, `world/quests`, `world/skills`,
      `world/ai`, `world/maps`, `world/art`, `world/imports`, `world/lore`,
      `world/onboarding`, `world/prompts`, `world/tests`, `commands`,
      `server`, `typeclasses`, `web/webclient`): change each candidate
      class's base `EvenniaTest` → `EvenniaTestCase` (or `(Mixin,
      EvenniaTest)` → `(Mixin, EvenniaTestCase)`), fix the
      `evennia.utils.test_resources` import line (keep `EvenniaTest` only if
      a remaining class in the file still uses it), and run the package's
      tests:
      `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings
      test_settings.py --keepdb <package>`
- [x] 2.2 Revert (base + import) any class that fails after downgrade; record
      it in the change summary; expect 0–5 reverts

## 3. Contract pinning

- [x] 3.1 Create `tests/test_fixture_base_contract.py` (new top-level file):
      AST-based assertions that a representative sample of the newly
      downgraded classes (5–10 across packages, e.g. `CombatModifierTests`,
      `BuffIntegrationTests`, `SexualTransitionTests`, `CombatAdapterTests`)
      inherit exactly `EvenniaTestCase` (or `{Mixin, EvenniaTestCase}`);
      annotate with
      `covers_requirement("evennia-test-optimization::fixture-free-test-classes-use-the-lightest-base")`
      (verify the literal ID with `uv run --locked python -m
      tools.spec_traceability list` after the delta spec is written)
- [x] 3.2 Run `uv run --locked -m unittest discover -s tests -t .`

## 4. Full-suite and static verification

- [x] 4.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings
      test_settings.py --noinput --parallel 16 commands server typeclasses
      world web.webclient` — same discovered test count as before (3,104)
- [x] 4.2 Serial handoff profile once:
      `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings
      test_settings.py --keepdb commands server typeclasses world
      web.webclient`
- [x] 4.3 `uv run --locked python -m tools.spec_traceability check` and
      `git diff --check`

## 5. OpenSpec and handoff

- [x] 5.1 `openspec validate lighten-evenniatest-fixtures --strict`
- [x] 5.2 Sync the delta spec into
      `openspec/specs/evennia-test-optimization/spec.md`, archive the change,
      run `openspec validate --all --strict`, and update the change summary
      with the downgrade/revert counts and the exclusion record