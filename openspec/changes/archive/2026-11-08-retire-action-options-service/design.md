# Design

## Context

See `proposal.md`. The backend chain is one connected import graph: `typeclasses/characters.py`, the dispatcher, and `ingress.py` call `server/option_proposal_service.schedule_action_options`, which imports `world.ai.action_options.generate_action_options`, which renders `prompts/action_options.yaml` through the `action_options` profile slot and validates with the ladder. Deleting any one node without the others leaves a broken import, so the chain is one change. The client renderer is already gone (`retire-action-options-webclient`).

## Goals / Non-Goals

**Goals:**

- No module, prompt, profile slot, action, or trigger survives for the retired feature, and startup/shutdown runs without any action-options registration step.
- Every surviving targeted panel push still resolves its audience through the same watcher registry, with its contract still specified.
- The action roster, the client catalog's silent-control declaration, the LLM profile registry, and the environment knobs describe only what exists.
- The deterministic game is untouched: no movement, dialogue, combat, clock, or quest behaviour changes.

**Non-Goals:**

- Do not touch the `context_actions` panel's `suggestions` field, `validate_suggestions`, the schema version, `OptionsSnapshot`/`FrozenCard`, `presentation/fingerprints.py`, or the affordance suggestion helpers. They still compile against an always-absent presentation state and are deleted by `retire-context-actions-suggestions`.
- Do not delete `web/webclient/presentation/watchers.py`, `typeclasses/exits.py`'s movement boundary, or any push helper; only the suggestion trigger call sites go.
- Do not amend the 2026-07-29 architecture document (it never names this layer) or rewrite the five dated 2026-08-15 feature design documents (historical provenance).

## Decisions

**D1 — Delete the whole chain, no offline stub.** The trigger service's `_OfflineStubClient` and the `client=None` fallback existed so a disabled profile degraded instead of opening a socket. With no generation call there is no stub to keep; deleting both removes the last "guess a session" seam.

**D2 — The watcher registry moves; it does not die.** `watchers_for` is consumed by `dialogue_push`, `lore_codex_push`, `party_push`, `travel_log_push`, and `alignment.py`, so the mechanism is general infrastructure. Its two duplicate requirements (one in the trigger hooks, one in the trigger service) are REMOVED, and `webclient-publication-settlements` gains one ADDED requirement stating the ingress-maintained, epoch-at-query-time contract. Removing the mechanism instead would orphan four live pushes.

**D3 — The adapter ABI is already owned elsewhere.** `webclient-action-dispatch` already specifies "Adapters may receive the authenticated session through a fixed optional third parameter", and every surviving adapter keeps that signature (`gallery.*`, `dream.*`, `account.character.*`, exploration ones). The dismiss capability's duplicate requirement is REMOVED without a move.

**D4 — Keep the read side compiling in this change.** `combat_panel.py`'s `_suggestions_section` reads `context.options_state`; with no writer, that value is always `None`, so the presenter already emits `{"status": "unavailable"}` on every render. The same is true for `fingerprints.py`, `OptionsSnapshot`, `FrozenCard`, `default_cards`, and `suggestible_candidates`: they compile and are simply unreachable. Leaving them one change longer keeps this change a pure backend deletion and avoids touching ~60 `context_actions` fixtures twice.

**D5 — `REQUIRED_PROFILE_FLAGS` dies with its only entry.** The mapping, its `ProfileValidationError` branch in `build_profiles`, and the explanatory settings comment exist solely for `action_options.supports_response_format`. `ProfileValidationError` itself stays (it reports generic bound failures). `ACTION_OPTIONS_MAX_TOKENS` and the `action_options` entry in `llm_knobs`'s layer list/defaults are deleted; `LLM_ACTION_OPTIONS_*` therefore stops resolving and is not documented as an override.

**D6 — Startup loses one step, not the startup-step pattern.** `_register_action_options_layer` and its `_startup_step(...)` call are deleted from `server/conf/at_server_startstop.py`; the tolerant-registration helper and every other layer registration stay. No observability freeze entry exists for the deleted modules (verified), so the freeze list is unchanged.

**D7 — The guardrail schema registration is deleted with the layer.** `ACTION_OPTIONS_OUTPUT_SCHEMA` is registered by the layer itself (`register_action_options`), not by `world/ai/schemas/registry.py`; that registry and its `descriptor.py`/`response.py` modules are untouched. `world/ai/tests/test_guardrail.py` keeps covering the remaining layers.

