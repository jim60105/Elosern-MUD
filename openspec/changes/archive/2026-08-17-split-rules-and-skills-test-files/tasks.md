# Tasks: Split the Rules and Skills Long Test Files

## 1. Split `world/rules/tests/test_combat_session.py`

- [x] 1.1 Create `world/rules/tests/_combat_session_helpers.py` with the
      module-level `_player`, `_monster`, `SEAM_AREA_KEY` code and the shared
      imports (including `BattlefieldIsolation` from wherever it lives today)
- [x] 1.2 Create `test_combat_session_flow.py` (InnateSkillTests, EngageTests,
      PlayerRoundTests, CommandedActionAttributionTests,
      RoundSettlementSeamTests, CommandSessionTests — its
      `EvenniaCommandTestMixin` base stays), `test_combat_session_targeting.py`
      (ExplicitTargetContractTests), `test_combat_session_persistence.py`
      (CombatSessionRecordTests, CombatSessionIdTests, SessionPersistenceTests),
      and `test_combat_session_recovery.py` (MalformedSessionNormalizationTests,
      MalformedSessionRecoveryTests, SettlementRecoveryTests,
      UpkeepTickCreditTests, OverwhelmDirectionTests, PreflightSideEffectTests),
      importing helpers from the helpers module; move every
      `covers_requirement` annotation with its method
- [x] 1.3 Remove the moved classes from `test_combat_session.py`; delete the
      file if nothing remains
- [x] 1.4 Update `tests/test_evennia_test_optimization_contract.py`: the
      `world/rules/tests/test_combat_session.py` expectations key moves to
      `world/rules/tests/test_combat_session_persistence.py` with the same
      class-to-base assertions
- [x] 1.5 Update `.github/evennia-shards.json`: replace the
      `world.rules.tests.test_combat_session` label in its `rules-*` shard
      with the four new module labels
- [x] 1.6 Update the `__import__`-resolved module keys in
      `world/rules/tests/test_guild_economy_scenarios.py` and the
      developer-doc examples naming the deleted modules (`AGENTS.md`,
      `docs/development/evennia-testing-guide.md`,
      `docs/development/adding-spells.md`)

## 2. Split `world/skills/tests/test_registry.py`

- [x] 2.1 Create `test_skill_registry.py` (SkillRegistryTests,
      SkillContentCompletionTests, DivineMysteryRegistryTests,
      SkillCategoryClassificationTests, FleeCategoryDeclarationTests)
- [x] 2.2 Create `test_spell_catalogs.py` (the eight `*SpellCatalogTests`
      classes plus their eight `*_SPELL_CATALOG` constants)
- [x] 2.3 Create `test_skill_casts.py` (DualBladeMasteryCastTests,
      LightSwordStyleCastTests, EarthHardenedSkinCastTests)
- [x] 2.4 Remove the moved classes and constants from `test_registry.py`;
      delete it if nothing remains; keep the file's shared import block
      per-module with only what each module uses

## 3. Contract tests and verification

- [x] 3.1 Create `tests/test_rules_skills_test_layout_contract.py`:
      AST-based (no imports) partition check asserting (a) the four
      `world.rules.tests.test_combat_session_*` modules and the three
      `world.skills.tests.test_skill_*` / `test_spell_catalogs` modules
      exist, and (b) every class from the pre-split inventories appears in
      exactly one test module of its package (no duplicates, no orphans);
      annotate the test with
      `covers_requirement("evennia-test-optimization::combat-session-and-skill-registry-test-modules-are-split-into-themed-modules")`
      (verify the literal ID with `uv run --locked python -m
      tools.spec_traceability list` after the delta spec is written)
- [x] 3.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings
      test_settings.py --keepdb world.rules` and `... world.skills` — all pass
- [x] 3.3 `uv run --locked python -m tools.spec_traceability check` — exit 0
      (static check passes once the delta spec is synced into main specs in
      4.2; the ID slug matches the tool's normalization — run again after 4.2)
- [x] 3.4 `uv run --locked -m unittest discover -s tests -t .` — all pass
      (pinned paths + evennia manifest ownership + the new layout contract)
- [x] 3.5 Full suite: `MUD_TEST_SETTINGS=1 uv run --locked evennia test
      --settings test_settings.py --noinput --parallel 16 commands server
      typeclasses world web.webclient` — same discovered test count (3,104
      at proposal time; measured 4,263 both before and after the split at
      the current HEAD)
- [x] 3.6 Spot-check dotted-label iteration:
      `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings
      test_settings.py --keepdb world.rules.tests.test_combat_session_flow.PlayerRoundTests`
      — runs only that class

## 4. OpenSpec and handoff

- [x] 4.1 `openspec validate split-rules-and-skills-test-files --strict`
- [x] 4.2 Sync the delta spec into
      `openspec/specs/evennia-test-optimization/spec.md`, archive the change,
      run `openspec validate --all --strict`, and confirm `git diff --check`
      is clean