## Context

`EvenniaTest` (via `EvenniaTestMixin.setUp()`) creates a full world per test
method; `EvenniaTestCase` is Django's `TestCase` with Evennia's cache-flush
teardown and no mixin fixtures. The conversion pattern is already proven in
this repository: the `web.webclient` presenter/action classes were moved
from `EvenniaTest` to `EvenniaTestCase` with class-level sync
(`docs/development/evennia-test-performance.md`, "Fixture-heavy presenter
tests"). The repo guide (`docs/development/evennia-testing-guide.md`)
documents the fixture hierarchy: `unittest.TestCase` → `EvenniaTestCase` →
`EvenniaTest` → `EvenniaCommandTest`.

Candidate pool (AST scan at `69aabe6`): 207 `EvenniaTest` classes whose class
body references none of the ten mixin fixture names — 1,202 test methods.
Largest: `SexualTransitionTests` (52), `CombatModifierTests` (43),
`BuffIntegrationTests` (42), `ProgressionTests` + `ElementMasteryGateTests`
(22+22), `RuntimeLifecycleTests` (21), `ShopTradeTests` (18),
`AffinityWriterTests` (16), `ActionPreviewTests` (16), `CombatAdapterTests`
(15), and ~180 classes with 1–14 methods.

## Goals / Non-Goals

**Goals:**
- Convert every candidate class to `EvenniaTestCase` (or `(Mixin,
  EvenniaTestCase)`) with zero behavior change: same tests, same assertions,
  same annotations, same transaction isolation.
- Verify per package during the conversion and revert (with a report) any
  class that needs the mixin after all.
- Pin the new boundary in the existing contract test.

**Non-Goals:**
- Merging test methods into subTests (rejected: the repo has a documented
  history of parallel/shuffle isolation flakes; the downgrade achieves the
  cost win without isolation risk).
- Converting fixture-using `EvenniaTest` classes (115 classes, 858 methods)
  or the contract-pinned `ExamStartTests`/`CombatSessionIdTests`.
- `setUpTestData()` adoption (zero current usages; fixture-free classes don't
  need it after downgrade, and fixture users rely on per-test transaction
  rollback).
- Moving classes between files (sibling changes split long test files).

## Decisions

- **AST-driven candidate generation**: a read-only script scans `test_*.py`
  files (excluding `.venv`, `.claude`, `web/tests/browser`), keeps classes
  whose base list contains `EvenniaTest` but not `EvenniaTestCase` or
  `EvenniaCommandTestMixin`, and whose class body has no `self.<fixture>`
  reference. The output list is manually reviewed — including the class's
  base chain, isolation mixins, and whether the code under test touches
  `SESSION_HANDLER` or a default session — and every exclusion is recorded
  with its reason in the change's design.md appendix so a re-run can
  reproduce the same sets.
- **Base rewrite rule**: `EvenniaTest` → `EvenniaTestCase`; `(X,
  EvenniaTest)` → `(X, EvenniaTestCase)` preserving mixin order. The existing
  `(RegistryIsolationMixin, unittest.TestCase)` pattern in
  `world/ai/tests/test_scenario_director.py:718` confirms mixin-first order.
- **Import hygiene**: `from evennia.utils.test_resources import
  EvenniaTestCase` added; `EvenniaTest` kept on the import line only when
  another class in the same file still uses it.
- **Revert-not-fix policy**: any failing class is reverted to `EvenniaTest`
  and reported; never "fixed" by adding fixture usage or weakening
  assertions.
- **Contract pinning**: extend the `expectations` dict in
  `test_pure_candidates_use_unittest_while_integration_fixture_remains` with
  5–10 representative downgraded classes across packages (its AST-based
  assertion already handles multi-mixin bases).

## Risks / Trade-offs

- **Hidden mixin dependency**: a candidate might transitively need the mixin
  (e.g. code under test touches `SESSION_HANDLER` or the default session).
  Mitigation: per-package verification during conversion; the revert policy
  bounds the damage; expected reversion count 0–5.
- **Import fallout**: files mixing downgraded and fixture-using classes keep
  both imports; the compileall/test gates catch mistakes.
- **Contract test churn**: only additive (new expectations entries).
- **Large diff surface**: ~200 classes across ~100 files is noisy but
  mechanical; per-package commits keep review tractable.
