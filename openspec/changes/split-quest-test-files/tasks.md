# Tasks: Split the Quests Long Test Files

## 1. Split `world/quests/tests/test_scene_builder.py`

- [ ] 1.1 Keep in `test_scene_builder.py`: `SceneBuilderTestBase`,
      `SceneBuilderIsolation`, the module-level payload helpers, and
      SceneBuilderMaterializationTests, SceneBuilderCharacterizationTests,
      SceneBuilderPortraitPipelineTests, SceneOccupantPrototypeTests
- [ ] 1.2 Create `test_scene_builder_offline.py`
      (SceneBuilderOfflineLoopTests), `test_scene_builder_flavor.py`
      (SceneFlavorContextAndApplyTests), and `test_scene_builder_boundary.py`
      (SceneBuilderBoundaryTests), importing the base/mixins:
      `from .test_scene_builder import SceneBuilderTestBase,
      SceneBuilderIsolation` (match the actual names), moving every
      `covers_requirement` annotation with its method
- [ ] 1.3 Remove the moved classes from `test_scene_builder.py`

## 2. Split `world/quests/tests/test_compile.py`

- [ ] 2.1 Create `world/quests/tests/_compile_helpers.py` with the module-level
      payload helpers, `await_result`, **and `CompileRegistryIsolation`
      (currently defined at `test_compile.py:170` — move it here so the new
      modules can import it after the original file is deleted)**
- [ ] 2.2 Create `test_compile_blueprint.py` (CompileQuestBlueprintTests,
      SceneBoundCompileTests, CharacterizationCompileTests),
      `test_compile_registration.py` (RegisterGeneratedQuestTests,
      SceneRequirementRegistryTests, SharedPayloadContractTests), and
      `test_compile_offline.py` (OfflineDirectorEndToEndTests), importing
      `CompileRegistryIsolation` and the helpers from `_compile_helpers`
- [ ] 2.3 Remove the moved classes and helpers from `test_compile.py`; delete
      the file only after confirming `CompileRegistryIsolation` is gone from
      it (nothing may reference the deleted file)

## 3. Contract tests and verification

- [ ] 3.1 Create `tests/test_quests_test_layout_contract.py`: AST-based (no
      imports) partition check asserting (a) `test_scene_builder_offline.py`,
      `test_scene_builder_flavor.py`, `test_scene_builder_boundary.py`,
      `test_compile_blueprint.py`, `test_compile_registration.py`, and
      `test_compile_offline.py` exist, and (b) every class from the pre-split
      inventories appears in exactly one test module of `world/quests/tests`;
      annotate with
      `covers_requirement("evennia-test-optimization::scene-builder-and-compile-test-modules-are-split-with-shared-bases-kept-importable")`
      (verify the literal ID with `uv run --locked python -m
      tools.spec_traceability list` after the delta spec is written)
- [ ] 3.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings
      test_settings.py --keepdb world.quests` — all pass
- [ ] 3.3 `uv run --locked python -m tools.spec_traceability check` — exit 0
- [ ] 3.4 `uv run --locked -m unittest discover -s tests -t .` — all pass
      (evennia manifest ownership + the new layout contract)
- [ ] 3.5 Full suite: `MUD_TEST_SETTINGS=1 uv run --locked evennia test
      --settings test_settings.py --noinput --parallel 16 commands server
      typeclasses world web.webclient` — same discovered test count (3,104)
- [ ] 3.6 Spot-check dotted-label iteration:
      `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings
      test_settings.py --keepdb world.quests.tests.test_compile_blueprint.CompileQuestBlueprintTests`
      — runs only that class

## 4. OpenSpec and handoff

- [ ] 4.1 `openspec validate split-quest-test-files --strict`
- [ ] 4.2 Sync the delta spec into
      `openspec/specs/evennia-test-optimization/spec.md`, archive the change,
      run `openspec validate --all --strict`, and confirm `git diff --check`
      is clean
