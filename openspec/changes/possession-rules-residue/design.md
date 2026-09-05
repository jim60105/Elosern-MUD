# Design: possession-rules-residue

## D-R1: Party owns the handback reason; possession deletes its copy

`REASON_HANDBACK_FIRST` and `HANDBACK_FIRST_MESSAGE` stay exactly where the live raise site and
every consumer already reads them: `world/rules/party.py`. From `world/rules/possession.py` we
delete the duplicate `REASON_HANDBACK_FIRST = "handback_first"` (:115) and its
`POSSESSION_REJECTION_MESSAGES` entry (:139) — nothing in the tree raises
`PossessionGateError(REASON_HANDBACK_FIRST)` (grep-verified: the constant has zero raise sites),
so the deletion removes dead state, not behavior. The party line 「請先歸位再解散同伴。」 stays
the only handback prose; the possession dict keeps its own reasons only.

Why not the reverse (possession owns it, party imports): the reason is raised *by the party
membership writer* at its own dismissal gate; a rules module should not export a reason it never
emits. The two-prose worry is moot — there is one observed line, in party, pinned by
`commands/tests/test_possess_commands.py` and `world/rules/tests/test_possession.py`.

## D-R2: The multisession guard moves into `release_on_disconnect`; the hook thins

`release_on_disconnect(account)` already enumerates `account.sessions.all()` to find possessed
puppets. The guard becomes its first step, in the rules layer: if ANY live session of the account
still puppets an object whose `db.possessed_by` is set, return without releasing (possession is
still actively driven). `typeclasses/accounts.py::at_post_disconnect` then reduces to
`super()` + the single `release_on_disconnect(self)` call — the shape the synced requirement
words. The `is_connected` pre-check that the typeclass used disappears with it: the session scan
is authoritative regardless of connection-flag timing (Evennia removes the disconnecting session
before `at_post_disconnect` fires, and the rules-layer scan no longer cares).

Concurrently we drop the dead `ObjectDB.objects.filter(db_account=account)` sweep: companion NPCs
are never `db_account`-owned, so it can only re-find characters `_account_characters` already
returned. The session scan plus `_account_characters` keeps full coverage (the possessed-NPC-on-
another-session case is exactly what the scan covers; a possession with NO live session is the
release-everything case it already handles).

The guard is count-based over *possessed* puppets only — a second session puppeting an ordinary
character must not block release of a possession nobody drives.

**Precondition (verified in Evennia 6.1):** `ServerSession.at_disconnect` unpuppets the departing
session (`account.unpuppet_object(self)`) BEFORE it calls `account.at_post_disconnect()`
(`.venv/.../evennia/server/serversession.py:155-171`) — so at hook time the disconnecting session
never still puppets anything, and the guard sees only *remaining* sessions. The existing tests
that call `at_post_disconnect`/`release_on_disconnect` while their fixture session still puppets
the NPC (`world/rules/tests/test_possession_transition.py:155-182` and `:352-369`,
`world/rules/tests/test_possession.py:338-348`) simulate an impossible state and MUST be updated
to clear the departing session's puppet (or remove the session) before the call — that is the
true disconnect shape, not a test accommodation hiding a behavior change.

## D-R3: `_transfer_puppet` retires before it grants

Reorder into THREE strict phases, not one interleaved loop: (1) collect `_acting_sessions(player)`
and refuse immediately when empty (no grant is ever attempted — strictly better than today's
grant-then-strip round trip); (2) for EVERY acting session, `send_unpuppet_transition` +
`retire_sequence` + `reset_client_sequence` — ALL sessions retire; (3) `_grant_puppet_lock` ONCE;
then the per-session access check / puppet / verify ladder exactly as today. A grant between two
sessions' retires would leave the later session with a live old epoch after the account already
holds puppet authority — an interleaved per-session retire-then-grant loop is explicitly rejected
as fixing only the first session.
All existing recovery paths (`_strip_puppet_lock` on every refused hop) stay valid: the strip is
idempotent and every post-grant hop already strips. No gate/mirror semantics change; only the
window where the grant exists with a live epoch closes.

Why fix code instead of amending the spec: the spec sentence states the invariant with a reason
("a completion for A can never publish after the swap") — it is the contract, the code drifted.

## D-R4: `_service_entry`'s paragraph becomes the docstring

Pure move in `web/webclient/presentation/affordances.py`: lift the paragraph currently stranded
after the possessed-actor guard (:468-484) to directly under `def _service_entry(...)`; the guard
stays the first *statement*. No logic, no imports, no output change.

## D-R5: Spec correction for `remote` prose ownership

`service-anchoring`'s resolver requirement claims registry-owned messages for `remote` AND
`off_anchor`. Reality (and the better design): the gate owns 「他的服務不在這裡營業。」 for
`off_anchor` only; `remote` refusals name the service ("商人不在這裡。", "公會服務人員不在這裡。")
and therefore belong to each caller's message table. The delta corrects the sentence; no code
changes for this item, and `MESSAGE_REMOTE` is deliberately NOT added (it would either go unused
or force identical prose on surfaces whose nouns differ).

## Traceability

After sync, take canonical IDs from `uv run --locked python -m tools.spec_traceability list` and
annotate the new/updated pins with `covers_requirement`: the disconnect-guard test (MODIFIED
disconnect requirement's new clause) and the retire-order test (same requirement family — the
ladder requirement is unchanged but its ordering clause newly gets a direct pin; annotate with
the ladder's existing ID).
