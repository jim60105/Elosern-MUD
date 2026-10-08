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
fixtures also use.

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

#### Scenario: Eligibility digest coverage
- **WHEN** the eligibility digest is computed
- **THEN** it SHALL cover the canonical eligible-affordance list as `action_id + params` pairs
  with labels excluded, so any change in what is executable — schedule-gate flips, locked
  exits, monster death, vanishing objects — SHALL produce a new fingerprint

#### Scenario: Public-state digest coverage
- **WHEN** the public-state digest is computed
- **THEN** it SHALL cover only state the player already sees: the displayed objective
  identity — the sorted `(quest_id, stage_index, objective_summary)` tuples of the active
  objectives the quest view renders, via a single read-only helper — and public relationship
  tier labels

#### Scenario: Hidden and incidental state is excluded
- **WHEN** either digest is computed
- **THEN** hidden stages, internal counters, thresholds, raw affinity numbers, narrative tail,
  look commands, and time of day SHALL NOT enter either digest

### Requirement: One LLM call per cache residency with replay and pending semantics

For each fingerprint the service SHALL call `generate_action_options` at most once per
**cache residency**: within a residency a cached fingerprint SHALL re-publish the cached
`OptionSet` without touching the LLM, a pending fingerprint SHALL attach the triggering
session as a subscriber to the in-flight generation instead of starting a second call, and an
uncached, unpending fingerprint SHALL register one pending entry and start exactly one
generation.

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

#### Scenario: Cache residency boundary
- **WHEN** a cache residency is measured
- **THEN** it spans from a fingerprint entering the cache (or pending) until its cache entry is
  evicted by LRU pressure or by `evict()`, and an evicted or dismissed fingerprint SHALL
  regenerate on its next trigger

#### Scenario: Ready display short-circuits the trigger
- **WHEN** a trigger's session already displays the current fingerprint with status `ready`
- **THEN** the service SHALL re-publish the session's `displayed` set (even when the global
  cache entry is already gone) and SHALL NOT schedule

#### Scenario: Degraded display refreshes with fresh defaults
- **WHEN** a trigger's session displays the current fingerprint at status `degraded`
- **THEN** the service SHALL re-derive `default_cards()` freshly and publish that as a status
  refresh

#### Scenario: Subscriber entries carry delivery guards
- **WHEN** a subscriber attaches to a generation
- **THEN** its entry carries the session, its current generation token, and the coordinator
  epoch captured at trigger time, and delivery SHALL be guarded by both

### Requirement: Session-scoped options presentation state survives async completion and puppet change

The service SHALL own a transport-scoped `options_state` on `session.ndb` with exactly
`{owner_actor_id, fingerprint, status, generation_token, displayed}` where `status` is one of
`generating|ready|degraded|unavailable`, `generation_token` is monotonic per session, and
`owner_actor_id` is the puppet the state belongs to.

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

#### Scenario: Puppet change clears the state
- **WHEN** the session's puppet changes
- **THEN** the state is cleared (next to the existing coordinator reset / sequence retirement),
  and a snapshot whose `owner_actor_id` differs from the rendering puppet SHALL be treated as
  absent

#### Scenario: Renders read the immutable snapshot
- **WHEN** a `context_actions` render assembles its `suggestions` section
- **THEN** it uses an immutable `OptionsSnapshot` carried on
  `PresentationContext.options_state`; the snapshot SHALL be built by the single shared
  presentation-context factory that the ingress, every dispatcher publication path, and the
  service's own push all use (a `None` default SHALL keep existing presenters and tests
  unchanged), and presenters SHALL never receive or read the raw session

#### Scenario: Generating is published only on transition
- **WHEN** a `generating` state is about to be published
- **THEN** it SHALL go only to sessions whose previous status was not `generating`

### Requirement: Delivery is guarded by token and epoch, and retired generations write nothing

A generation completion SHALL deliver to each subscriber entry only when the subscriber's
generation token is still the session's current token AND the session's live coordinator epoch
still equals the captured epoch; a completion with stale token or epoch SHALL publish nothing to
that subscriber. A **retired generation** (its last subscriber was removed by `evict()`) SHALL
write no cache entry, no memo, and no session state, even though its network request may still
be completing.

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

