# Tasks

## 1. Delete the wire validators and the read side

- [x] 1.1 Create `web/webclient/presentation/affordance_params.py` with `FREEFORM_ACTION_CODE`, the `_ACTION_PAYLOAD_VALIDATORS` table, and `validate_affordance_params`, moved verbatim from `options.py`; point `combat_panel.py` and `exploration.py` at it; then delete `options.py`, `fingerprints.py`, and `web/static/webclient/js/elosern/protocol/panels/suggestions.js`.
- [x] 1.2 Delete `test_fingerprints.py`, `test_combat_panel/test_suggestions_envelope.py`, `test_combat_panel/test_suggestions_render_path.py`, and `test_affordances/test_default_cards.py`; rename `test_combat_panel/test_options_and_validators.py` to `test_combat_panel/test_affordance_params.py`, keeping only `test_action_payload_validators_covers_allowlist` and `test_unregistered_action_code_payload_validation_rejects_cleanly` (imports retargeted to `affordance_params`) and deleting the snapshot class, the suggestion-params test, and every suggestion annotation.
- [x] 1.3 `web/webclient/presentation/context.py`: delete `FrozenCard`, `OptionsSnapshot`, `options_state`, and `options_fingerprint`; keep `ProposalSnapshot`.
- [x] 1.4 `web/webclient/presentation/ingress.py`: delete `options_snapshot`, `_current_options_fingerprint`, the two `options_state`/`options_barriers` reset pairs, and the `build_presentation_context` arguments that carried them. Keep the watcher registration and the concept-proposal snapshot.
- [x] 1.5 Delete the residual comments that name the retired snapshot/eligibility concepts: `web/webclient/actions/creation_actions.py`, `web/webclient/presentation/context.py`, and `web/webclient/presentation/coordinator.py`.
- [x] 1.6 `web/webclient/presentation/affordances.py`: delete `MAX_CARDS`, `SUGGESTIBLE_ACTION_IDS`, `suggestible_candidates`, `default_cards`, `eligible_affordance_digest`, and `canonical_json`, with their `__all__` entries and docstring sentences. Confirm `AffordanceView`, `exploration_affordances`, `in_exploration_mode`, `ACTION_CODE_ALLOWLIST`, `SURFACES`, and `MAX_AFFORDANCES` still export.

## 2. Re-version the panel and drop the field

- [x] 2.1 `web/webclient/presentation/combat_panel.py`: set `CONTEXT_ACTIONS_SCHEMA_VERSION = 9`; delete `suggestions` from the exploration form's and both combat forms' exact-field sets and serialized results; delete `_suggestions_section`, `_serialize_suggestions_card`, and the now-unused imports; update the docstring and the version note.
- [x] 2.2 `web/static/webclient/js/elosern/protocol/constants.js`: `CONTEXT_ACTIONS_SCHEMA_VERSION = 9`; delete the `OPTIONS_*`/`MAX_OPTION_*` constants and the freeform pin.
- [x] 2.3 `web/static/webclient/js/elosern/protocol/panels/combat.js`: remove the `suggestions` import, both exact key-set entries, both normalized `suggestions` results, and the "combat suggestions must be exactly unavailable" gate.
- [x] 2.4 `web/static/webclient/js/elosern/protocol.js`: remove the suggestions import and the `validateSuggestions`, `validateSuggestionCard`, `OPTIONS_STATUSES`, `OPTIONS_CARD_KINDS`, and `MAX_OPTION_CARDS` exports.
- [x] 2.5 `web/static/webclient/js/elosern/protocol/panels/skill_descriptor.js`: comment only.

## 3. Amend the surviving presentation tests

- [x] 3.1 `web/webclient/presentation/tests/test_combat_panel/_support.py`: drop the `suggestions` keys, `_suggestion_card`, `_ready_suggestions`, and the option-cap imports; every fixture is version 9.
- [x] 3.2 `test_schema.py`, `test_presenter.py`, `test_exploration_form.py`, `test_party_protocol.py`, `test_off_anchor.py`: update the pinned version and exact-key lists, delete the suggestion-specific assertions (including the `OptionsSnapshot` construction), and keep every other assertion.
- [x] 3.3 `test_presentation_context.py`: delete the options snapshot/fingerprint classes and the `_options_state` helper; keep the concept-proposal and publication-path coverage.
- [x] 3.4 `test_protocol.py`, `test_registry.py`: update any pinned `context_actions` version or exact key set; leave every other panel's version alone.
- [x] 3.5 `test_affordances/{__init__,_support,test_contract,test_delivery,test_rules,test_vocabulary}.py`: delete the imports, fixtures, and assertions for `SUGGESTIBLE_ACTION_IDS`, `default_cards`, `suggestible_candidates`, and `MAX_CARDS`; update the package docstring; keep the vocabulary, delivery, possess, and rule tests.
- [x] 3.6 `web/webclient/actions/tests/test_account_actions/_support.py` and `test_presentation_ordering.py`: drop the `FrozenCard`/`OptionsSnapshot` import and the `options_state` fixture/assertions. `web/webclient/presentation/tests/test_possession_presentation.py`: drop the `SUGGESTIBLE_ACTION_IDS`/`default_cards` imports and call.

## 4. Trim the repository contracts

