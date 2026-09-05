# Tasks: multichar-03-character-switch-action

## 1. Adapter module skeleton and validator

- [ ] 1.1 `web/webclient/actions/account_actions.py`: module docstring stating the
  decide-synchronously / transition-later contract and *why* (an inline transition retires the
  sequence `_publish_completion` guards on, so the request would receive no result), plus the
  verify-and-recover contract and why it exists (Evennia's `puppet_object` can refuse silently,
  and its `MAX_NR_SIMULTANEOUS_PUPPETS` guard refuses *after* releasing the previous puppet).
- [ ] 1.2 Stable codes and Traditional Chinese messages as module constants:
  `invalid_character` /「那不是你的角色。」, `in_combat` /「戰鬥中無法切換角色。」,
  `already_current` /「你已經在這個角色上了。」, the success code, and the three recovery lines
  (kept-current, repaired, and no-character-at-all naming `進入世界`).
- [ ] 1.3 `validate_account_character_switch_payload`: exactly `{character_id}`,
  `type(value) is int` (booleans excluded), positive. Raises the module's `AccountActionError` on
  any violation.

## 2. The scheduling seam

- [ ] 2.1 Module-level injectable clock following `world/ai/client.py`'s idiom: a private `_clock`
  defaulting to the global Twisted reactor and a test-facing override, so unit tests inject
  `twisted.internet.task.Clock`. Schedule with a zero delay.

## 3. The shared transition helper (reused by multichar-04)

- [ ] 3.1 `_attach_puppet(session, account, target)`: send `send_unpuppet_transition(session)` →
  `retire_sequence(session)` → `reset_client_sequence(session)` →
  `account.puppet_object(session, target)`, then **verify** `account.get_puppet(session) is target`
  and return that boolean. Do **not** call `account.unpuppet_object(session)` first — Evennia's
  `puppet_object` owns that internally, after its own guards, so a guard refusal leaves the
  previous character attached.
- [ ] 3.2 `_recover_transition(session, account, previous, target, cause)`: the three-rung ladder —
  (1) session still holds `previous` → `log_warn`, player line, `synchronize_session(previous)`;
  (2) session holds nothing but `_attach_puppet(previous)` verifies → `log_error`, player line,
  `synchronize_session(previous)`; (3) that also fails → `log_error` with account, session,
  previous and target identities, the explicit "you hold no character, use 進入世界" line, and no
  snapshot. Every rung emits exactly one player-visible line through `account.msg`.
- [ ] 3.3 `_perform_switch(session, account, character_id, previous)`: re-resolve the target inside
  `account.characters` and re-check `is_in_active_session(previous)`; on failure go straight to
  rung 1 without sending the detach signal. Otherwise `_attach_puppet`, and on success set
  `account.db._last_puppet = target` and `synchronize_session(session, target)`; on failure call
  `_recover_transition`.

## 4. Adapter and registration

- [ ] 4.1 `_account_character_switch_adapter(actor, payload, session)`: resolve the account from
  `actor.account`; reject `invalid_character` / `in_combat` / `already_current` synchronously;
  otherwise schedule `_perform_switch` and return the success result. Every return carries
  `"no_presentation": True`.
- [ ] 4.2 `web/webclient/actions/registry.py`: register `account.character.switch` with empty
  `affected_panels`, and extend `build_production_action_registry`'s docstring inventory.

## 5. Tests

- [ ] 5.1 `web/webclient/actions/tests/test_account_actions.py` — validator: exact payload shape;
  boolean, negative, non-integer, extra, and missing-field rejection.
- [ ] 5.2 Decisions with an injected `Clock`, asserting **nothing is scheduled**: foreign id →
  `invalid_character`; in combat → `in_combat`; own current puppet → `already_current`; each leaves
  `session.puppet` and the coordinator epoch unchanged.
- [ ] 5.3 Acceptance: the adapter returns success and `no_presentation` while the puppet is still
  unchanged; advancing the clock performs the transition; afterwards `session.puppet` is the target,
  `account.db._last_puppet` is the target, and a fresh-epoch snapshot was sent.
- [ ] 5.4 Recovery rung 1 — `puppet_object` patched to return silently without releasing the
  previous puppet: the session still holds the previous character, one player line was sent, a
  warning was logged, and a fresh snapshot for the previous character was published.
- [ ] 5.5 Recovery rung 2 — `puppet_object` patched to release the previous puppet and then return
  silently on the first call but succeed on the re-attach: the session ends holding the previous
  character, an error was logged, and a fresh snapshot for it was published.
- [ ] 5.6 Recovery rung 3 — `puppet_object` patched to fail every time after releasing: the session
  holds no puppet, an error carrying the account/session/previous/target identities was logged, the
  explicit no-character line naming `進入世界` was sent, and **no** snapshot was published.
- [ ] 5.7 Late re-validation failure — the target is removed from `account.characters`, or the
  character enters combat, between the result and the clock advance: no detach signal, no puppet
  change, one player line, and the current character's refreshed snapshot.
- [ ] 5.8 Ordering test through the real dispatcher: submit a switch and assert the recorded session
  messages are `ui_action_result`, then `ui_protocol_error(no_puppet)`, then `ui_snapshot` at a
  different epoch — and that the result was sent at all (the regression this change exists to
  prevent).
- [ ] 5.9 Cross-puppet isolation: committed action-option cards and a transient concept proposal on
  the old character are absent from the new puppet's first snapshot, and a generation settling after
  the switch publishes nothing. Assert the old character's quest progress and party binding are
  unchanged.
- [ ] 5.10 `covers_requirement` annotations for the six new `webclient-character-roster`
  requirements and the modified `webclient-action-dispatch` requirement.

## 6. Verification

- [ ] 6.1 `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb
  web.webclient server world commands`.
- [ ] 6.2 `uv run --locked python -m tools.observability_lint check` (the recovery ladder adds
  `log_warn` / `log_error` call sites) and
  `uv run --locked python -m tools.spec_traceability check`.
- [ ] 6.3 Live container check: from a browser session with two characters, switch back and forth
  repeatedly and confirm no "outcome could not be confirmed" notice appears and the stage fully
  re-renders each time; attempt a switch during combat and confirm the rejection leaves the combat
  UI untouched.