#### Scenario: Retirement is unaffected by an in-flight request
- **WHEN** a generation is retired while its network request may still be completing in the
  background
- **THEN** it still SHALL write no cache entry, no memo, and no session state

#### Scenario: Pushes go through the shared panel-update helper
- **WHEN** a guarded delivery pushes
- **THEN** it goes through `publish_panel_update(session, actor, panels, *, context,
  expected_epoch)`: on epoch mismatch the helper SHALL silently send nothing, otherwise SHALL
  produce the exact `ui_update` envelope (same revision discipline and message naming as the
  dispatcher)

#### Scenario: Outcomes map to published statuses
- **WHEN** a generation completes
- **THEN** a successful generation SHALL update `displayed` and publish `ready`; a degraded
  outcome SHALL publish `degraded` freshly derived from `default_cards()`; and a transport
  failure SHALL additionally record a negative memo

### Requirement: Eviction is per-session and clears the displayed situation

`evict(session, actor)` SHALL read the session's displayed fingerprint (the situation the player
is dismissing, even if they moved away), remove that fingerprint's cache entry and negative memo
from the global stores, remove that session from that fingerprint's pending subscribers
(retiring the generation when it was the last subscriber), increment the session's generation
token, and set its `options_state` to `{owner_actor_id, fingerprint: None, status: unavailable,
token+1}`.

#### Scenario: Dismiss leaves a second window untouched
- **WHEN** one of two sessions on the same puppet dismisses while a generation is in flight
- **THEN** the dismissing session's completion becomes inert, the other session's subscriber
  entry, token, state, and eventual publication are unaffected, and a later trigger regenerates
  the situation

#### Scenario: The cache and memo for the dismissed situation are gone
- **WHEN** the dismissed fingerprint is triggered again after the dismiss
- **THEN** the cached set and any negative memo for that fingerprint are absent, so a fresh
  generation starts

#### Scenario: Eviction reports success without raising
- **WHEN** `evict` completes
- **THEN** it SHALL return whether the eviction succeeded (a boolean) and SHALL NOT raise; a
  failed eviction SHALL leave the session's state unchanged, so the dismiss adapter rejects
  instead of reporting success

#### Scenario: Eviction is state-only, the dispatcher publishes
- **WHEN** an eviction succeeds
- **THEN** eviction SHALL NOT send a presentation update itself (state-only contract,
  dismiss-options-action D1): the dismissal's single `ui_update` with
  `suggestions.status="unavailable"` is published by the dispatcher completion path after the
  `options.dismiss` adapter declares `context_actions` affected

#### Scenario: Other sessions are untouched
- **WHEN** one session evicts
- **THEN** eviction SHALL leave every other session's subscriber entries, tokens, states, and
  future publications intact; a later trigger for the same situation SHALL regenerate

### Requirement: The negative memo applies to transport failures only

A transport failure SHALL memoize the fingerprint for `NEGATIVE_MEMO_TTL` (30 s); a trigger
within the TTL SHALL resolve to `degraded` immediately without transport work; after the TTL a
trigger SHALL attempt once more. A degraded outcome that is not a transport failure SHALL NOT be
memoized, and a successful generation SHALL NOT be memoized negatively.

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

#### Scenario: Non-transport degrades are named
- **WHEN** a degraded outcome arises without a transport failure
- **THEN** the non-memoized class includes validation exhaustion, prompt unavailability, a
  disabled profile, or a response that failed the guardrail's declared output schema (the
  client succeeded, so the failure is never observed at the client boundary)

#### Scenario: Discrimination is positional, not by failure kind
- **WHEN** an `LLMTransportError` is raised somewhere in the stack
- **THEN** a client that itself raises `LLMTransportError` (even one carrying the reason
  `"malformed"`) IS the memoized class, because it was observed at the client boundary, while
  the guardrail's own `LLMTransportError` raised after a successful client round-trip is not

#### Scenario: The wrapper observes client-boundary failures
- **WHEN** the service distinguishes the two failure positions through the controlled-failure
  fallback
