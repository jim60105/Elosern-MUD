# Tasks

## 1. Delete the generative layer and its prompt/profile plumbing

- [ ] 1.1 Delete `world/ai/action_options/` (`__init__.py`, `cards.py`, `context.py`, `generation.py`, `ladder.py`, `prompt.py`) and `world/ai/tests/test_action_options_layer.py`, `world/ai/tests/test_action_options_schema.py`.
- [ ] 1.2 Delete `prompts/action_options.yaml` and `prompts/tests/action_options.yaml`; delete the two `action_options.*` `PromptSpec` entries in `world/prompts/registry.py`.
- [ ] 1.3 `world/ai/profiles.py`: delete `action_options` from `LAYER_NAMES`, delete `ACTION_OPTIONS_MAX_TOKENS`, the `profiles["action_options"]` default block, `REQUIRED_PROFILE_FLAGS`, and its enforcement branch in `build_profiles`; update the docstrings. Keep `ProfileValidationError` for generic bound failures.
- [ ] 1.4 `world/ai/immutable.py`: docstring only — stop naming the deleted module.
- [ ] 1.5 `server/conf/llm_knobs.py`: delete `action_options` from the layer list and its per-layer `max_tokens` default. `server/conf/settings.py`: update the profile-validation comment only.
- [ ] 1.6 `server/conf/at_server_startstop.py`: delete `register_action_options_layer` from the lazy import list, delete `_register_action_options_layer`, delete its `_startup_step` call, and delete its `STARTUP_STEP_ORDER` entry. `server/conf/tests/test_startup_observability.py`: remove `"world.ai.action_options.register_action_options"` from `_BODY_TARGETS` and any step-order expectation naming the retired step.
- [ ] 1.7 Amend `world/ai/tests/test_profiles.py` (delete `ActionOptionsProfileTests` and the defaults branch) and `prompts/tests/test_loader.py` (delete the four `action_options` cases and the file-name set entry).

## 2. Delete the trigger service and its hooks

- [ ] 2.1 Delete `server/option_proposal_service/` and `server/conf/tests/test_option_proposal_service/`.
- [ ] 2.2 `typeclasses/characters.py`: delete `_schedule_action_options_after_move`, `_schedule_action_options_committed`, the `at_post_move` call, and the docstring paragraphs naming them; in `_schedule_projection_refresh_after_activation` delete the `schedule_action_options` import and call while keeping the `refresh_after_command` loop and watcher resolution — the refresh must still run for every scene activation.
- [ ] 2.3 `typeclasses/npcs.py`: delete the `_schedule_action_options_after_move` import and call in `at_post_move`. `typeclasses/exits.py`: docstring only — remove the sentence naming the action-options trigger.
- [ ] 2.4 `web/webclient/actions/dispatcher.py`: delete `_schedule_options_after_completion`, its call site, the terminal-combat-return schedule block, and their bounded `log_warn` events; the completion publication, result ordering, and sequence retirement stay unchanged.
- [ ] 2.5 `web/webclient/presentation/ingress.py`: delete the `schedule_action_options` call in the `ui_sync`/post-command path only; watcher registration and the snapshot path stay.
- [ ] 2.6 Delete `typeclasses/tests/test_action_options_room_entry.py`, `web/webclient/actions/tests/test_dispatcher/test_dialogue_trigger.py`.
- [ ] 2.7 Amend the surviving tests that patched the service: `web/webclient/actions/tests/test_combat_dispatcher.py`, `world/quests/tests/test_encounter_dispatch.py`, and `web/webclient/actions/tests/test_account_actions/test_presentation_ordering.py` (drop the `options_barriers` fixture/assertions and the `from server.option_proposal_service import _deliver_guarded, _PendingSubscriber` block with its test). Keep every behaviour assertion that is not about the trigger.
- [ ] 2.7a Strip retired annotations from surviving tests before the archive sync (a stale annotation would name a requirement the synced specs no longer carry): `tests/test_ai_transport_contract.py` (both retired-requirement decorators), `web/webclient/actions/tests/test_dispatcher/test_dispatcher_core.py` (retarget the three ABI annotations to the same requirement in `webclient-action-dispatch`), `web/webclient/presentation/tests/test_fingerprints.py` (ten `action-options-trigger-service` annotations and the `server.option_proposal_service` import/test), and `web/webclient/presentation/tests/test_combat_panel/test_suggestions_render_path.py` (two annotations).
- [ ] 2.8 `web/webclient/presentation/tests/test_watchers.py`: keep every behaviour test; delete the retired `covers_requirement` annotations during apply, and at the archive-sync commit add one annotation to the new `webclient-publication-settlements::the-ingress-maintained-watcher-registry-resolves-live-sessions-for-targeted-pushes` requirement (confirm the slug with `uv run --locked python -m tools.spec_traceability list`). Annotating the new ID before the sync would name a requirement the main specs do not yet carry.

## 3. Unregister the dismiss action

- [ ] 3.1 Delete `web/webclient/actions/options.py` and `web/webclient/actions/tests/test_options_actions.py`.
- [ ] 3.2 `web/webclient/actions/registry.py`: delete the `options.dismiss` `ActionSpec` and its imports; update the roster docstring.
- [ ] 3.3 `web/static/webclient/js/elosern/command_echo.js`: delete the `options.dismiss` entry from `SILENT_PRESENTATION_CONTROLS`; `web/static/webclient/js/tests/command_echo_coverage_manifest.json`: delete the same id from BOTH `registeredMutationActionIds` and `silentPresentationControlIds`; `web/static/webclient/js/tests/command_echo.test.js`: drop the `options.dismiss` assertions and keep the other silent-control cases.
- [ ] 3.4 Remove `options.dismiss` from the asserted production registry set in `web/webclient/actions/tests/test_dispatcher/test_registry.py` and the expected-silence row in `web/webclient-app/tests/store/command_echo_surfaces.test.js`.

