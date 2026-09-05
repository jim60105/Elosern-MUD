## Context

`account.character.switch` and `account.character.create`
(`web/webclient/actions/account_actions.py`) both follow the decide-synchronously /
schedule-the-transition contract established by `multichar-03`/`multichar-04`: the adapter makes
every authorization decision immediately and returns a plain `dict` result (never a `Deferred`),
then schedules the actual puppet transition (`_perform_switch` / `_perform_create`) via
`get_clock().callLater(0, ...)`.

Because the adapter's result is a plain dict, `web/webclient/actions/dispatcher.py` treats the
action as complete the instant the adapter returns: `_invoke_adapter` publishes the result and
`_settle_in_flight` clears `state.in_flight` synchronously, in the same call stack, before the
scheduled transition has run. The browser's own `dispatchAction` in-flight guard
(`web/webclient-app/stores/elosern.js`) clears the same way — as soon as it receives that first,
early `ui_action_result` — and `presentation_epoch` has not advanced yet either, since the epoch
only bumps when the transition's `reset_client_sequence`/`synchronize_session` actually run.

Nothing today stops a second `account.character.switch`/`account.character.create` from the same
session being admitted in that window. It re-reads `session.puppet` (still whatever it was before
the first transition ran), decides against it, and schedules its own transition. When that second
transition's callback fires, `account.get_puppet(session)` no longer matches the `previous` it
captured — the first transition already ran — and it takes the existing "stale puppet" exit: one
`log_warn`, no player message, no snapshot for the request that thought it succeeded. The player
was told `"outcome": "success"`; nothing they asked for happened.

## Goals / Non-Goals

**Goals:**
- Guarantee that at most one puppet transition is ever scheduled-but-not-yet-run per session.
- Make a second character-changing request arriving while one is pending fail loudly and
  synchronously (a normal rejection result) instead of being silently dropped after reporting
  success.
- Leave every already-shipped single-request behavior — the three recovery rungs, the rejection
  codes, the wire ordering, the read-only re-validation inside the scheduled callback — completely
  unchanged.
- Remove the dead `settings` import in `commands/localized/account.py`.

**Non-Goals:**
- Debouncing or rate-limiting on the client. The client already avoids optimistic UI and sends no
  more requests than the player triggers; this change only has to make the *server* refuse to
  accept a second request while one is still resolving, which also protects against a
  non-browser client (or a buggy/malicious one) that sends both requests deliberately.
- Any change to `MAX_NR_SIMULTANEOUS_PUPPETS`, `MULTISESSION_MODE`, or the roster/action wire
  schemas. No panel-version or protocol-version bump.
- Cross-session concurrency (two different sessions/accounts racing each other). Each account's
  puppet transitions are already session-scoped; this change only serializes *one* session against
  *itself*.

## Decisions

### D1: The marker lives on `session.ndb`, not a module-level dict

`account_actions.py` already reaches into `session.ndb` indirectly through
`reset_client_sequence`/`retire_sequence`, and the wider webclient presentation layer's convention
for exactly this kind of "ephemeral, session-scoped, must never survive a reload or leak across
sessions" state is a `session.ndb.<name>` attribute (`elosern_actor_id`, `elosern_dispatch`,
`options_state`, `concept_proposal`). A module-level `dict` keyed by session would duplicate what
`ndb` already gives for free — automatic per-session isolation, automatic cleanup when the session
object is garbage-collected, no risk of a leaked entry for a session that disconnects mid-transition
— and would be the first departure from that convention in this module. `session.ndb` wins with no
real alternative worth weighing.

The attribute is named `session.ndb.elosern_char_transition_pending`, a plain boolean, matching the
`elosern_`-prefixed cross-cutting session markers rather than the unprefixed per-panel ones (those
are the coordinator's own state; this is the account-actions module's).

### D2: One shared marker for both actions, not one per action type