- **THEN** it calls the layer through a thin client wrapper that observes `LLMTransportError`
  (raised or errbacked) on the injected client, and a degraded outcome with an observed
  transport failure is the memoized class while every other degrade is not (the disabled
  profile resolves before any client call, so it is never observable through the wrapper)

#### Scenario: The observation mechanism may evolve
- **WHEN** a later change revisits the discrimination
- **THEN** it MAY replace the observation with the layer's typed outcome without changing the
  memo semantics

### Requirement: Watcher registry resolves live sessions for the room-entry hook

`watchers_for(actor)` in `web/webclient/presentation/watchers.py` SHALL return the live
webclient sessions watching the given puppet, each with its **current** coordinator epoch read
at query time.

#### Scenario: A puppeted window registers and resolves
- **WHEN** a webclient session with a puppet synchronizes, then synchronizes again, and the
  room-entry hook asks for watchers of that puppet
- **THEN** the session appears exactly once (with its current coordinator epoch), and sessions
  without a puppet or of non-webclient transports are never registered

#### Scenario: Disconnected sessions are pruned at the next registration
- **WHEN** a session disconnects and any later registration occurs
- **THEN** the disconnected session no longer appears in `watchers_for` results

#### Scenario: Registry shape and idempotent registration
- **WHEN** the registry is maintained
- **THEN** it SHALL be a per-actor map keyed by session identity, and registration is
  idempotent per session (repeated `ui_sync` and command settlements update the entry, never
  append)

#### Scenario: Stale entries are pruned and harmless
- **WHEN** an entry's session is no longer connected or no longer puppets the recorded actor
- **THEN** the entry SHALL be pruned, and stale entries SHALL be harmless because the epoch
  guard drops their pushes

### Requirement: Scheduling never raises and never blocks

`schedule_action_options(actor, *, watchers, client=None) -> defer.Deferred | None` SHALL be
fire-and-forget: fingerprint derivation, context assembly, client construction, and Deferred
acquisition SHALL be wrapped so any synchronous failure (vanished room, malformed context, any
exception) logs a bounded diagnostic and resolves to nothing; the call SHALL NOT raise into its
caller's critical section.

#### Scenario: A vanished room makes the trigger a logged no-op
- **WHEN** the actor's location cannot be resolved at trigger time
- **THEN** the call returns `None`, logs a bounded diagnostic, and the caller's command path
  continues unaffected

#### Scenario: A disabled profile never touches transport
- **WHEN** the `action_options` profile is disabled
- **THEN** scheduling resolves every trigger to `degraded`, the offline stub's `get_response` is
  never invoked, no memo is recorded, and no connection is opened

#### Scenario: Client defaulting and the offline stub
- **WHEN** `client=None` is passed
- **THEN** scheduling SHALL build the `action_options` profile client, or the non-`None`
  offline stub when the profile is disabled (whose `get_response` SHALL fail loudly if ever
  invoked)

#### Scenario: Scheduled failures are logged, never raised
- **WHEN** a successfully scheduled generation fails
- **THEN** its failure path SHALL log and resolve to nothing

#### Scenario: Single caller, ephemeral writes only
- **WHEN** the service's production integration is inspected
- **THEN** it SHALL be the single production caller of `generate_action_options`, SHALL import
  no state writer, and SHALL write only ephemeral cache/presentation state — it SHALL never
  mutate canonical game state

### Requirement: Current situation freshness gates session-backed suggestions

The action-options service SHALL expose one shared, read-only exploration situation derivation
that produces the same fingerprint and deterministic input data for scheduling and presentation.
Before rendering any session snapshot with status `generating`, `ready`, or `degraded`, the
`context_actions` suggestions presenter SHALL require its snapshot fingerprint to equal the
context fingerprint; a mismatch SHALL render unavailable.

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

#### Scenario: The context factory carries the current fingerprint
- **WHEN** a presentation context is built
- **THEN** the presentation-context factory SHALL carry the current derived fingerprint, or
  `None` when no exploration situation can be derived