**D8 — Test ownership.** Deleted modules are removed from `.github/evennia-shards.json` in the same change. `server/conf/tests/test_option_proposal_service/` needs no manifest edit because the manifest already carries the package-level `server` label; `tools/test_data_freeze.json` names the service test path and the two `world/ai` modules and loses those lines. `tools/observability_freeze.json` names neither module and is not edited.

## Delete / amend matrix

### Delete

| Path | Why |
|---|---|
| `world/ai/action_options/` (6 modules) | The whole generative layer. |
| `world/ai/tests/test_action_options_layer.py` | Pins the layer's generation, prompt, context, and registration. |
| `world/ai/tests/test_action_options_schema.py` | Pins the ladder, caps, enrichment, and JSON contract. |
| `prompts/action_options.yaml`, `prompts/tests/action_options.yaml` | The two prompt keys and their hostile fixture. |
| `server/option_proposal_service/` (6 modules) | Fingerprint use, LRU, memo, pending registry, session state, scheduling. |
| `server/conf/tests/test_option_proposal_service/` | Its five slice modules. |
| `typeclasses/tests/test_action_options_room_entry.py` | Pins the room-entry trigger. |
| `web/webclient/actions/tests/test_options_actions.py` | Pins the dismiss action. |
| `web/webclient/actions/tests/test_dispatcher/test_dialogue_trigger.py` | Pins the conversation-completion trigger. |
| `web/webclient/actions/options.py` | The dismiss validator and adapter. |

### Amend — production

| File | Change |
|---|---|
| `world/ai/profiles.py` | Drop `action_options` from `LAYER_NAMES`, `ACTION_OPTIONS_MAX_TOKENS`, and the defaults; delete `REQUIRED_PROFILE_FLAGS` and its enforcement branch; update the module docstring. |
| `world/ai/immutable.py` | Docstring only: stop naming `world/ai/action_options.py` as a consumer. |
| `world/prompts/registry.py` | Delete the two `action_options.*` `PromptSpec` entries. |
| `server/conf/llm_knobs.py` | Delete `action_options` from the layer list and the per-layer `max_tokens` defaults. |
| `server/conf/settings.py` | Comment only: profile validation now covers generic bounds. |
| `server/conf/at_server_startstop.py` | Delete `_register_action_options_layer`, its module import list entry, its `_startup_step` call, and its `STARTUP_STEP_ORDER` entry. |
| `server/conf/tests/test_startup_observability.py` | Remove `"world.ai.action_options.register_action_options"` from `_BODY_TARGETS` and any step-order expectation naming the retired step. |
| `typeclasses/characters.py` | Delete `_schedule_action_options_after_move`, `_schedule_action_options_committed`, the `at_post_move` call, and the docstring paragraphs that name them; in `_schedule_projection_refresh_after_activation` delete the `schedule_action_options` import/call while keeping the `refresh_after_command` loop and its watcher resolution. |
| `typeclasses/npcs.py` | Delete the `_schedule_action_options_after_move` import and call in `at_post_move`. |
| `typeclasses/exits.py` | Docstring only: drop the sentence naming the action-options trigger. |
| `web/webclient/actions/registry.py` | Delete the `options.dismiss` `ActionSpec` and the `validate_options_dismiss_payload`/`_dismiss_adapter` imports; update the roster docstring. |
| `web/webclient/actions/dispatcher.py` | Delete `_schedule_options_after_completion` and the terminal-combat-return schedule block (and their log events), keeping the completion publication and every result ordering. |
| `web/webclient/presentation/ingress.py` | Delete the `ui_sync`/post-command `schedule_action_options` call only; the watcher registration and the snapshot path stay. |
| `web/static/webclient/js/elosern/command_echo.js` | Remove the `options.dismiss` silent entry; the account create/switch, name-roll, and dialogue-leave controls stay declared. |
| `web/static/webclient/js/tests/command_echo_coverage_manifest.json` | Remove `options.dismiss` from both `registeredMutationActionIds` and `silentPresentationControlIds`. |
| `web/static/webclient/js/tests/command_echo.test.js` | Drop the `options.dismiss` assertions and keep the other silent-control cases. |
| `web/webclient/actions/tests/test_dispatcher/test_registry.py` | Remove `options.dismiss` from the asserted production registry set. |
| `web/webclient-app/tests/store/command_echo_surfaces.test.js` | Remove the `options.dismiss` expected-silence row. |

### Amend — tests and manifests