A pending `account.character.switch` transition and a pending `account.character.create`
transition are both, from the session's point of view, "a puppet transition is about to happen to
this session." Both mutate `session.puppet` through the same `_attach_puppet` helper and both must
block *any* second character-changing request, not just a same-type one — a switch immediately
followed by a create-confirm is exactly as dangerous as two switches. A single shared boolean
avoids the false sense of safety a pair of independently-tracked flags would give (someone adding a
third character-changing action later would have to remember to gate against both existing flags
individually) and matches the proposal's framing of "a transition is pending" as one session-level
fact, not a per-action-type one.

### D3: The marker is a plain boolean, not a token/generation counter

The natural worry with a "pending" flag is a stale one blocking forever, or two transitions
overlapping if the flag is cleared at the wrong moment. Both are avoided by construction rather
than by tracking a generation:

- **No two transitions can ever be scheduled concurrently**, because the check happens
  synchronously at admission, before `callLater` is issued, and the marker itself is set
  synchronously immediately after `callLater` succeeds (see D6 for why that specific ordering
  matters) — all within the same, uninterrupted adapter call. A second admission arriving after
  that call returns sees the marker already set and is rejected before it can schedule anything.
  There is therefore only ever zero or one scheduled-but-pending transition per session — nothing a
  token would need to disambiguate.
- **The marker cannot be cleared too early**, because it is cleared from inside the scheduled
  callback itself (`_perform_switch`/`_perform_create`), in a `try/finally` wrapping the entire
  callback body (see D4) — not from the synchronous adapter, and not from any of the individual
  early-return branches (stale puppet, late capacity/combat re-check, recovery rungs 1–3), so
  every exit path clears it exactly once.

A token would earn its complexity only if two transitions *could* legitimately overlap and needed
telling apart; that case cannot occur here, so a boolean is the correct, simplest tool.

### D4: Clear the marker with `try/finally` around the whole scheduled callback, not at each return

`_perform_switch` and `_perform_create` each have several early-return branches (stale puppet
cancels cleanly; late re-validation failure; the three `_recover_transition` rungs plus its
"unexpected puppet" branch; the success path). Threading an explicit clear call through every one
of them is exactly the kind of place a future edit adds a new branch and forgets it. Instead, the
adapters' scheduled entry points wrap their existing bodies in:

```python
def _perform_switch(session, account, character_id, previous):
    try:
        ...existing body, unchanged...
    finally:
        _clear_transition_pending(session)
```

and the same for `_perform_create`. This guarantees the marker clears on every exit — normal
return, an early return, or an uncaught exception escaping the callback entirely (which would
otherwise leave the session permanently unable to switch or create again) — without touching the
existing branch logic at all.

### D5: Where the admission check sits, and its rejection code

The check is the *first* thing both adapters do, before resolving `actor.account`, before the
combat check, before resolving the target — it needs only `session`, is the cheapest possible
check, and there is no reason to do any other work before potentially rejecting on it:

```python
TRANSITION_PENDING_CODE = "transition_pending"
TRANSITION_PENDING_MESSAGE = "角色切換正在進行中，請稍候。"
```

Both adapters return `{"outcome": "rejected", "code": TRANSITION_PENDING_CODE, "message":
TRANSITION_PENDING_MESSAGE, "no_presentation": True}` when the marker is already set, exactly
mirroring the shape every other rejection in this module already uses. No new client-side handling
is required: the client already renders any `outcome: rejected` result generically (there is
nothing switch/create-specific about how a rejection is displayed), so this needs no protocol
version bump and no client code change.

