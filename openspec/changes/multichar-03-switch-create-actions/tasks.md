# Tasks: multichar-03-switch-create-actions

## 1. Adapter module skeleton and validators

- [ ] 1.1 `web/webclient/actions/account_actions.py`: module docstring stating the
  decide-synchronously / transition-later contract and *why* (an inline transition retires the
  sequence `_publish_completion` guards on, so the request would receive no result).
- [ ] 1.2 Stable codes and Traditional Chinese messages as module constants:
  `invalid_character` /「那不是你的角色。」, `in_combat` /「戰鬥中無法切換角色。」,
  `already_current` /「你已經在這個角色上了。」, `character_slots_full` /「角色數量已達上限。」,
  plus the success codes and the transition-failure line.
- [ ] 1.3 `validate_account_character_switch_payload`: exactly `{character_id}`, `type(value) is
  int` (booleans excluded), positive. `validate_account_character_create_payload`: exactly `{}`.
  Both raise the module's `AccountActionError` on any violation.

## 2. The scheduling seam and the transition helper

- [ ] 2.1 Module-level injectable clock following `world/ai/client.py`'s idiom: a private
  `_clock` defaulting to the global Twisted reactor and a test-facing setter/override, so unit
  tests inject `twisted.internet.task.Clock`. Schedule with a zero delay.
- [ ] 2.2 `_perform_switch(session, account, character_id)`: re-resolve the target inside
  `account.characters`; re-check `is_in_active_session` on the current puppet; then
  `account.unpuppet_object(session)` → `send_unpuppet_transition(session)` →
  `retire_sequence(session)` → `reset_client_sequence(session)` →
  `account.puppet_object(session, target)` → `account.db._last_puppet = target` →
  `synchronize_session(session, target)`, mirroring `CmdOOC.func`'s sequence exactly.
- [ ] 2.3 `_perform_create(session, account)`: the same leave sequence, then
  `account.create_character()` (no `key` override; `at_post_create_character` sets the pending
  marker), handling Evennia's `(None, [errors])` slot return as a re-validation failure; then
  puppet, `_last_puppet`, `synchronize_session`, and deliver `creation_start_screen()` as
  narrative text. Never send `WORLD_INTRODUCTION`; never rename the shell.
- [ ] 2.4 Shared failure path for both: keep the current puppet, `log_error` with account,
  session, and target identity in `context`, `account.msg` a Traditional Chinese failure line, and
  publish a fresh snapshot for whatever puppet the session still holds.

## 3. Adapters and registration

- [ ] 3.1 `_account_character_switch_adapter(actor, payload, session)`: resolve the account from
  `actor.account`; reject `invalid_character` / `in_combat` / `already_current` synchronously;
  otherwise schedule `_perform_switch` and return the success result. Every return carries
  `"no_presentation": True`.
- [ ] 3.2 `_account_character_create_adapter(actor, payload, session)`: reject
  `character_slots_full` (count against `settings.MAX_NR_CHARACTERS`, read at call time) and
  `in_combat` synchronously; otherwise schedule `_perform_create` and return the success result,
  also `no_presentation`.
- [ ] 3.3 `web/webclient/actions/registry.py`: register both with empty `affected_panels`, and
  extend `build_production_action_registry`'s docstring inventory to name the two account actions.

## 4. Backend tests

- [ ] 4.1 `web/webclient/actions/tests/test_account_actions.py` — validators: exact payload
  shapes, boolean/negative/extra/missing-field rejection for both actions.
- [ ] 4.2 Switch decisions with an injected `Clock`, asserting **nothing is scheduled**:
  foreign id → `invalid_character`; in combat → `in_combat`; own current puppet →
  `already_current`; each leaves `session.puppet` and the coordinator epoch unchanged.
- [ ] 4.3 Switch acceptance: the adapter returns success and `no_presentation` while the puppet is
  still unchanged; advancing the clock performs the transition; afterwards `session.puppet` is the
  target, `account.db._last_puppet` is the target, and a fresh-epoch snapshot was sent.
- [ ] 4.4 Create decisions and acceptance under the same clock split: at capacity →
  `character_slots_full` with no object created; in combat → `in_combat`; accepted → after the
  clock advances, a new pending shell exists, is puppeted, resolves the `creation` snapshot mode,
  and the creation start presentation was sent while `WORLD_INTRODUCTION` was not.
- [ ] 4.5 Transition-failure path: force `puppet_object` to raise inside the scheduled call and
  assert the session keeps its previous puppet, the error event is emitted, the player receives the
  failure line, and a snapshot is published.
- [ ] 4.6 Ordering test through the real dispatcher: submit a switch and assert the recorded
  session messages are `ui_action_result`, then `ui_protocol_error(no_puppet)`, then
  `ui_snapshot` at a different epoch — and that the result was sent at all (the regression this
  change exists to prevent).
- [ ] 4.7 Cross-puppet isolation: committed action-option cards and a transient concept proposal
  on the old character are absent from the new puppet's first snapshot, and a generation settling
  after the switch publishes nothing.

## 5. Integration test

- [ ] 5.1 `server/conf/tests/test_ui_action_integration.py`: end-to-end WebSocket scenario —
  activate character A, `account.character.create`, complete the wizard for B,
  `account.character.switch` back to A, then forward to B, asserting after each transition a
  complete snapshot whose `status`, `character`, and `roster` panels name the correct puppet, and
  that no request is left without a result.

## 6. Verification

- [ ] 6.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
  web.webclient server world commands`.
- [ ] 6.2 `uv run --locked python -m tools.observability_lint check` (the failure path adds a
  `log_error` call site) and `uv run --locked python -m tools.spec_traceability check`, with
  `covers_requirement` annotations for the five new roster requirements and the modified dispatch
  requirement.
- [ ] 6.3 Live container check: from a browser session, switch between two characters repeatedly
  and confirm no "outcome could not be confirmed" notice appears; attempt a switch during combat
  and confirm the rejection; fill the account to capacity and confirm the creation rejection.