- [x] 4.1 `tests/test_context_actions_parity_contract.py`: delete the `_OPTIONS_*` tables and the three option-parity tests and their annotations; keep `test_participant_condition_bound_is_identical` and retitle the module docstring.
- [x] 4.2 `tests/test_panel_schema_version_parity_contract.py`: run it; if a `context_actions` literal remains, update it to 9. Do not change another panel's version.
- [x] 4.3 `.github/evennia-shards.json`: remove `web.webclient.presentation.tests.test_fingerprints`, `web.webclient.presentation.tests.test_combat_panel.test_suggestions_envelope`, `web.webclient.presentation.tests.test_combat_panel.test_suggestions_render_path`, and `web.webclient.presentation.tests.test_affordances.test_default_cards`, and replace `web.webclient.presentation.tests.test_combat_panel.test_options_and_validators` with `web.webclient.presentation.tests.test_combat_panel.test_affordance_params`; keep `tests.test_context_actions_parity_contract` registered.
- [x] 4.4 `tools/test_data_freeze.json` and `tools/observability_freeze.json`: confirm no deleted path is listed (expected: no edit); do not add entries.

## 5. Amend the client mirror tests

- [x] 5.1 `web/static/webclient/js/tests/protocol_context_actions_a.test.js`: delete the `validateSuggestions` block, drop the normalized `suggestions` assertion, and move its `context_actions` fixtures to version 9.
- [x] 5.2 `web/static/webclient/js/tests/protocol_context_actions_b.test.js`: version 9 in the unavailable and available forms; drop `suggestions` from the exact key list and the rejection fixture.
- [x] 5.3 `web/static/webclient/js/tests/protocol_fixtures.js` and `combat_menu.test.js`: version 9 for `context_actions` fixtures only; delete `validSuggestions` and every `suggestions` key.
- [x] 5.4 `web/webclient-app/tests/store/protocol_fixtures.js`: version 9 for the exploration and combat `context_actions` fixtures only.
- [x] 5.5 `web/static/webclient/js/tests/hud_dock_menus.test.js` and `web/webclient-app/tests/frame-resolvers.test.js`: version 9 and no `suggestions` key in their `context_actions` fixtures.
- [x] 5.6 `web/tests/browser/_journey_support.py`: version 9 and no `suggestions` key in `_exploration_context_actions_panel` and `_combat_panel`; `web/tests/browser/test_vue_foundation.py` and `test_browser_exploration_state.py`: update their two `context_actions` literals to match.

## 6. Python verification

- [x] 6.1 `grep -RIn "OptionsSnapshot\|FrozenCard\|options_state\|options_fingerprint\|default_cards\|suggestible_candidates\|eligible_affordance_digest\|canonical_json" --exclude-dir=.git --exclude-dir=__pycache__ web world server tests openspec/specs` returns only this change's artifacts, archived changes, and any surviving requirement text retired in the same commit.
- [x] 6.2 `uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_combat_panel web.webclient.presentation.tests.test_presentation_context web.webclient.presentation.tests.test_affordances web.webclient.presentation.tests.test_protocol web.webclient.presentation.tests.test_registry` passes.
- [x] 6.3 `uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb tests.test_context_actions_parity_contract tests.test_panel_schema_version_parity_contract` passes at version 9.
- [x] 6.4 `uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_exploration_panel web.webclient.tests.test_webclient_contract` passes (the exploration form and the frozen envelope still validate).

## 7. Client verification

- [x] 7.1 `node --test web/static/webclient/js/tests/protocol_context_actions_a.test.js web/static/webclient/js/tests/protocol_context_actions_b.test.js web/static/webclient/js/tests/protocol_core.test.js web/static/webclient/js/tests/protocol_fixtures.js` passes.
- [x] 7.2 `pnpm exec vitest run web/webclient-app/tests/` passes.
- [x] 7.3 `pnpm run build` succeeds (the deleted module has no remaining import).

## 8. Gates

- [x] 8.1 No annotation names a retired requirement. `uv run --locked python -m tools.contract_gate --change retire-context-actions-suggestions` passes its traceability stage, which tolerates the six requirements this change retires until archive sync; the standalone `uv run --locked python -m tools.spec_traceability check` still reports exactly those six as uncovered (verified pre-sync) and passes only after os-archive syncs the delta.
- [x] 8.2 `uv run --locked --env-file=.env.test evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract tests.test_webclient_frozen_contract` passes.
- [x] 8.3 `openspec validate retire-context-actions-suggestions --strict` passes.
- [x] 8.4 `uv run --locked python -m tools.contract_gate --change retire-context-actions-suggestions` passes.
- Archive hand-off (8.5, sync): the stale Purpose sentences that named the removed surface are owned by os-archive and edited in the sync commit, not by apply, because they are a manual Purpose rewrite rather than a requirement delta. Rewrite exactly these four: `openspec/specs/webclient-room-actions/spec.md` ("ask for suggestions"), `openspec/specs/webclient-context-actions/spec.md` ("plus the state-backed `suggestions` envelope"), `openspec/specs/exploration-affordances/spec.md` ("the deterministic `default_cards()` degradation derivation" and the later-suggestions note), and `openspec/specs/webclient-frame-resolution/spec.md` ("status-driven suggestions frames").
