## Purpose

This capability covers the action-options trigger service, the write side of the
`context_actions` suggestions panel: situation fingerprinting, the
one-LLM-call-per-cache-residency contract with replay and pending semantics,
session-scoped presentation state, token/epoch-guarded delivery, per-session
eviction, the transport-failure-only negative memo, the watcher registry for the
room-entry hook, and fire-and-forget scheduling. The read side of the panel is
pinned by the `webclient-context-actions-suggestions` capability. This spec was
added by the `action-options-trigger-service` change.

## Requirements

### Requirement: Fingerprint identifies the situation, not the moment

The service SHALL derive one fingerprint per situation as
`sha256(room_key | sorted NPC identities | sorted monster identities | eligible_affordance_digest
| public_state_digest)`, computed through a single shared canonical-JSON serialization (keys
sorted, deterministic type coercion) that the schema ladder's stage-9 comparison and the test
fixtures also use. The eligibility digest SHALL cover the canonical eligible-affordance list as
`action_id + params` pairs with labels excluded, so any change in what is executable —
schedule-gate flips, locked exits, monster death, vanishing objects — SHALL produce a new
fingerprint. The public-state digest SHALL cover only state the player already sees: the
displayed objective identity — the sorted `(quest_id, stage_index, objective_summary)` tuples of
the active objectives the quest view renders, via a single read-only helper — and public
relationship tier labels. Hidden stages, internal counters, thresholds, raw affinity numbers,
narrative tail, look commands, and time of day SHALL NOT enter either digest.

#### Scenario: Identical situations replay on the same fingerprint
- **WHEN** the same room, people, eligibility, and public state are fingerprinted twice
- **THEN** both calls produce the same fingerprint and the second trigger replays instead of
  generating

#### Scenario: A schedule gate flip invalidates the fingerprint
- **WHEN** an NPC's schedule gate changes whether a talk affordance is eligible
- **THEN** the eligibility digest — and therefore the fingerprint — changes, so a cached
  proposal can never name an action that stopped being current

#### Scenario: Hidden progress never churns the fingerprint
- **WHEN** partial progress toward the current objective or an affinity increase within one
  tier occurs
- **THEN** the public-state digest (and fingerprint) is unchanged because hidden counters,
  stage progress, and numeric affinity are excluded

#### Scenario: Multiple active objectives hash deterministically
- **WHEN** two active objectives are present in different orders across two evaluations
- **THEN** the sorted identity tuples produce the same public-state digest in both evaluations

### Requirement: One LLM call per cache residency with replay and pending semantics

For each fingerprint the service SHALL call `generate_action_options` at most once per
**cache residency** — the period from a fingerprint entering the cache (or pending) until its
cache entry is evicted by LRU pressure or by `evict()`; an evicted or dismissed fingerprint SHALL
regenerate on its next trigger. Within a residency: a cached fingerprint SHALL re-publish the
cached `OptionSet` without touching the LLM; a pending fingerprint SHALL attach the triggering
session as a subscriber to the in-flight generation instead of starting a second call; an
uncached, unpending fingerprint SHALL register one pending entry and start exactly one
generation. A trigger whose session already displays the current fingerprint with status `ready`
SHALL re-publish the session's `displayed` set (even when the global cache entry is already
gone) and SHALL NOT schedule; at status `degraded` it SHALL re-derive `default_cards()` freshly
and publish that as a status refresh. Each subscriber entry SHALL carry the session, its current
generation token, and the coordinator epoch captured at trigger time; delivery SHALL be guarded
by both.

#### Scenario: Three triggers, one LLM call
- **WHEN** three sessions (or three consecutive triggers) visit the same uncached fingerprint
- **THEN** exactly one `generate_action_options` call occurs and every subscriber receives the
  result

#### Scenario: A pending trigger attaches a subscriber mid-flight
- **WHEN** a second trigger arrives while the first generation for the fingerprint is still in
  flight
- **THEN** no second transport call starts and both subscribers receive the eventual result,
  each guarded by its own token and epoch

