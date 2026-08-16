## Why

`world/rules/tests/test_combat_session.py` (1,351 lines, 16 classes) and
`world/skills/tests/test_registry.py` (1,708 lines, 16 classes) are among the
largest test files in the repository. Every class is independently runnable
via dotted labels, but developing inside a 1,700-line file is slow and merge
conflicts are painful. Splitting each file into themed modules — classes kept
byte-identical, only their file moves — gives fine-grained local iteration
and creates the natural units for the CI shard manifests. This is pure code
movement: no test semantics, coverage, or traceability change.

## What Changes

- `world/rules/tests/test_combat_session.py` splits into
  `test_combat_session_flow.py` (InnateSkillTests, EngageTests,
  PlayerRoundTests, CommandedActionAttributionTests, RoundSettlementSeamTests,
  CommandSessionTests), `test_combat_session_targeting.py`
  (ExplicitTargetContractTests), `test_combat_session_persistence.py`
  (CombatSessionRecordTests, CombatSessionIdTests, SessionPersistenceTests),
  and `test_combat_session_recovery.py` (MalformedSessionNormalizationTests,
  MalformedSessionRecoveryTests, SettlementRecoveryTests, UpkeepTickCreditTests,
  OverwhelmDirectionTests, PreflightSideEffectTests); the shared `_player`/
  `_monster`/`SEAM_AREA_KEY` module code moves to
  `world/rules/tests/_combat_session_helpers.py`.
- `world/skills/tests/test_registry.py` splits into `test_skill_registry.py`
  (SkillRegistryTests, SkillContentCompletionTests, DivineMysteryRegistryTests,
  SkillCategoryClassificationTests, FleeCategoryDeclarationTests),
  `test_spell_catalogs.py` (the eight `*SpellCatalogTests` plus their eight
  `*_SPELL_CATALOG` constants), and `test_skill_casts.py`
  (DualBladeMasteryCastTests, LightSwordStyleCastTests,
  EarthHardenedSkinCastTests).
- Every `covers_requirement(...)` annotation moves with its method; class
  bodies are not refactored.
- The contract pin in `tests/test_evennia_test_optimization_contract.py`
  (`test_pure_candidates_use_unittest_while_integration_fixture_remains`)
  moves `CombatSessionRecordTests`/`CombatSessionIdTests` to the new
  persistence module path.
- `.github/evennia-shards.json` (from `split-evennia-ci-shards`) replaces the
  `world.rules.tests.test_combat_session` label with the four new modules; the
  ownership contract test verifies it.

No backward-compatibility or migration work is needed — the project has no
released users.

## Capabilities

### Modified Capabilities

- `evennia-test-optimization`: "Long test files are split into themed
  modules" requirement added (test-module ownership in the shard manifests
  must be updated when modules are created).

## Impact

- `world/rules/tests/` — one file replaced by four modules plus one helpers
  module; `world/skills/tests/` — one file replaced by three modules.
- `tests/test_evennia_test_optimization_contract.py` — pinned-path update.
- `.github/evennia-shards.json` — label update for the rules shard.
- `world/rules/tests/test_guild_economy_scenarios.py` — the
  `__import__`-resolved module key for combat-session classes splits into
  per-module keys; developer-doc examples naming the deleted modules are
  updated (`AGENTS.md`, `docs/development/evennia-testing-guide.md`,
  `docs/development/adding-spells.md`).
- No production code, no player-facing commands, no test behavior change.
- Sibling changes split the remaining long files (`world/ai`, `world/quests`).
