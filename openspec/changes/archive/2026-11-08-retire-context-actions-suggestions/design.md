# Design

## Context

See `proposal.md`. After the two dependent changes, the only remaining suggestion machinery is the wire contract and its read side. `combat_panel.py` still validates a `suggestions` key on both forms and assembles it from `PresentationContext.options_state` (always `None`) plus `default_cards()` (unreachable); `ingress.py` still snapshots `session.ndb.options_state` (never written) and derives a situation fingerprint for it; the mirror still validates the envelope and card caps. This change removes all of it and re-versions the panel.

## Goals / Non-Goals

**Goals:**

- The `context_actions` panel carries no suggestion field at any schema version, and the server and client enforce the same new closed schema at version 9.
- `PresentationContext` loses every suggestion field; no presenter can read suggestion state because no such field exists.
- `affordances.py` keeps the canonical vocabulary and loses only the suggestion-only helpers.
- Every surviving panel, action, dock, and vocabulary behaviour is byte-identical apart from the removed key and the version number.

**Non-Goals:**

- Do not change any other panel's schema version, any action payload, or any presenter output other than `context_actions`.
- Do not remove `AffordanceView`, `exploration_affordances`, `in_exploration_mode`, `ACTION_CODE_ALLOWLIST`, `SURFACES`, or `MAX_AFFORDANCES`.
- Do not touch the dock (already retired) or the client's remaining view store.

## Decisions

**D1 — Bump 8 → 9 rather than reuse 8.** The panel is a strict closed schema with a dual-direction parity contract and an exact-field validator on both sides. Removing a required field is an observable wire change; keeping version 8 would let a stale client or fixture that still sends `suggestions` pass an older build and fail opaquely. Version 9 makes the break explicit in one number that both mirrors must agree on, and the existing parity contract enforces that agreement.

**D1a — Version-bearing requirement headings keep their identity.** The `webclient-context-actions` and `webclient-combat-menu` requirement headings embed earlier version numbers ("version-7", "version-5 field set"); the delta schema forbids renaming a requirement, so each block's body states version 9 and the heading stays as the requirement's identity. A future capability-wide retitle is out of scope.

**D2 — The field is rejected as an unknown key, not ignored.** Both the Python `_require_exact_fields` calls and the JS `requireExactFields` calls keep their exact key sets; removing `suggestions` from the set means a payload carrying it rejects. No lenient path is added.

**D3 — Delete the whole read side in one change.** `OptionsSnapshot`, `FrozenCard`, `options_state`, `options_fingerprint`, `options_snapshot`, `_current_options_fingerprint`, and `fingerprints.py` form one chain: only the (deleted) trigger service and the (deleted) suggestion section ever consumed them. Removing them together avoids leaving a frozen dataclass with no reader and a fingerprint derivation with no consumer.

**D4 — `affordances.py` loses only suggestion-only helpers.** `canonical_json` was used by the deleted digest/fingerprint only; `MAX_CARDS` capped suggestion cards; `SUGGESTIBLE_ACTION_IDS`, `suggestible_candidates`, `default_cards`, and `eligible_affordance_digest` existed for the ladder/service/presenter. The vocabulary builders, `AffordanceView`, `exploration_affordances`, `in_exploration_mode`, `ACTION_CODE_ALLOWLIST`, `SURFACES`, and `MAX_AFFORDANCES` are untouched.

**D5 — Parity contract trims, does not vanish.** `tests/test_context_actions_parity_contract.py` keeps its combat participant-condition bound check (annotated to `webclient-combat-menu`) and loses the four suggestion-parity tests; the file name and shard row stay so no manifest churn is needed. `tests/test_panel_schema_version_parity_contract.py` keeps enforcing that the registry constant, the mirror allowlist, and the presenter's form checks all read 9 on both sides.

**D6 — Fixture churn is scoped by panel.** Only `context_actions` fixtures move to version 9 and drop the key. `services` (8), `character` (9), `status` (1), and every other panel keep their literals; a blanket version edit would corrupt unrelated tests.

**D7 — `webclient-character-roster`'s session-state requirement keeps its other subjects.** The requirement also covers the transient creation concept proposal, the completed-result cache, and the in-flight marker; only the options-state and dismissal-barrier clauses are removed, and the two suggestion-named scenarios are reworded as absence assertions (the delta schema forbids renaming scenarios).

## Delete / amend matrix

### Delete