| File | Change |
|---|---|
| `world/ai/tests/test_profiles.py` | Delete `ActionOptionsProfileTests` and the `action_options` branch of the defaults test. |
| `prompts/tests/test_loader.py` | Delete the four `action_options` cases and the file-name set entry. |
| `server/conf/tests/test_llm_env_overrides.py` | Delete every `action_options` knob row/expectation. |
| `web/webclient/presentation/tests/test_watchers.py` | Keep every behaviour test and retarget its `covers_requirement` annotations to the new `webclient-publication-settlements` requirement (the added watcher-registry requirement), deleting the retired ones. |
| `web/webclient/actions/tests/test_combat_dispatcher.py` | Delete the `schedule_action_options` patches/assertions. |
| `world/quests/tests/test_encounter_dispatch.py` | Delete the `schedule_action_options` patch. |
| `tests/test_ai_transport_contract.py` | Delete the `action-options-layer::the-layer-is-strictly-proposal-only` and `action-options-trigger-hooks::every-trigger-is-fire-and-forget-non-raising-and-non-mutating` annotations; keep the transport-boundary assertions that do not name the retired layer. |
| `web/webclient/actions/tests/test_dispatcher/test_dispatcher_core.py` | Retarget the three `dismiss-options-action::adapters-receive-the-authenticated-session-through-a-fixed-optional-parameter` annotations to the same requirement in `webclient-action-dispatch` (it already owns the ABI). |
| `web/webclient/presentation/tests/test_fingerprints.py` | Delete the ten `action-options-trigger-service` annotations and the one test that imports `server.option_proposal_service` (`test_derivation_is_the_service_single_source`); the file itself is deleted by `retire-context-actions-suggestions`. |
| `web/webclient/presentation/tests/test_combat_panel/test_suggestions_render_path.py` | Delete the two `action-options-trigger-service` annotations; the file itself is deleted by `retire-context-actions-suggestions`. |
| `web/webclient/actions/tests/test_account_actions/test_presentation_ordering.py` | Delete the `options_barriers` fixture/assertions and the `from server.option_proposal_service import _deliver_guarded, _PendingSubscriber` block and the test that uses it. |
| `.github/evennia-shards.json` | Remove the five module labels listed in the proposal; add none. |
| `tools/test_data_freeze.json` and `tools/test_data_lint_seed.json` | Remove the same three paths from `seedDebtPaths` in **both** files in lockstep (the lint gate and `test_data_independence_*` assert they match); add none. |
| `tests/test_data_independence_ai_server.py` | Remove the three deleted modules from `MIGRATED_FILES`, remove `test_option_proposal_service` from `_SPLIT_PACKAGES`, and update the "seventeen modules" docstring to the new count. |
| `tools/observability_freeze.json` | No edit (verified no retired path is listed). |

### Amend — docs

| File | Change |
|---|---|
| `docs/development/llm-architecture.md` | Drop the `action_options.py` and `option_proposal_service.py` tree rows and any layer count. |
| `docs/development/llm-scenarios.md` | Delete the layer-table row and §6 (`行動建議卡片層`). |
| `docs/development/llm-guardrails.md` | Delete the 12-stage ladder section and the action-options mentions in the no-number and structured-output sections. |
| `docs/development/llm-configuration.md` | Drop the `action_options` MAX_TOKENS/SUPPORTS_RESPONSE_FORMAT notes. |
| `docs/development/settings-and-environment.md` | Drop the `action_options` per-layer defaults and forced-flag rows. |
| `docs/gm/prompts.md` | Drop the `action_options.yaml` tree row and the two key rows. |
| `docs/gm/overview.md` | Drop any action-options layer mention. |
| `.env.example` | Drop the `action_options` phrase in the MAX_TOKENS comment and the `LLM_ACTION_OPTIONS_MAX_TOKENS` example. |

## Risks / Trade-offs

- [A surviving module still imports a deleted one] → `grep -R "action_options\|option_proposal_service"` across the tree is the first acceptance step; the import graph is one-directional and enumerated above.
- [Deleting the trigger call sites changes movement/dialogue timing] → the calls are fire-and-forget tails; the tasks pin the focused movement, dialogue-completion, and combat-dispatch tests to prove settlement and result ordering are unchanged.
- [Traceability fails on an annotation naming a removed requirement] → annotations in `test_watchers.py` are the only survivors; the check in tasks 7 covers the whole repository.
- [`options_barriers`/`options_state` remnants look dead but stay] → deliberate: `retire-context-actions-suggestions` deletes them with the snapshot; noted in D4.
