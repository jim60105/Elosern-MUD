## ADDED Requirements

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
token, set its `options_state` to `{owner_actor_id, fingerprint: None, status: unavailable,
token+1}`, and publish `suggestions.status="unavailable"` to that session. Eviction SHALL leave
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
exhaustion or a disabled profile — SHALL NOT be memoized. The service SHALL distinguish the two
through the layer's typed outcome (`OptionGenerationOutcome` with `reason`
`transport|validation|disabled`, or the controlled-failure fallback until the layer amendment
lands); a successful generation SHALL NOT be memoized negatively.

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