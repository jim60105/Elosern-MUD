## Why

207 test classes (1,202 test methods) inherit `EvenniaTest` but never use any
of its mixin fixtures (`self.char1`, `self.char2`, `self.room1`,
`self.room2`, `self.account`, `self.session`, `self.obj1`, `self.obj2`,
`self.exit`, `self.script1`) — each of those methods pays the full
`EvenniaTestMixin.setUp()` (accounts, rooms, objects, characters, scripts,
session, cache flush) and an extra cache flush in teardown for a fixture it
never touches. Example: `CombatModifierTests` (43 methods) creates its own
`PlayerCharacter` inside every test (`world/rules/tests/test_combat_modifiers.py:29-39`).
`EvenniaTestCase` provides the same transaction-isolation semantics with
Evennia's cache flushing but skips the mixin fixture setup. Converting these
classes removes wasted setup/teardown from every local and CI run — the
"reduce setup cost for small tests" goal, achieved by removing the cost
rather than merging tests and risking isolation.

## What Changes

- ~200 test classes across all non-browser packages change their base from
  `EvenniaTest` to `EvenniaTestCase` (classes with an isolation mixin become
  `(Mixin, EvenniaTestCase)`; mixin order unchanged). Import lines updated;
  `EvenniaTest` imports removed where no remaining class in the file uses it.
- Excluded classes (not touched): `ExamStartTests` and `CombatSessionIdTests`
  (pinned to `EvenniaTest` by the existing contract test), any class using
  `EvenniaCommandTestMixin`, any class whose parent class uses the mixin
  fixtures, and the 115 fixture-using classes (858 methods) that legitimately
  need `EvenniaTest`.
- The contract pin for the new boundary lives in a new top-level test file
  `tests/test_fixture_base_contract.py` (AST assertions over a sample of the
  downgraded classes), annotated with the new requirement ID; the existing
  contract test `test_pure_candidates_use_unittest_while_integration_fixture_remains`
  (`tests/test_evennia_test_optimization_contract.py`) keeps covering the
  modified "Fixture optimization preserves the tested boundary" requirement.
- Per-package verification during conversion; any class that fails after
  downgrade is reverted (expected 0–5) and reported — never "fixed" by adding
  fixture usage. Every exclusion is recorded with its reason for
  reproducibility.

No backward-compatibility or migration work is needed — the project has no
released users.

## Capabilities

### Modified Capabilities

- `evennia-test-optimization`: a new requirement "Fixture-free test classes
  use the lightest base" is added, and "Fixture optimization preserves the
  tested boundary" is extended so the downgraded sample is part of the
  pinned contract.

## Impact

- Test files under `world/`, `commands/`, `server/`, `typeclasses/`,
  `web/webclient/` — base-class and import-line changes only; no method
  bodies, names, or annotations change.
- `tests/test_evennia_test_optimization_contract.py` — extended pinned
  expectations.
- No production code, no player-facing commands, no test semantics change.
- Follow-up `split-rules-and-skills-test-files` moves some of these classes
  into new files; the bases land first.
