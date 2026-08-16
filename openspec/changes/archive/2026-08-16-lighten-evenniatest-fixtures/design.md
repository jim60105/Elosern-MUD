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
- **Contract pinning**: the new boundary is pinned in a new top-level file
  `tests/test_fixture_base_contract.py` with AST-based assertions over 5–10
  representative downgraded classes across packages (e.g. `CombatModifierTests`,
  `BuffIntegrationTests`, `SexualTransitionTests`, `CombatAdapterTests`),
  annotated with the new requirement ID. The existing
  `test_pure_candidates_use_unittest_while_integration_fixture_remains`
  expectations dict stays unchanged and keeps covering the modified
  "Fixture optimization preserves the tested boundary" requirement.

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

## Appendix: Exclusion record

Re-run of the AST scan at the change's implementation HEAD (204 candidate
classes with test methods, 1,174 methods) and the manual dependency review:

**Contract-pinned to `EvenniaTest` (kept):**
- `CombatSessionIdTests` (`world/rules/tests/test_combat_session.py`) — pinned
  by `test_evennia_test_optimization_contract.py`.
- `ExamStartTests` (`world/rules/tests/test_guild_exams.py`) — pinned by
  `test_evennia_test_optimization_contract.py` as
  `{ExamRegistryIsolation, EvenniaTest}`.

**Reverted after per-package verification (16, above the expected 0–5):**
- `TurnInAtomicityTests`, `HelpEntryTests`, `FullJourneyTests`
  (`world/rules/tests/test_onboarding_journey.py`) — their shared parent
  `OnboardingJourneyMixin.setUp` uses the mixin fixture `self.account`
  (`self.account.at_post_create_character(self.player)`); downgrading the
  child classes to `EvenniaTestCase` removed the account fixture and the setup
  raised `AttributeError`.
- `InnateSkillTests` (`world/rules/tests/test_combat_session.py`),
  `ConferralActionTests` (`world/rules/tests/test_conferral_action.py`),
  `EffectivePowerIntegrationTests` (`world/rules/tests/test_effective_power.py`),
  `AcquireDefinitionTests`, `AcquireProgressTests`, `ImportNonProgressionTests`
  (`world/quests/tests/test_acquire.py`), `RuntimeLifecycleTests`
  (`world/quests/tests/test_runtime.py`), `ActionForbiddenStepTests`
  (`world/quests/tests/test_pipeline_scenarios.py`), `MonsterSexualBaselineTests`
  (`world/rules/tests/test_monster_sexual_baseline.py`), `MonsterPopulationTests`
  (`world/rules/tests/test_monster_scale.py`), `LandedEffectHandlerTests`
  (`world/rules/tests/test_effect_handlers.py`), `DisguiseBoundaryTests`
  (`world/rules/tests/test_disguise_boundary.py`) — each builds
  `PlayerCharacter`/`Monster`/`LivingEntity` entities via `create_object`
  without an explicit `home=`/`nohome=`, so home defaults to
  `settings.DEFAULT_HOME = "#2"`. Under `EvenniaTestCase` in a fresh parallel
  worker, that dbref can resolve through the process-global idmapper cache to a
  stale `room2` left by an earlier `EvenniaTest` fixture world in the same
  worker whose transaction was rolled back; the created row then fails the
  `db_home_id` foreign-key check at teardown. The failures are worker-order
  dependent (different classes surfaced across identical full-suite runs), so
  every class with this entity-creation pattern was reverted rather than
  selectively patched.
- `ClimaxRollbackTests` (`world/rules/tests/test_climax_settlement.py`) —
  `test_failed_combat_round_restores_climax_bookkeeping` engages a battlefield
  and the settlement-failure path re-registers it in the process-global
  `_BATTLEFIELDS` skip-safety registry without an isolation mixin; the leaked
  registration failed the contract-pinned `ExamStartTests` "no orphan
  registration" assertions that follow in the package.

**Reviewed and kept as candidates (no exclusion):** every isolation mixin used
by the downgraded classes (`BattlefieldIsolation`, `QuestRegistryIsolation`,
`RegistryIsolationMixin`, `ExamRegistryIsolation`, `ClockRegistryIsolation`,
`OfferRegistryIsolation`, `ShopRegistryIsolation`,
`DialogueTurnInRegistryIsolation`, `ServiceContentIsolation`,
`CompileRegistryIsolation`, `OnboardingGridMixin`) snapshots and restores
process-global registries via `setUp`/`addCleanup` and is compatible with
`EvenniaTestCase`. `ArtPushPresenterTests` was reviewed for its
`SESSION_HANDLER.get_sessions` patch: it uses a `FakeSession`, does not touch
the mixin's `self.session`, and passes after conversion.

**Result:** 186 classes downgraded to `EvenniaTestCase` (or `(Mixin,
EvenniaTestCase)`) across 108 files, 16 reverts, 2 contract-pinned stays.
