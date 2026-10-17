# Tasks

Total estimate: **6.5 hours**, including implementation, focused verification, documentation and integration. Direct prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Each group lands its own tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.25h)

- [x] 1.1 Implement exact combat.actor_choices/command/exit_prompt/exit_confirm adapters and retire old combat registrations; test all closed payloads, reserved flee and authorized commander/actor separation.
  - `web/webclient/actions/combat_actions.py` now owns the four exact validators (`validate_actor_choices_payload`, `validate_command_payload` with the closed skill/item/tactic union and its TargetSpec-dependent target forms, `validate_exit_prompt_payload`, `validate_exit_confirm_payload`) plus `validate_party_exit_prompt_data`; `validate_cast_/flee_/forfeit_payload` and the three retired adapters are gone, and `registry.py` registers exactly the four new action IDs.
  - Evidence: `web.webclient.actions.tests.test_combat_actions` (24 cases: closed payloads, reserved flee, TargetSpec shape matrix, closed tactic vocabulary, actor/commander separation, forged and absent actor references rejecting with `forbidden_actor` and no draft, round or revision change).

## 2. Bounded implementation and evidence (1.25h)

- [x] 2.1 Amend dispatcher actor-reference and registry/scale contracts without relaxing authentication; test forged actor/session references, no-puppet, extra fields and exact action allowlist.
  - Authentication is unchanged: the actor still comes only from `session.puppet`, and `actor_id`/`session_id` are accepted only inside the four exact guarded schemas, reauthorized at the rules boundary through `authorize_combat_actor`. The registry pin and the catalog lockstep (manifest, Node fixture, Vitest table) carry exactly the four IDs.
  - Evidence: `test_combat_dispatcher` (forged actor reference reaches the rules boundary and mutates nothing; an extra identity field rejects as `malformed_payload` without adapter invocation; an envelope identity field is a protocol error; the three retired IDs are `unknown_action`), `test_dispatcher.test_registry` (exact production ID set), `web.webclient.actions.tests.test_action_catalog_coverage`.

## 3. Bounded implementation and evidence (1.25h)

- [x] 3.1 Implement safe prompt/result variants, active inventory.use rejection and canonical progress-before-result publication; test nonfinal, needs-selection, stale, retry, final and terminal results.
  - Result variants are exactly the design's codes (`actor_choices`, `draft_saved`, `needs_selection`, `already_committed`, `round_committed`, `combat_terminal`, `party_exit_prompt`, `stale_command`), with the four-field bounded prompt data as the only success-data carrier and an adapter-side guard rejecting data on every other code. `service_actions._inventory_use_adapter` rejects an active-combat `inventory.use` before any target resolution with the new bounded `combat_item_command_required` reason.
  - Evidence: `test_combat_actions` (draft save, member reselection, stale session/revision/draft version, accepted-operation retry, item draft entry, exact prompt data, forged token, one settlement per confirmation plus idempotent replay), `test_combat_dispatcher` (progress publication precedes the result at one revision; the prompt result round-trips `validate_ui_action_result`), `test_inventory_actions` (the in-combat rejection with no consumption, mutation or time).

## 4. Bounded implementation and evidence (1h)

