# Tasks: Split the AI Long Test Files

## 1. Split `world/ai/tests/test_scenario_director.py`

- [ ] 1.1 Create `world/ai/tests/_director_helpers.py` with the module-level
      helpers (`_raw`, `_semantic_reset`, `_fallback_reset`, `_schema_reset`,
      `_reset_all`, `await_result`, `_item`, `_location`, `_stage`,
      `_blueprint`, `_payload`, `_context`, **and `_instance_payload`** —
      `RegistryRestoreRegressionTests` calls it at `test_scenario_director.py:1503`)
      and the shared import block
- [ ] 1.2 Create `test_scenario_director_proposals.py`
      (ScenarioDirectorProposalTypeTests, BlueprintCharacterizationTypeTests),
      `test_scenario_director_prompts.py` (ScenarioDirectorPromptTests),
      `test_scenario_director_validation.py` (ScenarioDirectorValidatorTests,
      SceneBoundValidatorTests, CharacterizationValidatorTests), and
      `test_scenario_director_registration.py`
      (ScenarioDirectorRegistrationTests, ScenarioDirectorEntryPointTests,
      ScenarioDirectorTemplatePoolTests, RegistryRestoreRegressionTests,
      ScenarioDirectorStartupRegistrationTests,
      ScenarioDirectorOfflineTestRuleTests), importing helpers from
      `_director_helpers` and `RegistryIsolationMixin` from
      `world.quests.tests._fixtures` where needed; move every
      `covers_requirement` annotation with its method
- [ ] 1.3 Update `ScenarioDirectorOfflineTestRuleTests.test_no_live_client_constructor_or_socket_in_scenario_director_tests`
      (currently `test_scenario_director.py:1549-1564`, reads the fixed path
      `.../tests/test_scenario_director.py`): change it to glob the
      `world/ai/tests` package for `test_scenario_director_*.py` modules and
      run the same three assertions (no `OpenAICompatClient(`, no `import
      socket`, no `from socket`) over every module's source
- [ ] 1.4 Remove the moved classes and helpers from `test_scenario_director.py`;
      delete the file if nothing remains

## 2. Split `world/ai/tests/test_npc_dialogue.py`

- [ ] 2.1 Create `world/ai/tests/_dialogue_helpers.py` with the module-level
      helpers and support classes (`_raw`, `_reset_all`, `await_result`,
      `_npc_context`, `_player_context`, `_memory`, `_reply_text`, …,
      **and `_HeldDialogueClient`** — used by the retry tests at
      `test_npc_dialogue.py:1018-1019,1094-1095`) and the shared import
      block (do NOT merge with `_director_helpers.py` — separate domains)
- [ ] 2.2 Create `test_npc_dialogue_prompts.py` (NPCDialoguePromptTests,
      AffinityPromptTests, PersonaPromptTests),
      `test_npc_dialogue_validators.py` (AffinityValidatorUnitTests,
      PartyInviteValidatorUnitTests, OfferQuestValidatorUnitTests,
      RevealLoreValidatorUnitTests, SecretSetValidatorUnitTests),
      `test_npc_dialogue_registration.py` (ReplyEntryPointTests,
      RegistrationGateTests, StartupRegistrationTests), and
      `test_npc_dialogue_retry.py` (ValidatorRetryTests, DegradePathTests)
- [ ] 2.3 Remove the moved classes and helpers from `test_npc_dialogue.py`;
      delete the file if nothing remains

## 3. Contract tests and verification

- [ ] 3.1 Create `tests/test_ai_test_layout_contract.py`: AST-based (no
      imports) partition check asserting (a) the four
      `world.ai.tests.test_scenario_director_*` modules and the four
      `world.ai.tests.test_npc_dialogue_*` modules exist, and (b) every class
      from the pre-split inventories appears in exactly one test module of
      `world/ai/tests`; annotate with
      `covers_requirement("evennia-test-optimization::ai-test-modules-are-split-into-themed-helpers-backed-modules")`
      (verify the literal ID with `uv run --locked python -m
      tools.spec_traceability list` after the delta spec is written)
- [ ] 3.2 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings
      test_settings.py --keepdb world.ai` — all pass
- [ ] 3.3 `uv run --locked python -m tools.spec_traceability check` — exit 0
- [ ] 3.4 `uv run --locked -m unittest discover -s tests -t .` — all pass
      (evennia manifest ownership + the new layout contract)
- [ ] 3.5 Full suite: `MUD_TEST_SETTINGS=1 uv run --locked evennia test
      --settings test_settings.py --noinput --parallel 16 commands server
      typeclasses world web.webclient` — same discovered test count (3,104)
- [ ] 3.6 Spot-check dotted-label iteration:
      `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings
      test_settings.py --keepdb world.ai.tests.test_npc_dialogue_retry.ValidatorRetryTests`
      — runs only that class

## 4. OpenSpec and handoff

- [ ] 4.1 `openspec validate split-ai-test-files --strict`
- [ ] 4.2 Sync the delta spec into
      `openspec/specs/evennia-test-optimization/spec.md`, archive the change,
      run `openspec validate --all --strict`, and confirm `git diff --check`
      is clean
