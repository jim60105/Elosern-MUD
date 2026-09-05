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

`retire_sequence(session)` sets `state.epoch = None` **and** `ndb.elosern_dispatch = None`, so a
subsequent `_sequence_state` call rebuilds a fresh state with `in_flight = False`.
`reset_client_sequence(session)` calls `coordinator.reset()`, producing a new epoch.
`synchronize_session(session, new_actor)` additionally retires the sequence itself, through
`_coordinator_for`'s actor-change branch.

Therefore an adapter that performs the transition inline trips all three guard clauses at once and
`_publish_completion` returns having sent nothing.

**Client reduction** (`web/static/webclient/js/elosern/protocol.js`,
`web/webclient-app/stores/elosern.js`)

- An **active** store rejects a snapshot whose epoch differs from the active one
  (`reason: "different_epoch"`). Only the `idle`, `awaiting_initial_snapshot`, and `detached`
  phases adopt a fresh epoch, and only from a full snapshot.
- `ui_protocol_error` with `code: "no_puppet"` is the sole transition into `detached`: it clears
  panels and locks mutations while retaining the active epoch so a late no-puppet rejection is
  still accepted.
- The store observes that transition and, at `stores/elosern.js`, does
  `if (prev.phase !== "detached" && rs.phase === "detached" && inFlight) { uncertain = true;
  inFlight = null; }`.

