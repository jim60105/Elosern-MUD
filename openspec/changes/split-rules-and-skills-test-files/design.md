## Context

Class inventories (verified at `69aabe6`):

`world/rules/tests/test_combat_session.py` (1,351 lines) — 16 classes:
`InnateSkillTests` (5), `CombatSessionRecordTests` (3, `unittest.TestCase`),
`CombatSessionIdTests` (1, `EvenniaTest`), `EngageTests` (4),
`PlayerRoundTests` (7), `CommandedActionAttributionTests` (1),
`ExplicitTargetContractTests` (7), `SessionPersistenceTests` (4),
`MalformedSessionNormalizationTests` (2), `MalformedSessionRecoveryTests` (3),
`SettlementRecoveryTests` (7), `UpkeepTickCreditTests` (2),
`OverwhelmDirectionTests` (2), `PreflightSideEffectTests` (3),
`RoundSettlementSeamTests` (1), `CommandSessionTests` (1,
`EvenniaCommandTestMixin`). Module-level: `_player`, `_monster` (lines
52-61), `SEAM_AREA_KEY` (line 1160). Most classes inherit
`(BattlefieldIsolation, EvenniaTest)` — `BattlefieldIsolation` is imported
from wherever it lives today and must not move.

`world/skills/tests/test_registry.py` (1,708 lines) — 16 classes:
`SkillRegistryTests` (18), `SkillContentCompletionTests` (4),
`DualBladeMasteryCastTests` (2), `LightSwordStyleCastTests` (2),
`DivineMysteryRegistryTests` (1), `FireSpellCatalogTests` (4),
`WaterSpellCatalogTests` (3), `EarthSpellCatalogTests` (2),
`EarthHardenedSkinCastTests` (3), `WindSpellCatalogTests` (4),
`LightningSpellCatalogTests` (3), `IceSpellCatalogTests` (3),
`LightSpellCatalogTests` (3), `DarkSpellCatalogTests` (3),
`SkillCategoryClassificationTests` (13), `FleeCategoryDeclarationTests` (2).
Module-level constants `FIRE_SPELL_CATALOG` … `DARK_SPELL_CATALOG` (lines
619-1280) belong to the catalog classes.

Contract pins: `tests/test_evennia_test_optimization_contract.py:233-259`
asserts `CombatSessionRecordTests` and `CombatSessionIdTests` under the path
`world/rules/tests/test_combat_session.py` — the path moves with the split.
The evennia shard manifest (`.github/evennia-shards.json`) lists
`world.rules.tests.test_combat_session` in a `rules-*` shard — the label must
be replaced by the four new module labels.

No repository code imports these two test modules from outside (verified by
grep at `69aabe6`), so the moves have no external importers.

## Goals / Non-Goals

**Goals:**
- Split the two files into themed modules with byte-identical class bodies.
- Keep every `covers_requirement` annotation on the same methods.
- Update the contract pins and the shard manifest so all gates stay green.
- Leave the original files empty-free (delete them once empty).

**Non-Goals:**
- Refactoring, renaming, or merging any class or method.
- Splitting the other long files (`world/ai`, `world/quests` — sibling
  changes).
- Base-class changes (sibling change `lighten-evenniatest-fixtures` lands
  first; the moves apply to whatever base the classes have).

## Decisions

- **Themed modules**: groupings follow test subject (flow / targeting /
  persistence / recovery; registry / catalogs / casts), matching the repo's
  `test_<theme>.py` naming convention and keeping each new module coherent
  for dotted-label invocation.
- **Shared module code**: `_player`, `_monster`, `SEAM_AREA_KEY`, and the
  spell-catalog constants move into a helpers module or the module that owns
  them (`_combat_session_helpers.py`; the `*_SPELL_CATALOG` constants move
  with the catalog classes into `test_spell_catalogs.py`). Base classes and
  mixins (`BattlefieldIsolation`, `SceneBuilderTestBase`-style) stay where
  they are today and are imported by the new modules.
- **Contract and manifest sync**: the pinned class paths and the shard
  manifest labels are updated in the same change; the ownership contract test
  from `split-evennia-ci-shards` mechanically verifies the manifest.
- **No shim modules**: moved classes are removed from the original file; the
  original file is deleted when empty. Nothing in the repository imports
  these modules, so no import shims are needed.

## Risks / Trade-offs

- **Annotation loss/duplication**: mitigated by grep checks (each class name
  appears exactly once across the new modules) and
  `tools.spec_traceability check`.
- **Helper misplacement**: helpers shared across new modules go to the
  helpers module; if imports would become circular, the executor stops and
  reports rather than duplicating the helper.
- **Test-count drift**: verified by comparing the discovered test count
  before and after (3,104).
- **Manifest/contract mismatch**: the ownership contract test fails loudly
  and is part of the verification gates.
