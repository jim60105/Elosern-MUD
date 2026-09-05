# Tasks: multichar-04-character-create-action

## 1. Validator and adapter

- [ ] 1.1 `web/webclient/actions/account_actions.py`: `validate_account_character_create_payload`
  accepting exactly `{}` and raising `AccountActionError` on any field.
- [ ] 1.2 Add the module constants for this action: the `character_slots_full` code with
  「角色數量已達上限。」, the success code, and the creation-failure player line.
- [ ] 1.3 `_account_character_create_adapter(actor, payload, session)`: resolve the account from
  `actor.account`; reject `character_slots_full` (count `account.characters` against
  `django.conf.settings.MAX_NR_CHARACTERS`, read at call time) and `in_combat` synchronously;
  otherwise schedule `_perform_create` and return the success result. Every return carries
  `"no_presentation": True`.
- [ ] 1.4 `web/webclient/actions/registry.py`: register `account.character.create` with empty
  `affected_panels` and extend `build_production_action_registry`'s docstring inventory.

## 2. The creation transition

- [ ] 2.1 `_perform_create(session, account, previous)`: re-validate capacity and the combat
  predicate; then call `account.create_character()` with **no `key` override** — before any detach
  signal, retire, or puppet change. Handle both the `(None, errors)` return and a raise as a
  stop-here failure: `log_warn`, one player line, and **no** change to the session.
- [ ] 2.2 Only once a shell exists, call change 03's `_attach_puppet(session, account, shell)`. On
  verified success set `account.db._last_puppet = shell`, `synchronize_session(session, shell)`, and
  `account.msg(creation_start_screen())`. Never send `WORLD_INTRODUCTION`; never rename the shell.
- [ ] 2.3 On a failed attach, call change 03's `_recover_transition` and leave the orphaned shell in
  place. Add an explicit comment that deleting it here would be a destructive write on an error
  branch and that the roster makes it recoverable.

## 3. Tests

- [ ] 3.1 `web/webclient/actions/tests/test_account_actions.py` — validator: an empty payload is
  accepted; any field is rejected.
- [ ] 3.2 Decisions with an injected `Clock`, asserting **nothing is scheduled**: at capacity →
  `character_slots_full` with no object created; in combat → `in_combat`. Both leave
  `session.puppet` and the coordinator epoch unchanged.
- [ ] 3.3 Acceptance: the adapter returns success and `no_presentation` while the puppet is
  unchanged; advancing the clock creates the shell, attaches it, and publishes a fresh-epoch
  snapshot whose mode is `creation`; `creation_start_screen()` was sent and `WORLD_INTRODUCTION`
  was not; the shell is `creation_pending`, is in `account.characters`, and still carries Evennia's
  default key.
- [ ] 3.4 Late capacity failure — patch `create_character` to return `(None, [error])` at transition
  time: the session keeps its puppet and epoch, **no** detach signal was sent, one player line was
  delivered, a warning was logged, and no character object exists.
- [ ] 3.5 Failed attach after a successful creation — patch `puppet_object` to fail: the recovery
  ladder runs, and the created shell still exists, still belongs to the account, and is still
  `creation_pending`.
- [ ] 3.6 Abandoned-shell round trip: create a second character, leave the wizard unfinished, switch
  back to the finished character, then switch to the unfinished one and assert the snapshot resolves
  `creation` mode with the saved draft intact.
- [ ] 3.7 `covers_requirement` annotations for the three new `webclient-character-roster`
  requirements.

## 4. Integration test

- [ ] 4.1 `server/conf/tests/test_ui_action_integration.py`: end-to-end WebSocket scenario —
  activate character A, `account.character.create`, complete the wizard for B,
  `account.character.switch` back to A, then forward to B. After each transition assert a complete
  snapshot whose `status`, `character`, and `roster` panels name the correct puppet, and that every
  submitted request received a result.
- [ ] 4.2 Note in the test module that the `roster` assertions require
  `multichar-02-roster-read-model`; if this change merges first, the roster assertion must be added
  when that change lands rather than left as a silently passing weaker check.

## 5. Verification

- [ ] 5.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
  web.webclient server world commands`.
- [ ] 5.2 `uv run --locked python -m tools.observability_lint check` and
  `uv run --locked python -m tools.spec_traceability check`.
- [ ] 5.3 Live container check: fill an account to capacity and confirm the creation rejection
  leaves the session untouched; create a character below capacity and confirm the wizard appears
  with no world introduction; abandon it, switch away, and switch back to confirm the draft resumed.