So: driving the client to `detached` is **mandatory** (an active store would otherwise discard the
new puppet's snapshot), and doing it while a request is in flight **necessarily** marks that
request uncertain. The only ordering that yields a clean switch is: result first, transition
second.

**Existing precedents relied on**

- `CmdOOC.func` is the reference sequence: `unpuppet_object` → `send_unpuppet_transition` →
  `retire_sequence` → `reset_client_sequence`.
- `_publish_completion` already supports a result-only completion via the internal
  `no_presentation` flag on a `success`/`rejected` outcome (introduced for `creation.roll_name`,
  namegen-creation-ui D10); the flag is stripped by `_normalize_result` and never reaches the wire.
- `world/ai/client.py` injects its reactor (`twisted.internet.task.Clock` in tests) rather than
  patching the module global — the project's established idiom for scheduling.

## Goals / Non-Goals

**Goals:**

- Two allowlisted account-scoped actions with exact payloads, stable codes, and Traditional
  Chinese messages, going through the existing registry/dispatcher with no new transport concept.
- A wire order that leaves the browser in a clean, certain state after a switch.
- Every authorization decision made and reported synchronously, so the result never promises
  something that has not been decided.
- Zero client-side protocol work: the browser path is the one Telnet OOC already exercises.
- No cross-account puppeting reachable through this surface, ever.

**Non-Goals:**

- No UI. The confirmation modal and the dropdown are `multichar-04`.
- No character deletion.
- No concurrent multi-window puppeting; `MULTISESSION_MODE` is untouched.
- No new Telnet command; `進入世界` already switches.
- No change to the creation wizard itself — a new shell simply falls into it.

## Decisions

### D1 — Decision synchronously, transition on the next reactor turn

Each adapter:

1. Runs every check synchronously: is the session a WebClient with a live puppet (the dispatcher
   already guarantees this), does the target resolve inside `account.characters`, is the actor in
   an active combat session, is the account below the configured capacity, is the target already
   the current puppet.
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
`server/conf/inputfuncs.py`, bypassing the dispatcher: rejected. `tests/test_webclient_frozen_contract.py`
freezes the seven envelope names and the `window.Elosern.Protocol` façade; a new envelope means a
frozen-contract amendment, a new validator, new client plumbing, and a second dispatch path with
its own duplicate/stale/busy semantics. The action registry already provides all of it.

Alternative considered — **a dispatcher post-send hook** instead of a reactor turn: rejected as
more invasive for the same ordering guarantee. It would put transition-awareness into the generic
dispatcher for the benefit of two adapters.

### D2 — What "success before the work" does and does not promise

The result reports the outcome of the **decision**, not of the mechanical transition, and this is
stated as a requirement rather than left implicit. Under Evennia's single-threaded Twisted
reactor nothing that could invalidate the decision runs between `_publish_completion` returning
and the zero-delay call firing.

The transition helper nevertheless re-validates before acting (the target is still owned, still
resolvable, and the current puppet is still not in an active combat session). If re-validation or
the puppeting itself fails, it:

- leaves the current puppet in place,
- emits an observability error event with the account, session, and target identity,
- delivers a Traditional Chinese failure line to the player through `account.msg` (the ordinary
  narrative channel, which is unaffected by presentation state), and
- pushes a fresh snapshot so the client is never stranded on a retired epoch.

This is the honest handling: the player learns the switch did not happen, through a channel that
cannot itself be broken by the failed transition.

### D3 — Both actions are result-only

`no_presentation: True` on both outcomes. For a success the completion snapshot would be built
from the *old* puppet and immediately superseded by the transition's own snapshot — pure waste
and a chance to publish stale state. For a rejection nothing changed, and more importantly a
rejected switch attempted while the creation overlay is open must not trigger a full snapshot that
re-renders the wizard and discards the player's unsaved form edits. This is exactly the case the
`no_presentation` flag was introduced for.

### D4 — `account.character.create` composes the existing pieces and adds nothing

Order inside the scheduled transition:

1. `account.unpuppet_object(session)`, `send_unpuppet_transition(session)`,
   `retire_sequence(session)`, `reset_client_sequence(session)` — the `CmdOOC` sequence verbatim.
2. `account.create_character()` with no `key` override, so Evennia's default applies; the project
   `at_post_create_character` hook sets `creation_pending = True`.
   `create_character` performs its own slot check and returns `(None, [error])` rather than
   raising, which is the re-validation of D2's capacity check.
3. `account.puppet_object(session, shell)` and `account.db._last_puppet = shell`.
4. `synchronize_session(session, shell)`.

The snapshot's mode resolves to `creation` through the unchanged
`PresentationCoordinator.mode_for` (`creation_pending` → `creation`), so `CreationOverlay` mounts
with no client change. The reusable creation start presentation is delivered as narrative text for
parity with a first character; `WORLD_INTRODUCTION` is not, and after `multichar-01` it *cannot*
be — it is bound to the login hook, which a mid-session puppet change does not run.

The new shell's key is Evennia's default (the account name) until the wizard's activation renames
it. `multichar-02`'s roster reports that truthfully with a pending marker; nothing here invents a
name.

### D5 — `account.character.switch` rejection vocabulary

| condition | code | message |
|---|---|---|
| `character_id` is not a member of `account.characters` | `invalid_character` | 那不是你的角色。 |
| the current puppet is in an active combat session | `in_combat` | 戰鬥中無法切換角色。 |
| `character_id` is already the current puppet | `already_current` | 你已經在這個角色上了。 |

`already_current` is a **rejection**, not a no-op success. A no-op success would tell the client a
transition is coming and leave it waiting for a `no_puppet` that never arrives; a rejection is
truthful and leaves the session untouched. (This corrects the original design's "no-op success on
self".)

Membership is checked against `account.characters` only — never a world-wide object search, never
a Builder-permission fallback like `CmdIC` has. Cross-account puppeting is unreachable through
this surface by construction, and a test asserts it for a foreign character's id.

`account.character.create` rejects with `character_slots_full` / 角色數量已達上限。 when the
account is at capacity, and with `in_combat` under the same combat predicate — creating a
character leaves the current one, so the combat lock applies identically.

### D6 — The combat lock is the shared predicate, re-derived, never read from the panel

Both adapters call `world.rules.combat_session.is_in_active_session(actor)` directly. The roster
panel's `switch_locked` field is advisory client state; the server never trusts it. A stale click
against a panel that has not yet re-rendered is rejected with `in_combat`, which is precisely the
race the field is not allowed to decide.

A live dialogue session is deliberately **not** blocked: dialogue state is per-character persistent
state that resumes when the player switches back, unlike combat, where leaving mid-session would
be an escape hatch and would strand the session's other participants.

### D7 — Payload validation

`account.character.switch` accepts exactly `{"character_id": <int>}` — a real integer, booleans
excluded (Python's `bool` is an `int` subclass, so the validator tests `type(value) is int` the way
the creation validators do), and positive. `account.character.create` accepts exactly `{}`. Any
extra, missing, or wrongly typed field is a malformed-payload rejection through the dispatcher's
existing channel, before the adapter runs.

## Risks / Trade-offs

- **A window of one reactor turn where the old puppet is still live and the client is unlocked.**
  A player could, in principle, dispatch a second action into that window. → Mitigation: it would
  act on the old puppet, which is still the correct live puppet at that instant, and the
  transition's re-validation then runs against committed state. A client round-trip is orders of
  magnitude longer than one reactor iteration, so this is theoretical rather than practical; it is
  called out because the ordering makes it possible in principle.
- **The success result precedes the mechanical transition.** → Mitigated by D2: every
  authorization decision precedes the result, the transition re-validates, and a failure reaches
  the player through `account.msg` plus a fresh snapshot. Named in the spec so it is a contract,
  not an accident.
- **Scheduling makes the adapters clock-dependent and harder to unit test.** → Mitigation: the
  clock is a module-level injectable seam (the `world/ai/client.py` idiom); unit tests inject
  `twisted.internet.task.Clock` and advance it explicitly, so the decision and the transition are
  asserted separately and deterministically.
- **Switching away from a character with a pending art job, an open dialogue, or a scheduled
  action-options generation.** → The existing `_coordinator_for` actor-change branch already
  clears `options_state`, `options_barriers`, and `concept_proposal`, and the epoch guard already
  prevents any in-flight generation from publishing into the new sequence. Nothing new is needed;
  a regression test asserts it for the switch path.
- **`account.characters` could contain a deleted or corrupted entry.** → The transition helper
  resolves the target by identity against that list at both decision and transition time and
  treats an unresolvable entry as `invalid_character`.
