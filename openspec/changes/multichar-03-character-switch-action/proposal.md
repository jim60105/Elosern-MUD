## Why

With the capacity raised (`multichar-01`) and the roster on the wire (`multichar-02`), the
WebClient can *see* an account's other characters but cannot reach them. The only way to switch is
the Telnet `進入世界 <角色>` command typed into the command line.

This change builds the account-scoped write path and the puppet-transition machinery that
`multichar-04-character-create-action` will reuse. It carries a real architectural constraint that
has to be resolved rather than assumed: a puppet transition is not an ordinary mutation.
`retire_sequence` destroys the dispatcher's in-flight marker and `reset_client_sequence` bumps the
presentation epoch, so an adapter that performs the transition inline returns into a
`_publish_completion` whose guard has already been invalidated and **no `ui_action_result` is ever
sent**. The browser would recover only through the `no_puppet` protocol-error path, which releases
the mutation lock but permanently marks the mutation *uncertain* — the client would show "outcome
could not be confirmed" after every successful character switch.

A second constraint, found in Evennia's own source, shapes the failure handling: `puppet_object`
returns silently rather than raising on several conditions, and its
`MAX_NR_SIMULTANEOUS_PUPPETS` guard returns **after** it has already unpuppeted the session's
previous character. A transition that does not verify its own outcome can therefore leave the
account fully OOC while reporting success.

## What Changes

- Add `web/webclient/actions/account_actions.py` with the account-scoped
  `account.character.switch` action (payload `{character_id}`), registered in the production action
  registry, plus the shared puppet-transition machinery.
- Split the action into a **synchronous decision** and a **deferred transition**: ownership, the
  combat lock, and the already-current check run at admission and produce the result immediately,
  while the mechanical transition is scheduled onto the next reactor turn. The wire order becomes
  `ui_action_result` → `ui_protocol_error(no_puppet)` → fresh-epoch `ui_snapshot`, which the client
  reducer already handles with no protocol change and no uncertain-result marking.
- Make the transition **verify its own outcome** and recover: the session's previous character is
  never unpuppeted by the helper itself (Evennia's `puppet_object` does that internally, after its
  own guards), the helper asserts the session actually holds the requested puppet afterwards, and a
  failure walks an explicit recovery ladder ending in an unambiguous message to the player.
- The action is result-only: it declares no affected panels and emits no completion snapshot, so a
  rejected switch attempted mid-creation cannot wipe the player's in-progress wizard form.

## Capabilities

### New Capabilities

None. The action extends `webclient-character-roster`, introduced by `multichar-02`.

### Modified Capabilities

- `webclient-character-roster`: gains `account.character.switch`, its exact payload and rejection
  codes, the deferred-transition ordering, the transition's verify-and-recover contract, and the
  guarantee that no state crosses the character boundary.
- `webclient-action-dispatch`: the completion requirement is extended to admit the
  transition-scheduling class of action — one whose committed effect retires the very sequence its
  result would be published into.

## Impact

- New: `web/webclient/actions/account_actions.py` and
  `web/webclient/actions/tests/test_account_actions.py`.
- Modified: `web/webclient/actions/registry.py` (one registration plus the docstring's action
  inventory).
- Reuses unchanged: `send_unpuppet_transition`, `retire_sequence`, `reset_client_sequence`,
  `synchronize_session`, `Account.puppet_object`.
- Depends on `multichar-01-account-capacity` (a second character must exist to switch to) and on
  `multichar-02-roster-read-model` for the shared capacity/lock vocabulary — though the adapter
  re-derives every predicate itself and never reads the panel.
- Unblocks `multichar-04-character-create-action` (which reuses the transition machinery) and
  `multichar-05-topbar-switcher-ui`.
- No client-side change: the reducer's `detached` → fresh-epoch re-establishment path already
  exists for Telnet `離開角色` / `進入世界`.