- [x] 4.1 Wire committed-round-only beat publication and requested-actor transport state/reconnect invalidation; test no pending-round beats or replay and unchanged global result-data safety.
  - Only a committed round's settlement carries the internal round record; edits, queries, prompts and idempotent replays never do. `party_actor_selection.py` holds the requested actor bound to the epoch, puppet, session and round, is retired on unpuppet, puppet change and sequence reset, and the combat panel falls back to its own default actor when a stale selection no longer resolves.
  - Evidence: `test_combat_actions` (beats record on a committed item round, unavailable form on an unmodeled HP mover, prompt/edit results carrying no round record, the actor query recording only a matching session/round and rejecting a foe or a stale revision), `test_combat_dispatcher` (the beats panel rides the update that completes the round; the actor query publishes the selected member's choices), `web/static/webclient/js/tests/protocol_core.test.js` (the prompt data and data-free combat codes in the result-envelope mirror).

## 5. Bounded implementation and evidence (0.75h)

- [x] 5.1 Update dispatcher/API docs, canonical requirement IDs, adapter fixtures and shard ownership; verify every old producer is accounted for in the client cutover dependencies.
  - Docs: module docstrings of `combat_actions.py`, `registry.py`, `dispatcher.py` (`_COMBAT_TRIGGER_ACTION_IDS`), `combat_beats.py`, `command_echo.js` and `skill_use_actions.py` name the guarded routes and the four action IDs. No player command surface changed (the text commands and both player command documents are owned unchanged by the batch's text slice), so `docs/game/*` needs no edit and `tests/test_command_docs.py` is unaffected.
  - Requirement IDs: tests for the MODIFIED requirements keep their existing main-spec annotations. The two requirements this delta REMOVES are still in `openspec/specs/`, so the tests that substantiate their preserved rule (closed scale set with absent default 1; adapters derive the actor only from the authenticated session, re-read the record, invoke only public rules APIs and assign no state) carry their IDs until the archive sync migrates them atomically with the spec removal; no new delta-only ID is annotated now because it cannot resolve before sync.
  - Fixtures and shard ownership: no test module was added, renamed or moved, so `.github/evennia-shards.json` and `.github/browser-shards.json` are unchanged (`tests.test_evennia_test_optimization_contract` is green through the contract gate's manifest check).
  - Old-producer accounting for the cutover: Python producers are retired here (`combat_actions.py`, `registry.py`, `dispatcher.py`); the client producers that still emit the retired IDs — `web/static/webclient/js/elosern/combat_menu.js` (dock rows), `web/webclient-app/stores/elosern/frames.js` / `combat.js` / `AppClient.vue` (dispatch and single-target identity), the dock/pane Vitest suites, and the CI-owned `web/tests/browser/test_browser_combat_*` acceptance — belong to the client slices (`webclient-party-command-selection`, `webclient-party-items-tactics`, `webclient-party-exit-confirmation`), and the typed combat spellings belong to `party-combat-text-commands`; the beat-binding and catalog halves that this slice owns are cut over in `beats.js`, `command_echo.js`, the coverage manifest and their suites.

## 6. Integration gate (1h)

- [x] 6.1 Run focused Python dispatcher/action/publication tests, Node result-envelope cases and tools.contract_gate; run observability lint and focused boundary tests if logging changes.
  - `uv run --locked --env-file=/tmp/mudtest.env evennia test --settings test_settings.py --keepdb web.webclient.actions.tests.test_combat_actions web.webclient.actions.tests.test_combat_dispatcher web.webclient.actions.tests.test_inventory_actions web.webclient.actions.tests.test_action_catalog_coverage` → 58 tests, OK; `... web.webclient.actions.tests.test_dispatcher` → 35, OK; `... web.webclient.actions.tests.test_service_actions` → 46, OK; `... web.webclient.presentation.tests.test_art_panel` → 40, OK; `... web.webclient.presentation.tests.test_combat_panel.test_presenter/test_party_protocol/test_schema` → 64, OK.
  - `node --test web/static/webclient/js/tests/*.test.js` → 542 tests, 542 pass, 0 fail (includes the new party-exit-prompt result-envelope cases).
  - `uv run --locked python -m tools.contract_gate` → passed: traceability (2253 requirements, 0 uncovered), observability (0 violations), test-data (0 violations), manifests, contracts (18 tests OK).
  - No logging code path changed (every log call site is untouched), so the observability lint inside the contract gate is the complete logging check.
  - `openspec validate party-combat-command-transport --strict` → valid.
  - CI-owned and therefore not run locally: the Vitest suites (the `beats` binding and the echo-surface table were updated in lockstep) and the managed browser suites.