#### Scenario: Fire-and-forget call with an existing ready display
- **WHEN** a trigger fires for a situation whose fingerprint matches the session's displayed
  state at `ready` and the global cache entry has since been evicted
- **THEN** the session's `displayed` set is re-published and no generation, pending entry, or
  transport work occurs

#### Scenario: An evicted fingerprint regenerates
- **WHEN** the fingerprint's cache entry was evicted by LRU pressure or user dismissal and a
  trigger arrives
- **THEN** exactly one new generation starts for that fingerprint (the one-call contract does
  not survive eviction or dismissal)

### Requirement: Session-scoped options presentation state survives async completion and puppet change

The service SHALL own a transport-scoped `options_state` on `session.ndb` with exactly
`{owner_actor_id, fingerprint, status, generation_token, displayed}` where `status` is one of
`generating|ready|degraded|unavailable`, `generation_token` is monotonic per session, and
`owner_actor_id` is the puppet the state belongs to. A puppet change SHALL clear the state (next
to the existing coordinator reset / sequence retirement), and a snapshot whose `owner_actor_id`
differs from the rendering puppet SHALL be treated as absent. Every `context_actions` render
SHALL assemble its `suggestions` section from an immutable `OptionsSnapshot` carried on
`PresentationContext.options_state`; the snapshot SHALL be built by the single shared
presentation-context factory that the ingress, every dispatcher publication path, and the
service's own push all use (a `None` default SHALL keep existing presenters and tests
unchanged), and presenters SHALL never receive or read the raw session. A `generating` state
SHALL be published only to sessions whose previous status was not `generating`.

#### Scenario: An async ready result survives the next snapshot
- **WHEN** a completion lands after a full-snapshot render began for the same situation
- **THEN** the snapshot's `suggestions` and the pushed update both read the same
  `options_state`, and the `ready` cards are not clobbered

#### Scenario: A repuppeted session never shows the previous character's options
- **WHEN** the session's puppet changes from character A to character B and a full snapshot
  renders
- **THEN** the A-owned options state is cleared and the B snapshot carries no A fingerprint,
  cards, or degraded state

#### Scenario: A generating-to-generating transition publishes nothing
- **WHEN** a new trigger takes over a session that is already `generating`
- **THEN** no generating line is published for that transition, and only the eventual replacement
  is delivered

### Requirement: Delivery is guarded by token and epoch, and retired generations write nothing

A generation completion SHALL deliver to each subscriber entry only when the subscriber's
generation token is still the session's current token AND the session's live coordinator epoch
still equals the captured epoch; a completion with stale token or epoch SHALL publish nothing to
that subscriber. A **retired generation** (its last subscriber was removed by `evict()`) SHALL
write no cache entry, no memo, and no session state, even though its network request may still
be completing in the background. The push SHALL go through `publish_panel_update(session, actor,
panels, *, context, expected_epoch)`: on epoch mismatch the helper SHALL silently send nothing,
otherwise SHALL produce the exact `ui_update` envelope (same revision discipline and message
naming as the dispatcher). A successful generation SHALL update `displayed` and publish
`ready`; a degraded outcome SHALL publish `degraded` freshly derived from `default_cards()`; a
transport failure SHALL additionally record a negative memo.

#### Scenario: A retired transport receives nothing
- **WHEN** a completion resolves for a subscriber whose transport was replaced or whose puppet
  changed (epoch mismatch)
- **THEN** the push is a silent no-op and the replacement sequence never receives the stale
  result

#### Scenario: A last-subscriber dismiss retires the generation
- **WHEN** the only subscriber of an in-flight generation dismisses and the generation then
  completes successfully
- **THEN** the completion writes no cache entry and no memo for that fingerprint, and the next
  trigger for the situation starts a fresh generation even though the old request finished
  later

#### Scenario: A stale token mutes only its own subscriber
- **WHEN** a session dismissed (or re-triggered) while its generation was in flight
- **THEN** that session's subscriber entry is dropped from the delivery and all other
  subscribers still receive their guarded publish