#### Scenario: A mismatched fingerprint emits the bare unavailable object
- **WHEN** the snapshot fingerprint is missing or mismatched
- **THEN** the presenter SHALL emit exact `{"status": "unavailable"}` with a bounded
  diagnostic and SHALL emit none of the old cards

#### Scenario: The gate is read-only
- **WHEN** the freshness gate runs
- **THEN** it SHALL be read-only and SHALL not schedule, evict, or mutate canonical state

### Requirement: All committed player relocations and terminal combat returns trigger options

Every committed relocation of an account-owned `PlayerCharacter`, including Exit traversal and a
direct `move_to()` call with movement hooks enabled, SHALL register one fire-and-forget
action-options scheduling callback through `transaction.on_commit`. A successful combat action
that has returned its actor to exploration SHALL schedule action options after the dispatcher's
completion publication, using `watchers_for(actor)`.

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

#### Scenario: The observer skips non-committed and NPC movement
- **WHEN** a relocation occurs
- **THEN** the observer SHALL not run for NPC movement, rollback compensation with hooks
  disabled, or a failed transaction

#### Scenario: Lifecycle triggers reuse the scheduling contract
- **WHEN** a relocation or terminal-combat trigger schedules
- **THEN** these lifecycle triggers SHALL use the existing watcher, token, epoch, and no-raise
  scheduling contract

### Requirement: Dismissal prevents replay from a concurrent older generation

The service SHALL tag each cache entry and pending generation for a fingerprint with a monotonic
ephemeral generation number, and `evict(session, actor)` SHALL record a per-session,
per-fingerprint minimum displayable generation number in a separate bounded `session.ndb` barrier
store, in addition to its existing state/token eviction. A later trigger for that session SHALL
not replay a cache entry or join a pending generation whose number is older than the recorded
minimum.

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

#### Scenario: Barrier store bounds and clearing
- **WHEN** the barrier store is maintained
- **THEN** it SHALL retain no more than the option-cache capacity, SHALL clear on puppet change
  and unpuppet, and SHALL never alter the exact `options_state` shape

#### Scenario: Fingerprint chains carry one active generation and one successor
- **WHEN** generations are registered for a fingerprint
- **THEN** each fingerprint SHALL own a chain with one joinable active generation and at most
  one successor

#### Scenario: Shared older generation keeps its subscribers
- **WHEN** another session still subscribes to an older active generation that a dismissing
  session leaves
- **THEN** the service SHALL retain its delivery and queue the dismissed session on the
  successor

#### Scenario: Losing the final subscriber hands off through the chain
- **WHEN** an active generation with a queued successor later loses its final subscriber
- **THEN** it SHALL leave the joinable registry immediately while an identity-guarded detached
  completion owned by the chain starts the still-current successor exactly once when the old
  Deferred settles, and the successor SHALL derive fresh context after that settlement

#### Scenario: Newer state is never overwritten and barriers clear on eligible delivery
- **WHEN** generations complete out of order
- **THEN** older completions SHALL never overwrite a newer cache entry, and a barrier SHALL
  clear only when its session receives an outcome from an eligible generation

### Requirement: Retired pending generations are removed by identity immediately

When `evict()` removes the final subscriber from a pending generation, the service SHALL mark that
generation retired and remove that exact generation from the joinable pending registry immediately.

#### Scenario: A retired completion cannot remove replacement work
- **WHEN** the last subscriber dismisses generation N, a later trigger starts generation N+1 for
  the same fingerprint, and generation N then completes
- **THEN** generation N's completion produces no cache or delivery and generation N+1 remains in
  the pending registry until it settles

#### Scenario: Chain-only detached reference for successor handoff
- **WHEN** a current successor waits behind a retired generation
- **THEN** the fingerprint chain alone MAY retain an identity-bearing detached completion
  reference solely for successor handoff, and that reference SHALL not be discoverable or
  joinable by scheduling

#### Scenario: Completion and cleanup are identity-guarded
- **WHEN** the retired generation's eventual completion and Deferred cleanup run
- **THEN** they SHALL write no cache, memo, or session state, and SHALL not remove a newer
  active or successor generation registered for the same fingerprint