| Path | Why |
|---|---|
| `web/webclient/presentation/options.py` | The envelope/card bounds and `validate_suggestions`/`_validate_suggestion_card`/freeform pin. Its surviving affordance-params validator and registry move to the new `affordance_params.py` first (task 1.1). |
| `web/webclient/presentation/fingerprints.py` | Situation fingerprint and digests; its only consumers were the trigger service (deleted) and the suggestion presenter gate. |
| `web/static/webclient/js/elosern/protocol/panels/suggestions.js` | The client envelope/card mirror. |
| `web/webclient/presentation/tests/test_fingerprints.py` | Pins the deleted fingerprint module. |
| `web/webclient/presentation/tests/test_combat_panel/test_suggestions_envelope.py` | Pins the removed envelope validators. |
| `web/webclient/presentation/tests/test_combat_panel/test_suggestions_render_path.py` | Pins the removed snapshot-to-cards render path. |
| `web/webclient/presentation/tests/test_combat_panel/test_options_and_validators.py` | Its `OptionsSnapshotFactoryTests` and the suggestion-params test pin deleted code; the two surviving affordance-validator tests move to `test_affordance_params.py`. |
| `web/webclient/presentation/tests/test_affordances/test_default_cards.py` | Pins `default_cards()`/`suggestible_candidates()`. |

### Amend — production

| File | Change |
|---|---|
| `web/webclient/presentation/affordance_params.py` (new) | Holds `FREEFORM_ACTION_CODE`, the `_ACTION_PAYLOAD_VALIDATORS` table, and `validate_affordance_params` moved from `options.py`; imports the action validators and the protocol error only. |
| `web/webclient/presentation/combat_panel.py` | `CONTEXT_ACTIONS_SCHEMA_VERSION = 9`; remove `suggestions` from both exact-field sets and both serialized results; delete `_suggestions_section` and `_serialize_suggestions_card`; import `validate_affordance_params` from the new module and drop `validate_suggestions`, `OPTIONS_STATUSES`, `default_cards`, and the unused protocol-error import; update the docstring and version note. |
| `web/webclient/presentation/exploration.py` | Import `validate_affordance_params` from the new module. |
| `web/webclient/presentation/context.py` | Delete `FrozenCard`, `OptionsSnapshot`, `options_state`, and `options_fingerprint` fields and docstrings; keep `ProposalSnapshot` and every other field. |
| `web/webclient/presentation/ingress.py` | Delete `options_snapshot`, `_current_options_fingerprint`, the `options_state`/`options_barriers` reset lines, and the corresponding `build_presentation_context` arguments; keep the watcher registration, concept-proposal snapshot, and every other factory input. |
| `web/webclient/presentation/affordances.py` | Delete `MAX_CARDS`, `SUGGESTIBLE_ACTION_IDS`, `suggestible_candidates`, `default_cards`, `eligible_affordance_digest`, `canonical_json`, and their `__all__`/docstring references. |
| `web/static/webclient/js/elosern/protocol.js` | Remove the `panels/suggestions.js` import and ALL ten option exports: `validateSuggestions`, `validateSuggestionCard`, `OPTIONS_STATUSES`, `OPTIONS_CARD_KINDS`, `MAX_OPTION_CARDS`, `MAX_OPTION_LABEL`, `MAX_OPTION_HINT`, `MAX_OPTION_PARAMS`, `OPTIONS_FREEFORM_ACTION_CODE`, `OPTIONS_MAX_PARAM_STRING`. |
| `web/static/webclient/js/elosern/protocol/constants.js` | `CONTEXT_ACTIONS_SCHEMA_VERSION = 9`; delete `OPTIONS_STATUSES`, `OPTIONS_CARD_KINDS`, `MAX_OPTION_CARDS`, `MAX_OPTION_LABEL`, `MAX_OPTION_HINT`, `MAX_OPTION_PARAMS`, `OPTIONS_MAX_PARAM_STRING`, and the freeform pin. |
| `web/static/webclient/js/elosern/protocol/panels/combat.js` | Reject/ignore nothing: remove `suggestions` from both exact key sets, both normalized results, and the "combat suggestions must be exactly unavailable" gate; drop the `suggestions` import. |
| `web/static/webclient/js/elosern/protocol/panels/skill_descriptor.js` | Comment only: the params gate no longer mentions suggestion cards. |

### Amend — tests