### Requirement: Eviction is per-session and clears the displayed situation

`evict(session, actor)` SHALL read the session's displayed fingerprint (the situation the player
is dismissing, even if they moved away), remove that fingerprint's cache entry and negative memo
from the global stores, remove that session from that fingerprint's pending subscribers
(retiring the generation when it was the last subscriber), increment the session's generation
token, and set its `options_state` to `{owner_actor_id, fingerprint: None, status: unavailable,
token+1}`. `evict` SHALL return whether the eviction succeeded (a boolean) and SHALL NOT raise; a
failed eviction SHALL leave the session's state unchanged, so the dismiss adapter rejects instead
of reporting success. Eviction SHALL NOT send a presentation update itself (state-only contract,
dismiss-options-action D1): the dismissal's single `ui_update` with
`suggestions.status="unavailable"` is published by the dispatcher completion path after the
`options.dismiss` adapter declares `context_actions` affected. Eviction SHALL leave
every other session's subscriber entries, tokens, states, and future publications intact; a
later trigger for the same situation SHALL regenerate.

#### Scenario: Dismiss leaves a second window untouched
- **WHEN** one of two sessions on the same puppet dismisses while a generation is in flight
- **THEN** the dismissing session's completion becomes inert, the other session's subscriber
  entry, token, state, and eventual publication are unaffected, and a later trigger regenerates
  the situation

#### Scenario: The cache and memo for the dismissed situation are gone
- **WHEN** the dismissed fingerprint is triggered again after the dismiss
- **THEN** the cached set and any negative memo for that fingerprint are absent, so a fresh
  generation starts

### Requirement: The negative memo applies to transport failures only

A transport failure SHALL memoize the fingerprint for `NEGATIVE_MEMO_TTL` (30 s); a trigger
within the TTL SHALL resolve to `degraded` immediately without transport work; after the TTL a
trigger SHALL attempt once more. A degraded outcome that is not a transport failure — validation
exhaustion, prompt unavailability, a disabled profile, or a response that
failed the guardrail's declared output schema (the client succeeded, so the
failure is never observed at the client boundary) — SHALL NOT be memoized.
The discrimination is positional, not by failure kind: a client that itself
raises `LLMTransportError` (even one carrying the reason `"malformed"`) IS
the memoized class, because it was observed at the client boundary, while
the guardrail's own `LLMTransportError` raised after a successful client
round-trip is not. The service
SHALL distinguish the two through the controlled-failure fallback: it calls the layer through a
thin client wrapper that observes `LLMTransportError` (raised or errbacked) on the injected
client, and a degraded outcome with an observed transport failure is the memoized class while
every other degrade is not (the disabled profile resolves before any client call, so it is
never observable through the wrapper); a successful generation SHALL NOT be memoized
negatively. A later change MAY replace the observation with the layer's typed outcome without
changing the memo semantics.

#### Scenario: A dead endpoint is not hammered within the TTL
- **WHEN** a transport failure memoizes a fingerprint and another trigger fires within 30 s
- **THEN** the second trigger resolves to `degraded` immediately and the client is never called
  again within the TTL

#### Scenario: Ordinary degrade is never memoized
- **WHEN** the layer degrades because of validation exhaustion or a disabled profile
- **THEN** no memo is recorded and the next trigger attempts the generation again

#### Scenario: The memo expires and a fresh attempt happens
- **WHEN** a trigger fires after the memo TTL elapsed
- **THEN** exactly one new generation attempt starts for that fingerprint

### Requirement: Watcher registry resolves live sessions for the room-entry hook

`watchers_for(actor)` in `web/webclient/presentation/watchers.py` SHALL return the live
webclient sessions watching the given puppet, each with its **current** coordinator epoch read
at query time. The registry SHALL be a per-actor map keyed by session identity: registration is
idempotent per session (repeated `ui_sync` and command settlements update the entry, never
append), entries SHALL be pruned when their sessions are no longer connected or no longer puppet
the recorded actor, and stale entries SHALL be harmless because the epoch guard drops their
pushes.

