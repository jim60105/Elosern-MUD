## Context

The relevant machinery, read from the tree rather than assumed:

**Server dispatch** (`web/webclient/actions/dispatcher.py`)

`handle_ui_action` validates the envelope, checks the epoch and base revision against the live
coordinator, looks up the spec, validates the payload, then sets `state.in_flight = True` and
`state.epoch = coordinator.epoch` before calling `_invoke_adapter`. A synchronous adapter's return
value goes straight into `_publish_completion`, which begins:

```python
coordinator = attach_coordinator(session, registry)
state = _sequence_state(session)
if not state.in_flight or state.epoch != epoch or coordinator.epoch != epoch:
    _settle_in_flight(session, epoch, None)
    return value          # nothing is sent
```

`retire_sequence(session)` sets `state.epoch = None` **and** `ndb.elosern_dispatch = None`
(`dispatcher.py:109-122`), so a subsequent `_sequence_state` call rebuilds a fresh state with
`in_flight = False`. `reset_client_sequence(session)` calls `coordinator.reset()`, producing a new
epoch (`ingress.py:118-131`). `synchronize_session(session, new_actor)` additionally retires the
sequence itself, through `_coordinator_for`'s actor-change branch (`ingress.py:72-97`).

Therefore an adapter that performs the transition inline trips all three guard clauses at once and
`_publish_completion` returns having sent nothing.

**Client reduction** (`web/static/webclient/js/elosern/protocol.js`,
`web/webclient-app/stores/elosern.js`)

- An **active** store rejects a snapshot whose epoch differs from the active one
  (`protocol.js:5245-5275`). Only `idle`, `awaiting_initial_snapshot`, and `detached` adopt a fresh
  epoch, and only from a full snapshot.
- `ui_protocol_error` with `code: "no_puppet"` is the sole transition into `detached`
  (`protocol.js:5311-5319`): it clears panels and locks mutations while retaining the active epoch
  so a late no-puppet rejection is still accepted.
- The store observes that transition and, at `stores/elosern.js:1009-1011`, does
  `if (prev.phase !== "detached" && rs.phase === "detached" && inFlight) { uncertain = true;
  inFlight = null; }`.

