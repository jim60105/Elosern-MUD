## Context

### Test classes vs. shared code (verified at `69aabe6`)

`world/ai/tests/test_scenario_director.py` (1,569 lines):
- Discoverable test classes (12): `ScenarioDirectorProposalTypeTests` (11),
  `BlueprintCharacterizationTypeTests` (5), `ScenarioDirectorPromptTests` (4),
  `ScenarioDirectorValidatorTests` (16), `SceneBoundValidatorTests` (7,
  `RegistryIsolationMixin`), `CharacterizationValidatorTests` (8),
  `ScenarioDirectorRegistrationTests` (3), `ScenarioDirectorEntryPointTests`
  (8), `ScenarioDirectorTemplatePoolTests` (9, `RegistryIsolationMixin`),
  `RegistryRestoreRegressionTests` (1), `ScenarioDirectorStartupRegistrationTests`
  (2), `ScenarioDirectorOfflineTestRuleTests` (1).
- Module helpers (move to `_director_helpers.py`): `_raw`,
  `_semantic_reset`, `_fallback_reset`, `_schema_reset`, `_reset_all`,
  `await_result`, `_item`, `_location`, `_stage`, `_blueprint`, `_payload`,
  `_context` (lines 53-140) and `_instance_payload` (line 1449, used by
  `RegistryRestoreRegressionTests` at line 1503).
- Imported mixins (stay in place): `RegistryIsolationMixin` from
  `world/quests/tests/_fixtures.py`.
- Fixed-path dependency: `ScenarioDirectorOfflineTestRuleTests` reads
  `tests/test_scenario_director.py` (lines 1549-1564) — must be updated to
  glob the split modules (task 1.3).

`world/ai/tests/test_npc_dialogue.py` (1,310 lines):
- Discoverable test classes (13, all `unittest.TestCase`): `NPCDialoguePromptTests`
  (6), `AffinityPromptTests` (3), `AffinityValidatorUnitTests` (5),
  `PartyInviteValidatorUnitTests` (3), `OfferQuestValidatorUnitTests` (5),
  `RevealLoreValidatorUnitTests` (5), `ReplyEntryPointTests` (6),
  `RegistrationGateTests` (7), `PersonaPromptTests` (5),
  `SecretSetValidatorUnitTests` (2), `ValidatorRetryTests` (24),
  `DegradePathTests` (4), `StartupRegistrationTests` (2).
- Module helpers and support classes (move to `_dialogue_helpers.py`):
  `_raw`, `_semantic_reset`, `_fallback_reset`, `_schema_reset`, `_reset_all`,
  `await_result`, `_npc_context`, `_player_context`, `_memory`, `_reply_text`
  (lines 41-90) and `_HeldDialogueClient` (line 96, used by the retry tests
  at lines 1018-1019 and 1094-1095).

No repository code imports these two test modules from outside (verified by
grep at `69aabe6`), so the moves have no external importers. The evennia
shard manifest owns `world.ai` by package label, so new modules under it need
no manifest edit.

## Goals / Non-Goals

**Goals:**
- Split the two files into themed modules with byte-identical class bodies.
- Keep every `covers_requirement` annotation on the same methods.
- Centralize each file's shared helpers in one per-family helpers module so
  new modules import them (no duplicated helper code).
- Keep the original files empty-free (delete once empty).

**Non-Goals:**
- Refactoring, renaming, or merging any class or method.
- Splitting the other long files (`world/rules`, `world/skills`,
  `world/quests` — sibling changes).
- Changing `RegistryIsolationMixin` or any non-test code.

## Decisions

- **Per-family helpers modules**: `_director_helpers.py` and
  `_dialogue_helpers.py` hold the module-level private helpers and the shared
  import block; each new test module imports only what it uses. The repo
  already uses `_fixtures.py`-style helper modules
  (`world/quests/tests/_fixtures.py`).
- **Themed groupings**: proposals / prompts / validation / registration for
  the director; prompts / validators / registration / retry for the dialogue
  family — matching the `test_<theme>.py` naming convention.
- **Mixin imports unchanged**: modules that need `RegistryIsolationMixin`
  import it from `world.quests.tests._fixtures` exactly as today.
- **Manifest**: no change required (`world.ai` is a package label); the
  ownership contract test from `split-evennia-ci-shards` re-verifies.

## Risks / Trade-offs

- **Helper drift between the two files**: the director and dialogue helpers
  look similar but are separate modules — do not merge them or share across
  families (they belong to different domains).
- **Annotation loss/duplication**: mitigated by grep (each class name appears
  exactly once) and `tools.spec_traceability check`.
- **Circular imports**: avoided by putting helpers in dedicated modules; if a
  cycle appears, STOP and report rather than duplicating helpers.
- **Test-count drift**: verified by comparing discovered counts at the
  `69aabe6` baseline (4,263 discovered with the current `--parallel 16`
  invocation, matching the on-disk suite size).