#### Scenario: A puppeted window registers and resolves
- **WHEN** a webclient session with a puppet synchronizes, then synchronizes again, and the
  room-entry hook asks for watchers of that puppet
- **THEN** the session appears exactly once (with its current coordinator epoch), and sessions
  without a puppet or of non-webclient transports are never registered

#### Scenario: Disconnected sessions are pruned at the next registration
- **WHEN** a session disconnects and any later registration occurs
- **THEN** the disconnected session no longer appears in `watchers_for` results

### Requirement: Scheduling never raises and never blocks

`schedule_action_options(actor, *, watchers, client=None) -> defer.Deferred | None` SHALL be
fire-and-forget: fingerprint derivation, context assembly, client construction, and Deferred
acquisition SHALL be wrapped so any synchronous failure (vanished room, malformed context, any
exception) logs a bounded diagnostic and resolves to nothing; the call SHALL NOT raise into its
caller's critical section. `client=None` SHALL build the `action_options` profile client, or the
non-`None` offline stub when the profile is disabled (whose `get_response` SHALL fail loudly if
ever invoked). A successfully scheduled generation's failure path SHALL log and resolve to
nothing. The service SHALL be the single production caller of `generate_action_options`, SHALL
import no state writer, and SHALL write only ephemeral cache/presentation state — it SHALL never
mutate canonical game state.

#### Scenario: A vanished room makes the trigger a logged no-op
- **WHEN** the actor's location cannot be resolved at trigger time
- **THEN** the call returns `None`, logs a bounded diagnostic, and the caller's command path
  continues unaffected

#### Scenario: A disabled profile never touches transport
- **WHEN** the `action_options` profile is disabled
- **THEN** scheduling resolves every trigger to `degraded`, the offline stub's `get_response` is
  never invoked, no memo is recorded, and no connection is opened

### Requirement: Current situation freshness gates session-backed suggestions

The action-options service SHALL expose one shared, read-only exploration situation derivation
that produces the same fingerprint and deterministic input data for scheduling and presentation.
The presentation-context factory SHALL carry the current derived fingerprint, or `None` when no
exploration situation can be derived. Before rendering any session snapshot with status
`generating`, `ready`, or `degraded`, the `context_actions` suggestions presenter SHALL require
its snapshot fingerprint to equal the context fingerprint; a missing or mismatched fingerprint
SHALL emit exact `{"status": "unavailable"}` with a bounded diagnostic and SHALL emit none of the
old cards. This gate SHALL be read-only and SHALL not schedule, evict, or mutate canonical state.

#### Scenario: Combat terminal state cannot revive pre-combat cards
- **WHEN** a ready session state produced before combat remains on the session after the terminal
  combat action returns the actor to exploration with a different eligible-affordance digest
- **THEN** the first exploration snapshot emits `suggestions.status = "unavailable"` until a fresh
  generation replaces the stale session state, and no pre-combat card reaches the wire

#### Scenario: Direct relocation suppresses an old in-flight state
- **WHEN** an actor is relocated with `move_to()` while a prior room's options state is generating
  or ready
- **THEN** presentation compares the snapshot fingerprint with the new location's derived
  fingerprint and renders unavailable rather than the prior room's generating line or cards

### Requirement: All committed player relocations and terminal combat returns trigger options

Every committed relocation of an account-owned `PlayerCharacter`, including Exit traversal and a
direct `move_to()` call with movement hooks enabled, SHALL register one fire-and-forget
action-options scheduling callback through `transaction.on_commit`. The observer SHALL not run for
NPC movement, rollback compensation with hooks disabled, or a failed transaction. A successful
combat action that has returned its actor to exploration SHALL schedule action options only after
the dispatcher has published its completion update and action result, using every current live
watcher returned by `watchers_for(actor)`. These lifecycle triggers SHALL use the existing
watcher, token, epoch, and no-raise scheduling contract.

#### Scenario: Direct teleport schedules fresh options
- **WHEN** a puppeted player is moved directly from one exploration room to another through
  `move_to()` and the relocation transaction commits
