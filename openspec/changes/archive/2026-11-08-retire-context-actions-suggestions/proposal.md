# Proposal

## Why

The client surface and the backend writer are gone. What still exists is the wire contract they shared: the `context_actions.suggestions` envelope (and its validator, mirror, parity test, card caps, and freeform pin), plus the presentation read side that fed it — `OptionsSnapshot`/`FrozenCard` on `PresentationContext`, the ingress snapshot/fingerprint factory, `presentation/fingerprints.py`, and the suggestion-eligibility/degradation helpers in `affordances.py`. Every one of them now renders or computes from an always-absent state. Delete them and bump the panel version so the closed-schema contract states the new shape.

## What Changes

- **BREAKING**: remove the `suggestions` field from both `context_actions` available forms and bump the panel schema version from 8 to 9 on the server and in the client mirror.
- **BREAKING**: delete `web/webclient/presentation/options.py` (envelope/card bounds and validators), moving its surviving affordance-params validator into a new `web/webclient/presentation/affordance_params.py` consumed by `combat_panel.py` and `exploration.py`; delete `web/static/webclient/js/elosern/protocol/panels/suggestions.js` and the mirror's `validateSuggestions`/`validateSuggestionCard` exports plus `OPTIONS_STATUSES`, `OPTIONS_CARD_KINDS`, and `MAX_OPTION_*`.
- **BREAKING**: delete `PresentationContext.options_state`/`options_fingerprint`, `OptionsSnapshot`, `FrozenCard`, the ingress `options_snapshot`/`_current_options_fingerprint` factories and reset lines, and `web/webclient/presentation/fingerprints.py`.
- **BREAKING**: delete `suggestible_candidates`, `SUGGESTIBLE_ACTION_IDS`, `default_cards`, `eligible_affordance_digest`, `canonical_json`, and `MAX_CARDS` from `affordances.py`; the canonical vocabulary, `AffordanceView`, `exploration_affordances`, `in_exploration_mode`, and `ACTION_CODE_ALLOWLIST` stay.
- Retire the `webclient-context-actions-suggestions` capability and rewrite the requirements that named the envelope or the eligibility set: `context_actions`, `webclient-combat-menu`, `exploration-affordances`, `webclient-exploration-menu`, `webclient-character-roster`, `webclient-possession-presentation`.
- Update every `context_actions` fixture to version 9 (other panels keep their own versions), delete the retired test modules, drop their shard labels, and trim the parity contract to its surviving combat-bound check.

Non-goals: no behaviour change to any surviving panel, the exploration vocabulary's entries, the dock, the action dispatch, or the LLM layers. No new suggestion mechanism.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `webclient-context-actions-suggestions`: REMOVED — the whole capability (five requirements).
- `webclient-context-actions`: version 9, both forms without `suggestions`, exact-field rejection of the retired key.
- `webclient-combat-menu`: version 9 combat form without `suggestions`.
- `exploration-affordances`: "Suggestion eligibility derives executable cards" and "The deterministic degradation fallback derives rule cards" REMOVED; the validator-normalization, idle-baseline, and vocabulary requirements lose their suggestion references.
- `webclient-exploration-menu`: `explore.talk_open` and the server-authored-affordance requirement lose their suggestion wording.
- `webclient-character-roster`: the puppet-change requirement loses the options state and dismissal barrier; the concept proposal and result cache stay.
- `webclient-possession-presentation`: the possession-controls scenario reports the vocabulary-only truth.

## Impact

- Code: new `web/webclient/presentation/affordance_params.py`; amend `web/webclient/presentation/{context,combat_panel,affordances,ingress,exploration}.py`; delete `presentation/{options,fingerprints}.py`; amend `web/static/webclient/js/elosern/protocol.js`, `protocol/constants.js`, `protocol/panels/{combat,skill_descriptor}.js`; delete `protocol/panels/suggestions.js`.
- Tests deleted: `web/webclient/presentation/tests/test_fingerprints.py`, `test_combat_panel/test_suggestions_envelope.py`, `test_combat_panel/test_suggestions_render_path.py`, and `test_affordances/test_default_cards.py`; `test_combat_panel/test_options_and_validators.py` is renamed to `test_combat_panel/test_affordance_params.py` keeping only its two surviving validator tests.
- Tests amended: the `context_actions` fixtures in `web/webclient/presentation/tests/**`, `tests/test_context_actions_parity_contract.py` (trim to the combat-bound check), `tests/test_panel_schema_version_parity_contract.py` (version 9), `web/static/webclient/js/tests/protocol_context_actions_{a,b}.test.js`, `protocol_fixtures.js`, `combat_menu.test.js`, `web/webclient-app/tests/protocol_fixtures.js`, `test_affordances/{test_contract,test_vocabulary}.py`.
- Manifests: `.github/evennia-shards.json` removes `web.webclient.presentation.tests.test_fingerprints`, `…test_combat_panel.test_suggestions_envelope`, `…test_suggestions_render_path`, and `…test_affordances.test_default_cards`, and replaces `…test_combat_panel.test_options_and_validators` with `…test_combat_panel.test_affordance_params`; `tests.test_context_actions_parity_contract` stays registered (amended). `tools/test_data_freeze.json` and `tools/observability_freeze.json` have no matching entry and are not edited.
- Docs: none beyond the capability text and the change artifacts; `docs/development/webclient-vue-frozen-contract-audit.md` cites no `suggestions` requirement and is untouched here.
- Spec traceability: the retired capability's requirement IDs and every annotation pinned by the deleted modules disappear in this change; `uv run --locked python -m tools.spec_traceability check` must pass after apply.
- Human review: none required.

## Batch:

Part of the AI action-suggestions retirement batch.

depends-on: retire-action-options-service

Code-conflict notes: apply last. `retire-action-options-service` already deleted the writer, so the snapshot/eligibility read side here has no producer; `retire-action-options-webclient` already deleted the only client readers. This change touches `web/webclient/presentation/{context,ingress,combat_panel,affordances}.py` and the protocol mirror, which the earlier two changes also touched (disjoint hunks), so apply in order.
