# Proposal

## Why

The client half of the AI 建議 surface is gone (`retire-action-options-webclient`). What remains is the backend that produced it: a whole generative layer (bounded-context serializer, prompt, 12-stage validation ladder, retry/degrade pipeline), an LLM profile slot, a prompt file, a trigger service with a fingerprint/LRU/negative-memo/dismissal-barrier machine, three deterministic trigger hooks, an `options.dismiss` action, and a session presentation state that nothing reads. None of it serves the deterministic game, which must stay fully playable with every LLM offline, and it is the only advisory layer in the engine. Delete it.

## What Changes

- **BREAKING**: delete `world/ai/action_options/` (cards, context, ladder, prompt, generation), its guardrail registration, and the `action_options` output schema.
- **BREAKING**: delete `prompts/action_options.yaml`, its two registry entries, the `action_options` slot in `LAYER_NAMES`/`default_profiles()`, the `RequIRED` structured-output flag rule, and the `LLM_ACTION_OPTIONS_*` knobs (`.env.example`, `server/conf/llm_knobs.py`, docs).
- **BREAKING**: delete `server/option_proposal_service/` (fingerprint, LRU cache, negative memo, pending registry, session options state, epoch-guarded push, scheduling), the room-entry trigger in `typeclasses/characters.py`/`npcs.py`, the dialogue-completion and terminal-combat trigger in `web/webclient/actions/dispatcher.py`, and the `ui_sync` schedule call in `web/webclient/presentation/ingress.py`.
- **BREAKING**: unregister `options.dismiss` and delete `web/webclient/actions/options.py`; the action roster and the client catalog's declared silent-control list lose the id (the other declared silent controls stay).
- Move the watcher-registry contract to `webclient-publication-settlements`, where every surviving targeted push already consumes it, instead of retiring a mechanism that other surfaces rely on.
- Delete the binder, guardrail last-line group, and every retired test/prompt/doc reference; `.github/evennia-shards.json` and `tools/test_data_freeze.json` lose their entries in the same change.

Non-goals: the `context_actions.suggestions` field, its validator, the panel schema version, the `OptionsSnapshot`/`FrozenCard` read side, `default_cards`/`suggestible_candidates`/`eligible_affordance_digest`, and the `webclient-context-actions-suggestions` capability. They still compile against an always-absent state and are removed by `retire-context-actions-suggestions`, which depends on this change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `action-options-layer`, `ai-action-options-prompts`, `ai-action-options-schema`, `action-options-trigger-service`, `action-options-trigger-hooks`, `dismiss-options-action`: REMOVED — six whole capabilities (40 requirements).
- `llm-profiles`: the registry maps six layers; the retired slot is rejected like any unknown key and no required-flag rule runs.
- `settings-environment-overrides`: the per-layer secret-merge example uses a surviving layer instead of the retired `action_options` knob.
- `webclient-action-dispatch`: the production roster and composition lose `options.dismiss`; the three-argument adapter ABI stays where it already lives.
- `webclient-input-narrative`: the catalog's silent-control declaration loses `options.dismiss`; every other registered mutation action still resolves to a line.
- `webclient-publication-settlements`: gains the ingress-maintained watcher-registry requirement moved from the trigger hooks.

## Impact

- Code: delete `world/ai/action_options/`, `server/option_proposal_service/`, `prompts/action_options.yaml`, `web/webclient/actions/options.py`; amend `world/ai/profiles.py`, `world/prompts/registry.py`, `server/conf/{settings,llm_knobs,at_server_startstop}.py`, `typeclasses/{characters,npcs,exits}.py`, `web/webclient/actions/{registry,dispatcher}.py`, `web/webclient/presentation/ingress.py`.
- Tests deleted: `world/ai/tests/test_action_options_{layer,schema}.py`, `server/conf/tests/test_option_proposal_service/`, `typeclasses/tests/test_action_options_room_entry.py`, `web/webclient/actions/tests/test_options_actions.py`, `web/webclient/actions/tests/test_dispatcher/test_dialogue_trigger.py`, `prompts/tests/action_options.yaml`.
- Tests amended: `world/ai/tests/test_profiles.py`, `prompts/tests/test_loader.py`, `server/conf/tests/test_llm_env_overrides.py`, `web/webclient/presentation/tests/test_watchers.py` (annotations only), `web/webclient/actions/tests/test_combat_dispatcher.py`, `world/quests/tests/test_encounter_dispatch.py`, `web/webclient/actions/tests/test_account_actions/test_presentation_ordering.py`.
- Manifests: `.github/evennia-shards.json` removes the five now-missing module labels (`world.ai.tests.test_action_options_layer`, `world.ai.tests.test_action_options_schema`, `typeclasses.tests.test_action_options_room_entry`, `web.webclient.actions.tests.test_dispatcher.test_dialogue_trigger`, `web.webclient.actions.tests.test_options_actions`); `server/conf/tests/test_option_proposal_service/` is covered by the shard's package-level `server` label, so no entry is added. `tools/test_data_freeze.json` removes `server/conf/tests/test_option_proposal_service.py`, `world/ai/tests/test_action_options_layer.py`, and `world/ai/tests/test_action_options_schema.py`. `tools/observability_freeze.json` has no matching entry and is not edited.
- Docs: `docs/development/llm-architecture.md`, `llm-scenarios.md` (§6 plus the layer table row), `llm-guardrails.md` (ladder and no-number rule), `llm-configuration.md`, `settings-and-environment.md`, `docs/gm/prompts.md`, `docs/gm/overview.md`, `.env.example`.
- Architectural source of truth: `docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md` never names the action-options layer, so it is not amended; the five dated `2026-08-15-ai-action-options-*` design documents are retained as historical provenance for the archived changes that cite them.
- Player commands: unaffected; no command name, alias, or syntax changes, so `docs/game/commands.md` and `command-reference.md` stay untouched.
- Spec traceability: every annotation naming a retired requirement is removed in this change; `uv run --locked python -m tools.spec_traceability check` must pass after apply.
- Human review: none required.

## Batch:

Part of the AI action-suggestions retirement batch.

depends-on: retire-action-options-webclient

Code-conflict notes: apply second. The client no longer reads `suggestions`, so deleting the writer cannot leave a rendered surface behind. It edits `web/webclient/presentation/ingress.py` and `web/webclient/actions/dispatcher.py`, which `retire-context-actions-suggestions` edits again to delete the read side; apply in order. It and the webclient change both edit `.github/evennia-shards.json` (different labels).