## 4. Manifests and freezes

- [ ] 4.1 `.github/evennia-shards.json`: remove `world.ai.tests.test_action_options_layer`, `world.ai.tests.test_action_options_schema`, `typeclasses.tests.test_action_options_room_entry`, `web.webclient.actions.tests.test_dispatcher.test_dialogue_trigger`, and `web.webclient.actions.tests.test_options_actions`; add no entry. `server/conf/tests/test_option_proposal_service/` stays covered by the package-level `server` label.
- [ ] 4.2 Remove `server/conf/tests/test_option_proposal_service.py`, `world/ai/tests/test_action_options_layer.py`, and `world/ai/tests/test_action_options_schema.py` from `seedDebtPaths` in BOTH `tools/test_data_freeze.json` and `tools/test_data_lint_seed.json` (the lint gate asserts they match), and remove the same three from `MIGRATED_FILES` in `tests/test_data_independence_ai_server.py`, delete `test_option_proposal_service` from `_SPLIT_PACKAGES`, and update that module's "seventeen modules" docstring. `tools/observability_freeze.json`: confirm no retired path is listed; do not add entries.

## 5. Docs

- [ ] 5.1 `docs/development/llm-architecture.md`: delete the `action_options.py` and `option_proposal_service.py` tree rows.
- [ ] 5.2 `docs/development/llm-scenarios.md`: delete the layer-table row and §6 (`行動建議卡片層`).
- [ ] 5.3 `docs/development/llm-guardrails.md`: delete the 12-stage ladder section and the `action_options` mentions in the no-number and structured-output sections.
- [ ] 5.4 `docs/development/llm-configuration.md` and `docs/development/settings-and-environment.md`: delete the `action_options` MAX_TOKENS and forced SUPPORTS_RESPONSE_FORMAT rows.
- [ ] 5.5 `docs/gm/prompts.md` and `docs/gm/overview.md`: delete the prompt-file/key rows and any layer mention. `.env.example`: delete the `action_options` phrase in the MAX_TOKENS comment and the `LLM_ACTION_OPTIONS_MAX_TOKENS` example.
- [ ] 5.6 Delete the residual comments/docstrings that still name the retired surface: `web/webclient/actions/dispatcher.py` (module docstring), `web/webclient/actions/registry.py` (`options.dismiss` precedent comment), `web/webclient/actions/title_actions.py`, `server/title_nomination_service.py`, `web/webclient-app/components/SettingsOverlay.vue`, and `web/admin-app/stories/fixtures.js`.
- [ ] 5.7 Confirm `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` is untouched (it never names the layer) and the five `2026-08-15-ai-action-options-*` design documents stay as historical provenance.

## 6. Verification

- [ ] 6.1 `grep -RIn "action_options\|option_proposal_service\|options\.dismiss" --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=__pycache__ .` returns only: this change's own artifacts, `openspec/changes/archive/**`, the five retained dated design docs, the `openspec/specs/**` requirement blocks retired by `retire-context-actions-suggestions`, and the docstrings of the two modules that change deletes (`presentation/options.py`, `presentation/fingerprints.py`). Anything else is a missed reference.
- [ ] 6.2 `uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb world.ai.tests.test_profiles prompts.tests.test_loader server.conf.tests.test_llm_env_overrides` passes.
- [ ] 6.3 `uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb typeclasses.tests.test_exits typeclasses.tests.test_npcs web.webclient.actions.tests.test_combat_dispatcher world.quests.tests.test_encounter_dispatch web.webclient.presentation.tests.test_watchers` passes.
- [ ] 6.4 `uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb web.webclient.actions.tests.test_dispatcher web.webclient.actions.tests.test_registry web.webclient.actions.tests.test_action_catalog_coverage` passes (the roster and catalog coverage pins lose exactly `options.dismiss`).
- [ ] 6.5 `node --test web/static/webclient/js/tests/command_echo.test.js` passes.
- [ ] 6.6 `uv run --locked python -m tools.test_data_lint check`, the focused `tests.test_test_data_lint` and `tests.test_data_independence_ai_server` test modules, and `uv run --locked python -m tools.observability_lint check` pass.
- [ ] 6.7 `uv run --locked python -m tools.spec_traceability check` passes; no annotation names a retired requirement.
- [ ] 6.8 The focused `tests.test_evennia_test_optimization_contract`, `server.conf.tests.test_startup_observability`, and `tests.test_ai_transport_contract` test modules pass (shard ownership, the removed startup step, and the stripped transport annotations).
- [ ] 6.9 `openspec validate retire-action-options-service --strict` passes.
- [ ] 6.10 `uv run --locked python -m tools.contract_gate --change retire-action-options-service` passes.

## 7. Offline playability

- [ ] 7.1 With every `LLM_PROFILES` entry disabled, walk one deterministic loop (move → look → talk → wait) and confirm the dock, compass, readout, presence rail, verb card, and place card work with no network call and no action-options event on startup.