| File | Change |
|---|---|
| `web/webclient/presentation/tests/test_combat_panel/_support.py` | Drop `suggestions` from the combat/exploration/unavailable fixtures and delete `_suggestion_card`/`_ready_suggestions` and the imported option caps. |
| `web/webclient/presentation/tests/test_combat_panel/{test_schema,test_presenter,test_exploration_form,test_party_protocol,test_off_anchor}.py` | Version 9, no `suggestions` key; delete the suggestion-specific assertions and the `OptionsSnapshot` constructions. |
| `web/webclient/presentation/tests/test_presentation_context.py` | Delete the options snapshot/fingerprint tests; keep the concept-proposal and publication-path tests. |
| `web/webclient/presentation/tests/test_protocol.py`, `test_registry.py` | Update the pinned version and any exact-key list. |
| `web/webclient/presentation/tests/test_affordances/test_contract.py` | Drop the `SUGGESTIBLE_ACTION_IDS`, `default_cards`, `suggestible_candidates`, and `MAX_CARDS` imports and their tests. |
| `web/webclient/presentation/tests/test_affordances/test_vocabulary.py` | Delete the suggestion-eligibility tests and the `default_cards` assertions; keep the vocabulary tests. |
| `web/webclient/actions/tests/test_account_actions/_support.py` | Drop the `FrozenCard`/`OptionsSnapshot` import and the options-state construction. |
| `web/webclient/actions/tests/test_account_actions/test_presentation_ordering.py` | Delete the `options_state` fixture/assertions the earlier change left behind. |
| `web/webclient/presentation/tests/test_possession_presentation.py` | Drop the `SUGGESTIBLE_ACTION_IDS`/`default_cards` imports and the `default_cards` call/assertions. |
| `web/webclient/presentation/tests/test_affordances/{__init__,_support,test_delivery,test_rules}.py` | Drop the `MAX_CARDS`/`SUGGESTIBLE_ACTION_IDS`/`default_cards`/`suggestible_candidates` imports and assertions; update the package docstring. |
| `web/static/webclient/js/tests/hud_dock_menus.test.js` | Move the `context_actions` fixture to version 9 and delete the `suggestions` key/envelope helper. |
| `web/webclient-app/tests/frame-resolvers.test.js` | Move `combatActions` to version 9 and delete its `suggestions` key. |
| `web/tests/browser/_journey_support.py` | Move `_exploration_context_actions_panel` and `_combat_panel` to version 9 and delete their `suggestions` keys; every caller then inherits the new shape. |
| `web/tests/browser/test_vue_foundation.py`, `web/tests/browser/test_browser_exploration_state.py` | Update the two `context_actions` literals to version 9 with no `suggestions` key. |
| `tests/test_context_actions_parity_contract.py` | Delete the option-bound pairs, fragments, and the three option tests; keep the combat participant-condition bound test and retitle the module docstring. |
| `tests/test_panel_schema_version_parity_contract.py` | No structural change expected (it reads constants); re-run it and fix only a literal that the version bump exposes. |
| `web/static/webclient/js/tests/protocol_context_actions_a.test.js` | Delete the `validateSuggestions` test block and the `normalized.suggestions` assertion; version 9. |
| `web/static/webclient/js/tests/protocol_context_actions_b.test.js` | Version 9; drop the `suggestions` key from the exact key list and the unavailable-form rejection fixture. |
| `web/static/webclient/js/tests/protocol_fixtures.js`, `combat_menu.test.js` | Version 9 for `context_actions` fixtures; delete `validSuggestions` and the `suggestions` keys. |
| `web/webclient-app/tests/protocol_fixtures.js` | Version 9 for the exploration/combat `context_actions` fixtures. |
| `.github/evennia-shards.json` | Remove the five deleted module labels. |

## Risks / Trade-offs

- [A fixture that pins the old version hides in an unexpected file] → task 6 runs the Python presentation package and checks `CONTEXT_ACTIONS_SCHEMA_VERSION` references; task 7 runs the Node protocol tests and the panel-version parity contract, which names every mismatch.
- [The mirror and server disagree on the exact key set] → `tests/test_context_actions_parity_contract.py` and the panel-version parity contract both run in tasks 6/7.
- [Deleting `canonical_json` breaks an unexpected importer] → `grep -RIn canonical_json` is the first acceptance step; only the deleted fingerprint module and its tests imported it.
- [Traceability breaks on an annotation in a surviving test] → task 8 runs the check and names the offending requirement; the retired IDs are gone from the index at sync.
- [The audit document or another spec still cites the retired capability] → verified: the audit cites `webclient-options-surface` (already retargeted by the first change) and no `suggestions` requirement; this change touches no docs.
