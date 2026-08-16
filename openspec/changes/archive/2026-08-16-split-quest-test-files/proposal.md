## Why

`world/quests/tests/test_scene_builder.py` (1,258 lines, 9 classes) and
`world/quests/tests/test_compile.py` (1,130 lines, 7 classes) are among the
largest test files in the repository. Each class is independently runnable
via dotted labels, but 1,100+ line files make targeted iteration and review
slow. Splitting them into themed modules — classes kept byte-identical, only
their files move — gives fine-grained local development. Pure code movement:
no test semantics, coverage, or traceability change.

## What Changes

- `world/quests/tests/test_scene_builder.py` keeps the shared base and
  mixins (`SceneBuilderTestBase`, `SceneBuilderIsolation`), the module-level
  payload helpers, and the materialization family
  (SceneBuilderMaterializationTests, SceneBuilderCharacterizationTests,
  SceneBuilderPortraitPipelineTests, SceneOccupantPrototypeTests); new
  modules `test_scene_builder_offline.py` (SceneBuilderOfflineLoopTests),
  `test_scene_builder_flavor.py` (SceneFlavorContextAndApplyTests), and
  `test_scene_builder_boundary.py` (SceneBuilderBoundaryTests) import the
  base/mixins from the original module.
- `world/quests/tests/test_compile.py` splits into
  `test_compile_blueprint.py` (CompileQuestBlueprintTests,
  SceneBoundCompileTests, CharacterizationCompileTests),
  `test_compile_registration.py` (RegisterGeneratedQuestTests,
  SceneRequirementRegistryTests, SharedPayloadContractTests), and
  `test_compile_offline.py` (OfflineDirectorEndToEndTests); the shared
  payload helpers and `await_result` move to
  `world/quests/tests/_compile_helpers.py`, and `CompileRegistryIsolation`
  is imported from wherever it lives today.
- Every `covers_requirement(...)` annotation moves with its method; class
  bodies are not refactored.
- The `world.quests` package label in the evennia shard manifest
  (`.github/evennia-shards.json`) covers the new modules automatically — no
  manifest change needed; the ownership contract test still verifies it.

No backward-compatibility or migration work is needed — the project has no
released users.

## Capabilities

### Modified Capabilities

- `evennia-test-optimization`: "Long test files are split into themed
  modules" (added by `split-rules-and-skills-test-files`) applies to these
  files too; this change adds its scenarios for keeping shared base classes
  in the original module and importing them.

## Impact

- `world/quests/tests/` — `test_scene_builder.py` slimmed with three new
  modules; `test_compile.py` replaced by three modules plus a helpers module.
- No production code, no player-facing commands, no test behavior change.