- **THEN** watchers of that player receive the normal generating or replay path for the destination
  situation, and no exit-specific hook is required

#### Scenario: Terminal combat schedules after the result
- **WHEN** a successful `combat.cast`, `combat.flee`, or `combat.forfeit` action ends the active
  combat session
- **THEN** the dispatcher sends its terminal completion presentation and action result first, then
  schedules the exploration options trigger for every live watcher of the actor, whose later
  update carries the fresh destination situation only

### Requirement: Dismissal prevents replay from a concurrent older generation

The service SHALL tag each cache entry and pending generation for a fingerprint with a monotonic
ephemeral generation number. `evict(session, actor)` SHALL record a per-session,
per-fingerprint minimum displayable generation number in a separate bounded `session.ndb` barrier
store, in addition to its existing state/token eviction. The barrier store SHALL retain no more
than the option-cache capacity, SHALL clear on puppet change and unpuppet, and SHALL never alter
the exact `options_state` shape. A later trigger for that session SHALL not replay a cache entry or
join a pending generation whose number is older than the recorded minimum. Each fingerprint SHALL
own a chain with one joinable active generation and at most one successor. If another session
still subscribes to an older active generation, the service SHALL retain its delivery and queue the
dismissed session on the successor. If that active generation later loses its final subscriber, it
SHALL leave the joinable registry immediately while an identity-guarded detached completion owned
by the chain starts the still-current successor exactly once when the old Deferred settles. The
successor SHALL derive fresh context after that settlement. Older completions SHALL never overwrite
a newer cache entry, and a barrier SHALL clear only when its session receives an outcome from an
eligible generation.

#### Scenario: One window dismisses while another window remains pending
- **WHEN** sessions A and B share an in-flight generation, A dismisses, and B remains subscribed
- **THEN** B receives the old generation normally, A receives none of it, and A's next trigger
  receives a successor generation rather than a replay of the old generation's cache entry

#### Scenario: A later cache replay is fresh for the dismissing session
- **WHEN** the successor generation for a dismissed fingerprint completes successfully
- **THEN** its cache entry has a generation number meeting the session's barrier, the barrier is
  cleared on delivery, and later triggers for that session may replay that successor entry

#### Scenario: A detached predecessor hands off exactly once
- **WHEN** A dismisses and queues a successor behind an active generation, B then dismisses as the
  active generation's final subscriber, and the detached active Deferred completes
- **THEN** the old generation is absent from the joinable registry, its completion starts the
  current successor exactly once through chain identity checks, and A receives only that successor
  outcome

#### Scenario: A second dismissal bars the queued successor
- **WHEN** a session already queued on a successor dismisses again — raising its barrier above the
  successor's generation — and then triggers
- **THEN** the session never joins the pre-dismiss successor, settles degraded in place with the
  barrier standing, and a later trigger starts fresh work above the barrier

#### Scenario: A successor that cannot name the old situation settles without clearing the barrier
- **WHEN** the actor moved on or the situation vanished before the queued successor started
- **THEN** the successor settles its queued watchers degraded with no memo and without clearing
  their dismissal barriers for the old fingerprint, and the chain drops the successor

### Requirement: Retired pending generations are removed by identity immediately

When `evict()` removes the final subscriber from a pending generation, the service SHALL mark that
generation retired and remove that exact generation from the joinable pending registry immediately.
When a current successor waits behind it, the fingerprint chain alone MAY retain an
identity-bearing detached completion reference solely for successor handoff; that reference SHALL
not be discoverable or joinable by scheduling. The eventual completion and Deferred cleanup SHALL
remain identity-guarded: it SHALL write no cache, memo, or session state, and SHALL not remove a
newer active or successor generation registered for the same fingerprint.

#### Scenario: A retired completion cannot remove replacement work
- **WHEN** the last subscriber dismisses generation N, a later trigger starts generation N+1 for
  the same fingerprint, and generation N then completes
- **THEN** generation N's completion produces no cache or delivery and generation N+1 remains in
  the pending registry until it settles
