## Why

A codebase audit of the merged `multichar-01`..`05` work found that `account.character.switch`
and `account.character.create` (`web/webclient/actions/account_actions.py`) decide synchronously
and schedule their real puppet transition one reactor turn later, but nothing stops a *second*
request from the same session being admitted, deciding, and reporting `"outcome": "success"`
while the *first* request's transition is still pending. When the second transition's deferred
callback finally runs, it finds `account.get_puppet(session)` no longer matches the puppet it
captured at admission (the first transition already ran) and silently cancels through the
existing stale-puppet branch — a server-side `log_warn` only, with no player-visible message. The
client was already told the second action succeeded; nothing about it actually happened. This is
exactly the "reported success but nothing happened" failure class the whole
decide-synchronously/verify-and-recover architecture (`multichar-03-character-switch-action`,
`multichar-04-character-create-action`) was built to eliminate for a *single* in-flight request —
it was never extended to guard the window between two overlapping admissions. No existing test
exercises this: the one "stale puppet" test reassigns `session.puppet` directly from test code,
not through a second admitted action.

Separately, `multichar-01-account-capacity` removed the two module-level bindings in
`commands/localized/account.py` that were the only consumers of `from django.conf import
settings`, but left the import itself in place as dead code.

## What Changes

- Add a per-session "transition pending" marker that `account.character.switch` and
  `account.character.create` both set synchronously at admission (the moment a request is
  accepted and its transition scheduled) and clear only when the scheduled transition actually
  finishes — on success, or on any of the three recovery-ladder rungs, or on the existing
  stale-puppet-cancels-cleanly path.
- Reject a second `account.character.switch` or `account.character.create` admitted for a session
  that already has a transition pending, synchronously, with a new stable code/message
  (`transition_pending` / 「角色切換正在進行中，請稍候。」), scheduling nothing.
- Delete the unused `from django.conf import settings` import in
  `commands/localized/account.py`.

No behavior changes for the already-shipped single-request paths: every existing recovery-ladder
rung, rejection code, and the wire ordering (`ui_action_result` → detach signal → fresh-epoch
snapshot) stay exactly as specified. This change only closes the multi-request admission gap and
removes dead code; no backward compatibility or migration concerns apply (pre-release, no users).

## Capabilities

### New Capabilities
(none)

### Modified Capabilities
- `webclient-character-roster`: adds a requirement that a session with a puppet transition already
  scheduled (from a prior `account.character.switch` or `account.character.create`) refuses a
  further character-changing action synchronously, rather than admitting it and letting it be
  silently dropped later.

## Impact

- `web/webclient/actions/account_actions.py`: new per-session pending-transition tracking, a new
  rejection code/message, an admission check in both adapters, and clearing the marker at every
  exit path of `_perform_switch`/`_perform_create` (including all three `_recover_transition`
  rungs and the stale-puppet-cancel branch).
- `web/webclient/actions/tests/test_account_actions.py`: new tests for the rejection, for the
  marker clearing correctly after each completion path, and a regression check that the full
  existing single-request suite (recovery rungs 1/2/3, late revalidation failures, externally
  reassigned `session.puppet`) is unaffected.
- `commands/localized/account.py`: delete one unused import line. No behavior change.
- No new client-visible codes need wiring beyond a message string — the client already renders any
  `outcome: rejected` result generically; no protocol/schema version bump.
