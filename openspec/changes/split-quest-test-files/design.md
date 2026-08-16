## Context

Class inventories (verified at `69aabe6`):

`world/quests/tests/test_scene_builder.py` (1,258 lines) — 9 classes:
`SceneOccupantPrototypeTests` (3), `SceneBuilderMaterializationTests` (15),
`SceneBuilderCharacterizationTests` (12), `SceneBuilderPortraitPipelineTests`
(2), `SceneBuilderOfflineLoopTests` (5, `SceneBuilderIsolation` +
`EvenniaCommandTestMixin` + `EvenniaTest`), `SceneFlavorContextAndApplyTests`
(11), `SceneBuilderBoundaryTests` (5, `unittest.TestCase`), plus the shared
base `SceneBuilderTestBase` and the `SceneBuilderIsolation` mixin (defined in
the file or imported — keep them where they are). Module-level payload
helpers at lines 69-178.

`world/quests/tests/test_compile.py` (1,130 lines) — 7 classes:
`CompileQuestBlueprintTests` (22), `RegisterGeneratedQuestTests` (4),
`SceneBoundCompileTests` (8), `SceneRequirementRegistryTests` (5),
`CharacterizationCompileTests` (8), `SharedPayloadContractTests` (1),
`OfflineDirectorEndToEndTests` (1). All inherit
`(CompileRegistryIsolation, unittest.TestCase)` except
`OfflineDirectorEndToEndTests` (`CompileRegistryIsolation`, `EvenniaTest`).
Module-level payload helpers at lines 76-140 and `await_result` at line 1123.

`CompileRegistryIsolation` is defined in `world/quests/tests/test_compile.py:170`
(verified at `69aabe6`; no other module imports it), so it must MOVE to
`_compile_helpers.py` before `test_compile.py` is deleted — the new compile
modules import it from there.

No repository code imports these two test modules from outside (verified by
grep at `69aabe6`), so the moves have no external importers. The evennia
shard manifest owns `world.quests` by package label, so new modules under it
need no manifest edit.

## Goals / Non-Goals

**Goals:**
- Split the two files into themed modules with byte-identical class bodies.
- Keep `SceneBuilderTestBase`/`SceneBuilderIsolation` in
  `test_scene_builder.py` so moved subclasses import them cleanly.
- Keep every `covers_requirement` annotation on the same methods.
- Keep the original files slim (scene builder) or deleted (compile, when
  empty).

**Non-Goals:**
- Refactoring, renaming, or merging any class or method.
- Splitting the other long files (`world/rules`, `world/skills`,
  `world/ai` — sibling changes).
- Changing `_fixtures.py` contents beyond what the compile split imports.

## Decisions

- **Base-stays-put rule**: shared base classes and mixins remain in
  `test_scene_builder.py`; the offline/flavor/boundary modules import them
  (`from .test_scene_builder import SceneBuilderTestBase,
  SceneBuilderIsolation`). This matches the repo's `_fixtures.py` import
  pattern and avoids moving code the remaining classes also use.
- **Helpers module for compile**: the payload builders, `await_result`, AND
  `CompileRegistryIsolation` (currently defined at `test_compile.py:170` —
  it must move before the original file is deleted) go to
  `world/quests/tests/_compile_helpers.py` (alongside the existing
  `_fixtures.py`); each new compile module imports what it uses from there.
- **Manifest**: no change required (`world.quests` is a package label); the
  ownership contract test from `split-evennia-ci-shards` re-verifies.

## Risks / Trade-offs

- **Base-class import coupling**: new scene-builder modules import from
  `test_scene_builder.py`; if the original file is later deleted, those
  imports break — acceptable because the base classes stay there
  permanently (documented in the module docstrings).
- **Annotation loss/duplication**: mitigated by grep (each class name appears
  exactly once) and `tools.spec_traceability check`.
- **Circular imports**: avoided by keeping bases in the original module and
  helpers in dedicated modules; if a cycle appears, STOP and report.
- **Test-count drift**: verified by comparing discovered counts (3,104).