So: driving the client to `detached` is **mandatory** (an active store would otherwise discard the
new puppet's snapshot), and doing it while a request is in flight **necessarily** marks that
request uncertain. The only ordering that yields a clean switch is: result first, transition
second.

**Evennia's `puppet_object`** (`evennia/accounts/accounts.py:459-555`)

Its control flow is load-bearing for the failure design:

- It returns **silently** (a player message, no exception) when the session already puppets the
  object (479), when the account lacks the `puppet` lock (483), and when the object is puppeted by
  another connected account (512).
- All three of those returns happen **before** line 517-519, where it unpuppets the session's
  previous puppet. So an early guard failure leaves the session's current character intact.
- The `MAX_NR_SIMULTANEOUS_PUPPETS` guard (525-539) returns silently **after** that unpuppet. It is
  reachable — `MAX_NR_SIMULTANEOUS_PUPPETS` is `1` by Evennia default and the project never
  overrides it — and leaves the session with **no puppet at all**.
- Only "Object not found" / "Session not found" raise `RuntimeError`, and both precede the
  unpuppet.

**Existing precedents relied on**

- `CmdOOC.func` is the reference OOC sequence: `unpuppet_object` → `send_unpuppet_transition` →
  `retire_sequence` → `reset_client_sequence`.
- `_publish_completion` already supports a result-only completion via the internal
  `no_presentation` flag on a `success`/`rejected` outcome (introduced for `creation.roll_name`,
  namegen-creation-ui D10); the flag is stripped by `_normalize_result` and never reaches the wire.
- `world/ai/client.py` injects its reactor (`twisted.internet.task.Clock` in tests) rather than
  patching the module global — the project's established scheduling idiom.

## Goals / Non-Goals

**Goals:**

- One allowlisted account-scoped switch action with an exact payload, stable codes, and
  Traditional Chinese messages, going through the existing registry/dispatcher with no new
  transport concept.
- A wire order that leaves the browser in a clean, certain state after a switch.
- Every authorization decision made and reported synchronously, so the result never promises
  something that has not been decided.
- A transition that cannot silently strand the account OOC, and that says so out loud when it
  cannot complete.
- Reusable transition machinery for `multichar-04-character-create-action`.
- No cross-account puppeting reachable through this surface, ever.

**Non-Goals:**

- No `account.character.create` — that is `multichar-04-character-create-action`, which adds a
  second caller to the helper built here.
- No UI. The dropdown and its confirmation are `multichar-05-topbar-switcher-ui`.
- No character deletion.
- No concurrent multi-window puppeting; `MULTISESSION_MODE` and `MAX_NR_SIMULTANEOUS_PUPPETS` are
  untouched.
- No new Telnet command; `進入世界` already switches.

## Decisions

### D1 — Decision synchronously, transition on the next reactor turn

The adapter:

1. Runs every check synchronously: does the target resolve inside `account.characters`, is the
   actor in an active combat session, is the target already the current puppet.
2. On rejection, returns `{"outcome": "rejected", code, message, "no_presentation": True}` and
   schedules nothing.
3. On acceptance, schedules the transition through an injectable clock seam
   (`reactor.callLater(0, ...)` in production) and returns
   `{"outcome": "success", code, message, "no_presentation": True}`.

`_publish_completion` then runs at the still-live epoch, sends the result, and releases the
in-flight marker. On the next reactor turn the transition runs, the client goes `detached`, and the
fresh-epoch snapshot re-establishes it.

Alternative considered — **do the work inline and accept the uncertain flag**: rejected, because
`uncertain` is player-visible "outcome could not be confirmed" state that would be shown after
every *successful* switch, which is simply false.

Alternative considered — **a new inbound OOB envelope** (`ui_character_switch`) handled in
`server/conf/inputfuncs.py`, bypassing the dispatcher: rejected.
`tests/test_webclient_frozen_contract.py` freezes the seven envelope names and the
`window.Elosern.Protocol` façade; a new envelope means a frozen-contract amendment, a new
validator, new client plumbing, and a second dispatch path with its own duplicate/stale/busy
semantics. The action registry already provides all of it.

Alternative considered — **a dispatcher post-send hook** instead of a reactor turn: rejected as
more invasive for the same ordering guarantee. It would put transition-awareness into the generic
dispatcher for the benefit of two adapters.

### D2 — What "success before the work" does and does not promise

The result reports the outcome of the **decision**, not of the mechanical transition, and this is
stated as a requirement rather than left implicit. Under Evennia's single-threaded Twisted reactor,
the adapter call and `_publish_completion` run back-to-back in one stack frame
(`dispatcher.py:271-290`), so nothing can invalidate the sequence between admission and the result
being sent, and the zero-delay call cannot fire before it.

### D3 — The transition never pre-unpuppets, and always verifies

This is the correction that Evennia's control flow forces. The helper does **not** call
`account.unpuppet_object(session)` itself. `puppet_object` performs that unpuppet internally at
line 517-519, *after* all three of its silent-return guards — so letting it own the unpuppet means
a guard failure leaves the session's current character intact instead of stranding it OOC.

`send_unpuppet_transition(session)` is still sent explicitly, because it is the client's `detached`
signal and nothing else produces it. It is only an OOB message; sending it before a transition that
then fails is harmless, because the recovery path re-synchronizes at a fresh epoch and the detached
client adopts that snapshot.

Order inside the scheduled call:

1. Re-validate against committed state: the target still resolves inside `account.characters`, and
   the current puppet is still not in an active combat session. A failed re-validation stops here,
   before anything is sent or changed.
2. `send_unpuppet_transition(session)` → `retire_sequence(session)` →
   `reset_client_sequence(session)`.
3. `account.puppet_object(session, target)`.
4. **Verify**: `account.get_puppet(session) is target`. This is the step that catches
   `puppet_object`'s silent returns, including the `MAX_NR_SIMULTANEOUS_PUPPETS` one that returns
   after the internal unpuppet.
5. On success: `account.set_last_puppet(target)`, then `synchronize_session(session, target)`.

### D4 — An explicit three-rung recovery ladder

If step 1 fails, or step 3 raises, or step 4's verification fails, the helper resolves what the
session actually holds and takes the highest rung that applies:

1. **The session still holds its previous character** (every early-guard case, and re-validation
   failure): log a warning, tell the player in Traditional Chinese that the switch did not happen
   and which character they are still playing, and `synchronize_session` that character. The
   detached client adopts the fresh-epoch snapshot and is fully recovered.
2. **The session holds no puppet and the previous character can be re-puppeted**: attempt
   `account.puppet_object(session, previous)` and verify it the same way. On success, continue as
   rung 1 but log at error, because an unexpected state was repaired.
3. **The session holds no puppet and recovery also failed**: leave it OOC, log at error with the
   account, session, previous-character and target identities, and tell the player explicitly that
   they are no longer playing any character and how to return (`進入世界`). Send no snapshot,
   because there is no puppet to render — the client stays `detached`, which is the truthful state.

The failure line always reaches the player through `account.msg`, the ordinary narrative channel,
which is unaffected by presentation state. Silently swallowing any of these is forbidden by the
spec, not merely discouraged.

### D5 — Rejection vocabulary

| condition | code | message |
|---|---|---|
| `character_id` is not a member of `account.characters` | `invalid_character` | 那不是你的角色。 |
| the current puppet is in an active combat session | `in_combat` | 戰鬥中無法切換角色。 |
| `character_id` is already the current puppet | `already_current` | 你已經在這個角色上了。 |

`already_current` is a **rejection**, not a no-op success. A no-op success would tell the client a
transition is coming and leave it waiting for a `no_puppet` that never arrives; a rejection is
truthful and leaves the session untouched. (This corrects the original design's "no-op success on
self".)

Membership is checked against `account.characters` only — never a world-wide object search, never a
Builder-permission fallback like `CmdIC` has. Cross-account puppeting is unreachable through this
surface by construction, and a test asserts it for a foreign character's id.

### D6 — The action is result-only

`no_presentation: True` on both outcomes. For a success the completion snapshot would be built from
the *old* puppet and immediately superseded by the transition's own snapshot — pure waste and a
chance to publish stale state. For a rejection nothing changed, and more importantly a rejected
switch attempted while the creation overlay is open must not trigger a full snapshot that
re-renders the wizard and discards the player's unsaved form edits. This is exactly the case the
`no_presentation` flag was introduced for.

### D7 — The combat lock is the shared predicate, re-derived, never read from the panel

The adapter calls `world.rules.combat_session.is_in_active_session(actor)` directly. The roster
panel's `switch_locked` field is advisory client state; the server never trusts it. A stale click
against a panel that has not yet re-rendered is rejected with `in_combat`, which is precisely the
race the field is not allowed to decide.

A live dialogue session is deliberately **not** blocked: dialogue state is per-character persistent
state that resumes when the player switches back, unlike combat, where leaving mid-session would be
an escape hatch and would strand the session's other participants.

### D8 — Inherited per-character state is accepted explicitly, not silently

Switching runs the ordinary unpuppet/puppet hooks, which carries two consequences worth naming
rather than discovering later:

- **Party and companion bindings** (`world/rules/party.py`) are keyed to the character object, not
  the account. A companion following the character left behind stays bound to it, with no online
  owner. This is already true of Telnet `離開角色`, but this change makes switching a frequent,
  low-friction action, so the behaviour will surface far more often. Accepted as-is for this
  change: unbinding companions on switch would be a party-system decision, not a presentation one,
  and silently changing party semantics inside a WebClient action would be the wrong place for it.
  Named here so a follow-up can own it deliberately.
- **`PlayerCharacter.at_post_unpuppet`** (`typeclasses/characters.py:131-134`) unconditionally
  calls `_schedule_nomination_on_logout`, framed as "the logout epithet-nomination rest point". A
  switch now fires it too. Accepted: it is cooldown-gated (`world/rules/titles.py:800-812`) so it
  cannot runaway-spam the LLM, and a character being set down genuinely is a rest point. The
  semantic mismatch is recorded so a later change can pass a reason through the hook if the
  cadence proves wrong in play.

What *is* guaranteed not to cross the boundary is session-scoped presentation state:
`_coordinator_for`'s actor-change branch already clears `options_state`, `options_barriers`, and
`concept_proposal`, and the epoch guard already prevents any in-flight generation from publishing
into the new sequence. A regression test asserts this for the switch path.

### D9 — Payload validation

`account.character.switch` accepts exactly `{"character_id": <int>}` — a real integer, booleans
excluded (Python's `bool` is an `int` subclass, so the validator tests `type(value) is int` the way
the creation validators do), and positive. Any extra, missing, or wrongly typed field is a
malformed-payload rejection through the dispatcher's existing channel, before the adapter runs.

## Risks / Trade-offs

- **A window of one reactor turn where the old puppet is still live and the client is unlocked.** A
  player could, in principle, dispatch a second action into that window. → Mitigation: it would act
  on the old puppet, which is still the correct live puppet at that instant, and the transition's
  re-validation then runs against committed state. A client round-trip is orders of magnitude
  longer than one reactor iteration, so this is theoretical rather than practical; it is called out
  because the ordering makes it possible in principle.
- **The success result precedes the mechanical transition.** → Mitigated by D2 and D4: every
  authorization decision precedes the result, the transition re-validates and verifies, and every
  failure rung reaches the player through `account.msg`. Named in the spec so it is a contract, not
  an accident.
- **Rung 3 leaves the account OOC.** → Accepted as the least-bad terminal state, and made loud: an
  error-level log plus an explicit player message naming `進入世界`. The alternative — pretending a
  puppet exists — would produce a snapshot for a character the session is not attached to.
- **Scheduling makes the adapter clock-dependent and harder to unit test.** → Mitigation: the clock
  is a module-level injectable seam (the `world/ai/client.py` idiom); unit tests inject
  `twisted.internet.task.Clock` and advance it explicitly, so the decision and the transition are
  asserted separately and deterministically.
- **`account.characters` could contain a deleted or corrupted entry.** → The helper resolves the
  target by identity against that list at both decision and transition time and treats an
  unresolvable entry as `invalid_character`.
