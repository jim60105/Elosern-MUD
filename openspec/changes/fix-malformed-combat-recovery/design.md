## Context

`PlayerCharacter.db.active_combat` durably holds one JSON-safe `CombatSessionRecord` (dbref lists plus
fled/knockout identity, `rounds_elapsed`, optional `settled_tick`). Startup recovery iterates every
player in `restore_persisted_sessions` (`world/rules/guild_economy.py:157-169`) and delegates to
`restore_active_session` (`world/rules/combat_session.py:1250-1290`). The current recovery places the
strict parse (`read_session`, `:1260`) OUTSIDE its recovery `try` block (`:1272`), and the wrapper only
logs the propagated exception, so an unparseable payload survives every restart. `read_session`
(`:249-257`) also lets `TypeError`/`ValueError` escape from `dict(raw)`; only `CombatSessionError` is
re-raised and only `is_in_active_session` (`:350-355`) catches it. Consequences (audit finding, run-3
index 3): `is_in_active_session` reports no session, hostile `engage` (`:575`) and `combat forfeit`
(`:1238`) reject forever, and no path clears the record except an unrelated guild examination
overwriting it (`guild_exams.py:251` gate sees no session).

The recovery contract this change must preserve: well-formed records whose participant references are
invalid (missing/deleted/moved/duplicated, room missing, dead actor) settle diagnostically as defeat or
exam FAIL through `_settle_with_restore` (`combat_session.py:1190-1233`), and records already carrying a
durable `settled_tick` skip settlement and just clear leftover state (`:1263-1271`,
fix-combat-settlement-recovery D2). The outer atomic round-and-settlement transaction
(`submit_player_action`, `:892-956`) is untouched by this change.

## Goals / Non-Goals

**Goals:**
- Startup clears or quarantines unparseable `active_combat` payloads without deriving time settlement or
  participant effects from untrusted fields.
- Every raw-conversion failure normalizes to `CombatSessionError(SessionReason.MALFORMED_SESSION)`; no
  unhandled `TypeError`/`ValueError` leaks from active-session queries or commands.
- Unrelated restoration/settlement exceptions never clear or re-settle a valid session; the record stays
  intact for retry.
- Keep the invalid-participant diagnostic termination and the `settled_tick` fast path intact.

**Non-Goals:**
- No schema change or data migration (0 released users); the record shape and storage key are unchanged.
- No runtime auto-clearing: `is_in_active_session` stays a pure side-effect-free query (it is called by
  service views, creation flows, and webclient presenters); startup recovery is the only clearing point.
- No player-command surface change (no `docs/game` edits).
- Not treating the guild-examination overwrite as a recovery mechanism.

## Decisions

**D1 — Normalize raw-conversion failures inside `read_session`.** `read_session` keeps its strict
parse but catches `(TypeError, ValueError)` around `from_storage(dict(raw))`, re-raising
`CombatSessionError(MALFORMED_SESSION, ...)` chained with `from error`, while re-raising any existing
`CombatSessionError` untouched (it subclasses `ValueError`, so the handler must check it first). This
covers every raw shape failure (`dict(raw)` on a string raises `ValueError`, on an integer a
`TypeError`, unhashable-key or exotic iterable failures inside `from_storage` as well). `read_session`
is the actor-facing parse entry point for the combat facade, commands, and webclient adapters
(`web/webclient/actions/combat_actions.py` reads through it), so `is_in_active_session`, `engage`,
`forfeit`, `submit_player_action`, and the Telnet commands all inherit the normalization without code
changes. It is not the only reader of the raw attribute: the wilderness population scan
(`world/maps/wilderness_population.py:157-166`) calls `from_storage(dict(raw))` under a broad
defensive `except`, and `world/rules/status_query.py:263` fails closed with its own error type — both
already avoid leaking raw `TypeError`/`ValueError`, and startup ordering clears malformed records
(`restore_persisted_sessions` at `at_server_startstop.py:178`) before the wilderness scan
(`:179`). Alternative considered: hardening `from_storage` itself — rejected because it is also the
strict parser used by tests and content tooling, where raising the raw error type is not the contract;
normalizing at the actor-attribute boundary keeps the parser strict.