Because the pending check runs first, it also takes precedence over every other rejection: a
second request that is *both* pending-blocked and would otherwise fail for its own reason (a
foreign `character_id`, an in-combat session, or `already_current`) is rejected as
`transition_pending`, not as the reason it would otherwise have failed for. This ordering is
deliberate — the caller cannot distinguish "your target was invalid" from "your target might have
been fine, but a transition was already running" if a later check ran first and answered on stale
information — and is worth a dedicated scenario and test so a future reordering of the checks
cannot silently violate it (see the delta spec's precedence scenario and tasks.md 3.2).

### D6: Set the marker only after scheduling succeeds, not before

Task 2.1/2.2's admission path does two things once a request is accepted: schedule the transition,
and record that one is now pending. These must happen in **schedule-then-set** order, not
set-then-schedule: `clock.callLater(0, _perform_switch, ...)` is called first, and
`_set_transition_pending(session)` only afterward, immediately before the adapter returns its
success result.

The reason is a narrow but real leak the reverse order would introduce. `try/finally` (D4) only
protects the window *after* the transition has actually been scheduled — it guards the body of
`_perform_switch`/`_perform_create` themselves, which cannot run at all until scheduling succeeds.
If the marker were set *before* the `callLater` call and that call itself somehow failed (reactor
shutdown, or any other synchronous failure between the two statements), the marker would be left
permanently set with nothing ever scheduled to clear it, silently locking that session out of
every future character-changing action for the rest of the process's life.

Scheduling first removes the failure window entirely: Twisted's single-threaded reactor guarantees
a `callLater(0, ...)` callback cannot run until the current call stack returns control to the event
loop, so setting the marker immediately after a successful `callLater(...)` call — still within the
same synchronous adapter call, with no thread or coroutine boundary in between — can never race the
callback itself. If `callLater(...)` were to raise, it does so before the marker is ever set, so
there is nothing to clean up; the exception propagates out of the adapter and is caught by the
dispatcher's existing `_invoke_adapter` error handling exactly like any other adapter failure, with
no special case needed here.

### D7: The dead-import cleanup rides in the same change

Deleting `from django.conf import settings` from `commands/localized/account.py` (unused since
`multichar-01` removed its last two readers) has no behavioral surface, no spec-level requirement,
and no test beyond "the module still imports and the existing localized-command tests still pass."
It shares no code with the transition-pending work and is included here only because it was found
in the same audit and is too small to justify its own change.

## Risks / Trade-offs

- **[Risk] A legitimate rapid retry (e.g. the player's first click silently failed to reach the
  server) is now rejected with `transition_pending` instead of being queued or retried.** →
  Mitigation: this is the correct behavior, not a regression — the alternative is the exact bug
  this change exists to close. The window is bounded by a single reactor turn (`callLater(0,
  ...)`), so in practice the marker clears before a human could plausibly react to a rejection and
  retry; a `transition_pending` rejection is itself evidence the *first* request is about to
  complete, and the next snapshot will reflect its outcome.
- **[Risk] Forgetting to clear the marker on some future new exit path added to `_perform_switch`
  or `_perform_create`.** → Mitigation: the `try/finally` wrapper (D4) makes this structurally
  impossible for any exit that returns or raises from within the wrapped body — a future branch
  cannot forget the clear because it never has to remember it.
- **[Trade-off] The marker is per-session `ndb`, so it does not survive a server reload.** →
  Accepted: neither does anything else about an in-flight `callLater` transition (Evennia does not
  persist scheduled Twisted calls across a reload either), so this introduces no new inconsistency
  — a reload during the sub-second transition window was already an edge case outside this
  mechanism's reach, and the worst case (the marker reset to unset) only ever makes the *next*
  request more permissive, never less safe, since at most one real transition can still be
  in-flight regardless.

## Migration Plan

Not applicable — this is an in-place fix to code that shipped in the same pre-release codebase with
no external consumers. No data migration, no phased rollout, no rollback plan beyond a normal
revert.

## Open Questions

None. The mechanism is fully determined by the existing single-in-flight-transition invariant the
codebase already relies on elsewhere (the dispatcher's own `state.in_flight`/`state.epoch` pair
guards the same class of problem for regular actions); this change applies the same shape of
guard to the one path that structurally cannot use the dispatcher's own guard, because that guard
is scoped to the synchronous call, not the deferred transition.
