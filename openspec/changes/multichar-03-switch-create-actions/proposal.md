## Why

With the capacity raised (`multichar-01`) and the roster on the wire (`multichar-02`), the
WebClient can *see* an account's other characters but cannot reach them. The only way to switch is
the Telnet `進入世界 <角色>` command typed into the command line, and the only way to create a
second character is a Developer-locked `charcreate`. The graphical client needs its own
account-scoped write path.

This change is also where a real architectural constraint has to be resolved rather than assumed.
A puppet transition is not an ordinary mutation: `retire_sequence` destroys the dispatcher's
in-flight marker and `reset_client_sequence` bumps the presentation epoch. An adapter that
performs the transition inline therefore returns into a `_publish_completion` whose
`state.in_flight`/epoch guard has already been invalidated, so **no `ui_action_result` is ever
sent for the request**. The browser would recover only through the `no_puppet` protocol-error
path, which releases the mutation lock but permanently marks the mutation *uncertain* — the
client would show "outcome could not be confirmed" after every successful character switch.

## What Changes

- Add `web/webclient/actions/account_actions.py` with two account-scoped actions registered in the
  production action registry:
  - `account.character.switch` — payload `{character_id}` — re-puppet another character the same
    account owns.
  - `account.character.create` — empty payload — create a fresh character shell and puppet it, so
    it falls into the existing creation wizard through its `creation_pending` marker.
- Split each action into a **synchronous decision** and a **deferred transition**: every
  authorization check (ownership, capacity, combat lock, self-target) runs at admission and
  produces the action's result immediately, while the mechanical unpuppet → puppet → snapshot
  sequence is scheduled onto the next reactor turn. The wire order becomes
  `ui_action_result` → `ui_protocol_error(no_puppet)` → fresh-epoch `ui_snapshot`, which the
  client reducer already handles with no protocol change and no uncertain-result marking.
- Both actions are result-only: they declare no affected panels and emit no completion snapshot,
  so a rejected switch attempted mid-creation cannot wipe the player's in-progress wizard form.
- The world introduction is never resent: after `multichar-01` it is bound to the login hook, and
  a mid-session puppet change does not run that hook. The reusable creation start presentation is
  sent for a newly created shell.
- Extend the WebSocket integration test with an end-to-end second-character scenario: create,
  switch back, switch forward, asserting a complete snapshot for the correct puppet after each
  transition.

## Capabilities

### New Capabilities

None. Both actions extend `webclient-character-roster`, introduced by `multichar-02`.

### Modified Capabilities

- `webclient-character-roster`: gains the two account-scoped actions, their exact payloads,
  rejection codes, deferred-transition ordering, and the guarantee that the world introduction is
  never resent.
- `webclient-action-dispatch`: the completion requirement is extended to admit the
  transition-scheduling class of action — an action whose committed effect is a puppet change must
  deliver its result and release both locks *before* the transition retires the sequence, and
  every authorization decision it reports must be made before the result is sent.

## Impact

- New: `web/webclient/actions/account_actions.py` and
  `web/webclient/actions/tests/test_account_actions.py`.
- Modified: `web/webclient/actions/registry.py` (two registrations plus the docstring's action
  inventory), `server/conf/tests/test_ui_action_integration.py`.
- Reuses unchanged: `send_unpuppet_transition`, `retire_sequence`, `reset_client_sequence`,
  `synchronize_session`, `Account.create_character`, `Account.puppet_object`.
- Depends on `multichar-01-account-capacity` (a second character must be creatable at all) and on
  `multichar-02-roster-read-model` for the shared capacity/lock vocabulary — though the adapters
  re-derive both predicates themselves and never read the panel.
- Unblocks `multichar-04-topbar-switcher-ui`.
- No client-side change: the reducer's `detached` → fresh-epoch re-establishment path already
  exists for Telnet `離開角色` / `進入世界`.