**D2 — Unparseable records are cleared, never settled.** `restore_active_session` moves parsing inside
the recovery boundary. On `CombatSessionError` from `read_session`, it logs a diagnostic and calls
`clear_session(actor, None, None)`: this sets `db.active_combat = None`, clears `ndb.action_context`,
and calls `unregister_active_battlefield(actor)` (`combat_session.py:538-561`). It deliberately does
NOT settle: `rounds_elapsed`/dbref fields of an untrusted payload must never drive a clock advance or
participant unregistration. The actor's own skip-safety registration (the only key
`evaluate_skip_safety` consults for the actor) is removed, so skips are unblocked even though no
participant-id scan is possible.

**D3 — Recovery splits invalid-references from unrelated exceptions.** After a successful parse and the
unchanged `settled_tick` fast path, `reconstruct_battlefield` is called under an `except
CombatSessionError` that performs the existing diagnostic settlement (`_settle_with_restore(actor,
record, None, "defeat"/"exam_failed")`); every later step (`_terminal_outcome`, `_settle_with_restore`,
`register_active_battlefield`) runs outside that handler, so any unrelated exception propagates to
`restore_persisted_sessions` (which logs and continues) with the durable record intact — the
attribute-restore in `_settle_with_restore` already keeps the in-process surfaces consistent for retry.
This removes the current behavior where a settlement fault on a valid session triggered a second
settlement attempt as defeat (current `:1279-1290` catches everything). Alternative considered:
settling on every exception as today — rejected because it violates the design direction to never
re-settle a valid session for an unrelated settlement exception.

**D4 — `is_in_active_session` stays pure; tests exercise both recovery entry points.** No clearing is
added to queries. Regression tests follow repo convention (`EvenniaTest` + `BattlefieldIsolation`,
direct calls) and cover both `restore_active_session` (focused) and `restore_persisted_sessions` (the
actual startup entry) with the exact payload `{"not": "a valid record"}`, asserting the record,
`action_context`, and battlefield registration are cleared, the clock does not advance, and a subsequent
`engage` against a co-located living monster succeeds.

## Risks / Trade-offs

- **Broader catch in `read_session` could mask programming errors** → only `TypeError`/`ValueError`
  are normalized (conversion-shape failures), chained with `from` for traceability; `CombatSessionError`
  re-raises untouched, and `from_storage`'s strict checks still own content validation.
- **Clear-without-participant-scan leaves residual registrations possible** → a corrupted session can
  only be cleaned by ids derived from the payload; untrusted ids must not drive cleanup. The actor's own
  registration (the only key gating the actor's skips) is cleared; any stale registrations under other
  dbrefs belong to a separate valid session's settlement or a future restart, and cannot block the actor.
- **A malformed exam-mode record can leave an orphaned ACTIVE exam** → the durable `guild_exams` list
  and the spawned temporary opponent are not addressable without trusted `exam_id`/dbref fields in the
  payload, so the malformed-clear cannot safely settle or delete them; an ACTIVE exam entry can keep
  `start_guild_exam` rejecting with `DUPLICATE_ACTIVE` until cleared by other means. Ordinary hostile
  engagement and forfeit are unblocked; this residual is documented and deliberately out of scope.
- **Exception classification change for reconstruction bugs** → non-`CombatSessionError` failures inside
  `reconstruct_battlefield` now propagate (record intact) instead of settling as defeat; this is the
  intended "never re-settle valid sessions for unrelated exceptions" behavior and no existing test
  relies on the old broad catch (all invalid-recovery paths raise `CombatSessionError`).
- **Landing context** → `fix-movement-settlement-atomicity` and `fix-npc-policy-cast-gate` are
  unrelated; `fix-dot-kill-credit` edits `submit_player_action`/`_context_for` in the same module but
  not `read_session`/`restore_active_session`. This change only edits `read_session` and
  `restore_active_session`, so it does not overlap any active sibling change.
