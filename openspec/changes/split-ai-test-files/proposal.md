## Why

`world/ai/tests/test_scenario_director.py` (1,569 lines, 12 classes) and
`world/ai/tests/test_npc_dialogue.py` (1,310 lines, 14 classes) are among the
largest test files in the repository. Each class is independently runnable
via dotted labels, but 1,300+ line files make targeted iteration and review
slow. Splitting them into themed modules — classes kept byte-identical, only
their files move — gives fine-grained local development. Pure code movement:
no test semantics, coverage, or traceability change.

## What Changes

- `world/ai/tests/test_scenario_director.py` splits into
  `test_scenario_director_proposals.py`
  (ScenarioDirectorProposalTypeTests, BlueprintCharacterizationTypeTests),
  `test_scenario_director_prompts.py` (ScenarioDirectorPromptTests),
  `test_scenario_director_validation.py` (ScenarioDirectorValidatorTests,
  SceneBoundValidatorTests, CharacterizationValidatorTests), and
  `test_scenario_director_registration.py` (ScenarioDirectorRegistrationTests,
  ScenarioDirectorEntryPointTests, ScenarioDirectorTemplatePoolTests,
  RegistryRestoreRegressionTests, ScenarioDirectorStartupRegistrationTests,
  ScenarioDirectorOfflineTestRuleTests); the shared module-level helpers
  (`_raw`, `_reset_all`, `await_result`, `_item`, `_location`, `_stage`,
  `_blueprint`, `_payload`, `_context`, …) move to
  `world/ai/tests/_director_helpers.py`.
- `world/ai/tests/test_npc_dialogue.py` splits into
  `test_npc_dialogue_prompts.py` (NPCDialoguePromptTests, AffinityPromptTests,
  PersonaPromptTests), `test_npc_dialogue_validators.py`
  (AffinityValidatorUnitTests, PartyInviteValidatorUnitTests,
  OfferQuestValidatorUnitTests, RevealLoreValidatorUnitTests,
  SecretSetValidatorUnitTests), `test_npc_dialogue_registration.py`
  (ReplyEntryPointTests, RegistrationGateTests, StartupRegistrationTests), and
  `test_npc_dialogue_retry.py` (ValidatorRetryTests, DegradePathTests); the
  shared helpers (`_raw`, `_reset_all`, `await_result`, `_npc_context`,
  `_player_context`, `_memory`, `_reply_text`, …) move to
  `world/ai/tests/_dialogue_helpers.py`.
- Every `covers_requirement(...)` annotation moves with its method; class
  bodies are not refactored. `RegistryIsolationMixin` stays where it lives
  and is imported by the modules that need it.
- The `world.ai` package labels in the evennia shard manifest
  (`.github/evennia-shards.json`) cover the new modules automatically — no
  manifest change needed; the ownership contract test still verifies it.

No backward-compatibility or migration work is needed — the project has no
released users.

## Capabilities

### Modified Capabilities

- `evennia-test-optimization`: "Long test files are split into themed
  modules" (added by `split-rules-and-skills-test-files`) applies to these
  files too; this change adds its scenarios for helper modules shared across
  new modules.

## Impact

- `world/ai/tests/` — two files replaced by eight modules plus two helpers
  modules.
- No production code, no player-facing commands, no test behavior change.
- Sibling changes split the remaining long files (`world/quests`).
