## Context

`server.option_proposal_service` owns the asynchronous action-options cache, pending work, and
per-session display state. The v5 `context_actions` presenter correctly consumes an immutable
snapshot, but it currently trusts any ready snapshot without proving that the actor is still in
the fingerprinted situation. The trigger hooks cover exit traversal, dialogue completion, and
`ui_sync`, leaving combat termination and direct `move_to()` relocation without a fresh
generation. The service also assumes one pending generation per fingerprint, which permits a
different window's completion to repopulate a cache after one window dismissed it.

The fix must preserve the architectural boundary. `world.ai` continues to emit proposals only;
the new derivation and lifecycle observations are read-only presentation work, while the existing
deterministic movement and combat code remains the sole writer of canonical game state. All
options state stays process-local or on `session.ndb`.

## Goals / Non-Goals

**Goals:**

- Prevent a ready, generating, or degraded state from rendering after its fingerprint became stale.
- Schedule a replacement generation after every committed player relocation and after a combat
  action that returns the actor to exploration.
- Preserve another window's in-flight delivery while guaranteeing that a dismissing window does
  not replay its pre-dismiss generation.
- Keep one canonical node encoder and one narrative stream-end append owner.
- Remove retired pending entries immediately without allowing old Deferred cleanup to remove newer
  work.

**Non-Goals:**

- Persisting proposals, dismissals, cache generations, or pending work across a server restart.
- Changing the v5 OOB envelope, card schema, LLM prompt, validation ladder, or deterministic
  fallback vocabulary.
- Adding a new player command, a new LLM call for ordinary cache replay, or a background clock
  trigger.
- Retrofitting a generic observer into unrelated non-player entity relocation paths.

## Decisions

### Shared situation derivation is the freshness authority

Extract the read-only exploration situation derivation from `option_proposal_service` into
`web.webclient.presentation.fingerprints`. It returns the current fingerprint and the deterministic
data the trigger service already needs, using the existing canonical eligibility and public-state
digests. This module MUST NOT import `server.option_proposal_service` or `world.ai`; the server
service consumes it through a function-local import, while `build_presentation_context()` consumes
only its fingerprint and records it on immutable presentation context.

The exploration suggestions presenter compares every non-`unavailable` snapshot fingerprint to
the context fingerprint. A missing or mismatched derivation emits exact `{"status":
"unavailable"}` and logs a bounded diagnostic. It never displays cached cards merely because the
snapshot shape remains valid.

Computing a separate fingerprint inside the presenter was rejected because it could drift from
the trigger service. Treating old cards as valid until the next explicit trigger was rejected
because it contradicts the vocabulary-lock freshness claim after combat and direct relocation.

### Location and terminal-combat lifecycle events schedule after canonical settlement

Move the action-options location observer from the Exit-only helper to the player typeclass's
post-move lifecycle. It remains player/account gated and registers a `transaction.on_commit`
callback, so an aborted movement publishes nothing. Normal exit traversal and direct
`move_to()` relocation therefore share one observer; rollback compensations with `move_hooks=False`
remain silent. Existing exit-specific scheduling is removed to avoid duplicate callbacks.

The dispatcher adds a terminal-combat scheduling gate after it has published the action completion
update and action result. It is limited to successful combat actions and verifies that the actor is
back in exploration before calling the trigger service with `watchers_for(actor)`, rather than the
dispatcher-held session alone. This preserves the initiating session's output/result ordering and
refreshes every live window for the actor only after combat has settled.

Scheduling from the combat rules package was rejected because the service is presentation
orchestration and the rules package must not own session transport behavior. Scheduling before a
movement or combat transaction commits was rejected because it can name a situation that never
became canonical.

### Dismissal uses per-session generation barriers and a bounded pending chain

Each fingerprint carries a monotonically increasing ephemeral generation number. Cache entries and
pending generations are tagged with that number. A dismiss records, in a separate bounded
`session.ndb` barrier store keyed by fingerprint, the minimum generation number that may
subsequently be displayed. This store is capped at the option-cache capacity, clears on puppet
change and unpuppet, and removes an entry after eligible delivery or its bounded eviction. It never
extends the exact `options_state` shape. The marker is cleared only after that session receives an
outcome from a generation at or above the barrier.

Each fingerprint's chain is the explicit owner of one joinable active generation and at most one
successor. When a different session still owns an older in-flight generation, the dismissing
session's next trigger is queued on that successor rather than joining or replaying the old
generation. The old generation continues to deliver only to its remaining subscribers. If its last
subscriber subsequently dismisses, it is removed at once from the joinable pending registry but
its identity-bearing Deferred completion remains detached under the chain solely to start the
still-current successor. When that Deferred settles, the continuation verifies the chain and
successor identities, starts the successor exactly once with a fresh situation derivation, and
then discards the detached predecessor reference. The chain allows one active and one successor
generation per fingerprint. Repeated triggers coalesce into the same applicable generation instead
of producing unbounded parallel LLM calls.

Older completions may deliver to their own valid subscribers, but version checks prevent them from
overwriting a newer cache entry. A retired generation is removed from the joinable pending registry
immediately by identity. Its eventual Deferred cleanup and detached handoff remain
identity-guarded, so they cannot remove or start an obsolete replacement generation.

Globally cancelling a shared generation on one-window dismissal was rejected because it violates
the existing second-window isolation contract. Letting the dismissing session reuse a later
repopulation of the old cache was rejected because it defeats the explicit dismissal intent.

### Destination IDs and stream-end movement have single owners

`affordances._move_entries()` calls `node_id_for_location(destination)` for every destination and
the private duplicate destination encoder is removed. The existing current-node adapter comparison
continues to call that same function.

`StreamEndBlock.appendNode()` already inserts new narrative nodes before the mounted block and is
therefore the only relocation mechanism required during normal appends. Remove the unused
`moveChoicePointToEnd` facade method and its choice-point readiness requirement. Attachment,
replacement, and removal stay on the facade; no module gains direct narrative-container access.

Calling the unused move method after every append was rejected because it is always a no-op under
the existing `insertBefore` ownership and would obscure the single scroll/unread decision.

## Risks / Trade-offs

- [Freshness derivation cannot read a valid situation] → The presenter fails closed to
  `unavailable`; the next lifecycle trigger or `ui_sync` attempts recovery without mutating state.
- [A dismissal overlaps a long-running transport] → A chain-owned detached predecessor hands off
  to one current successor after identity checks, avoiding duplicate calls and stranded successor
  subscribers; the dismissing window never receives the old result.
- [A player moves repeatedly while a successor is queued] → Tokens and fingerprint checks mute
  obsolete delivery. The later committed location trigger derives the next applicable situation.
- [Player typeclass post-move runs during initialization] → The existing account and exploration
  gates reduce this to a logged no-op; tests cover initial placement and rollback paths.
- [A session barrier outlives its puppet] → Puppet-change and unpuppet reset paths clear the
  bounded `session.ndb` barrier store; disconnect releases the session-local state.
- [Removing the facade method misses an external caller] → Repository-wide JavaScript contract
  tests and a source search verify that narrative append paths already own relocation.

## Migration Plan

This is an in-memory-only change. Deploying a new worker starts with empty caches, pending chains,
and session `ndb` markers. No database migration or compatibility path is required. Rollback is a
code rollback followed by a worker restart, which discards the same ephemeral state.

## Open Questions

None.
