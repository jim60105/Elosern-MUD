## Purpose

Exact bounded UI action validation, allowlisted adapters, session identity, stale and duplicate handling, in-flight serialization, and deterministic-core mutation boundaries.

## Requirements


### Requirement: UI actions use an exact bounded request envelope
`ui_action` SHALL accept exactly `protocol_version`, `presentation_epoch`, `request_id`, `base_revision`, `action_id`, and `payload`. Protocol version SHALL be integer 1; epoch SHALL satisfy the protocol's exact 22-character form; request ID SHALL be 1..64 characters from ASCII letters, digits, colon, underscore, and hyphen; action ID SHALL be 1..64 lowercase dotted identifier characters; base revision SHALL be a non-negative JavaScript-safe integer excluding booleans; and payload SHALL be an object within global bounds plus its registered action-specific smaller schema. Unknown fields or invalid global values SHALL be rejected before action lookup.

#### Scenario: A valid action reaches action lookup
- **WHEN** an authenticated puppeted WebSocket session submits an exact envelope within every global bound
- **THEN** the dispatcher proceeds to epoch, revision, registry, and action-payload validation

#### Scenario: An oversized action is rejected early
- **WHEN** an action exceeds the envelope size, depth, field, string, or list bound
- **THEN** the dispatcher invokes no action-specific validator and no adapter

### Requirement: Action identity comes only from the authenticated session
The dispatcher SHALL accept actions only from authenticated WebSocket sessions with an active puppet and SHALL pass only `session.puppet` as the actor. The action payload SHALL NOT accept an actor, account, session, or puppet identifier, and no error response SHALL disclose another actor's state.

#### Scenario: Payload cannot select a different actor
- **WHEN** a client includes an actor-like unknown field in the envelope or action payload
- **THEN** exact-schema validation rejects the request without adapter invocation

#### Scenario: Unpuppeted action is rejected
- **WHEN** an anonymous or logged-in but unpuppeted session submits `ui_action`
- **THEN** no adapter runs and no character state is returned

### Requirement: Action registries are allowlisted and duplicate-safe
The action registry SHALL bind each stable action ID to one exact payload validator and one adapter, SHALL reject duplicate registration, and SHALL reject unknown action IDs. The production registry SHALL contain exactly the three combat adapters `combat.cast`, `combat.flee`, and `combat.forfeit`, the seven service adapters `guild.register`, `guild.quest_accept`, `guild.quest_abandon`, `guild.quest_turnin`, `guild.exam_start`, `shop.buy`, and `shop.sell`, the two inventory adapters `inventory.use` and `inventory.toggle_equip`, the five creation adapters `creation.preset`, `creation.custom`, `creation.concept`, `creation.activate`, and `creation.reset`, the ten exploration adapters `explore.move`, `explore.look`, `explore.talk_scripted`, `explore.talk_freeform`, `explore.party_invite`, `explore.party_leave`, `explore.engage`, `explore.wait`, `explore.possess`, and `explore.possess_release`, the `options.dismiss` action, the four title adapters `title.accept`, `title.decline`, `title.equip`, and `title.remove`, and the persona-editing adapter `character.persona.update`, each with its own exact validator and deterministic adapter, until another owning change adds an explicitly specified action. Tests MAY use an isolated proof adapter that cannot be reached in production configuration. No action SHALL route an action ID or payload string through the text command parser.

#### Scenario: Unknown action cannot become a command
- **WHEN** a client submits an unregistered action ID or a string resembling an Evennia command
- **THEN** the dispatcher rejects it with a schema-valid `ui_action_result` (outcome `rejected`, stable code `unknown_action`) carrying the request ID, and it is not routed through the text command parser

#### Scenario: Malformed action payload rejects without a protocol error
- **WHEN** a client submits a globally valid `ui_action` envelope whose registered action payload fails its exact schema
- **THEN** the dispatcher sends a schema-valid `ui_action_result` (outcome `rejected`, stable code `malformed_payload`) without invoking the adapter and without emitting a `ui_protocol_error`

#### Scenario: Duplicate action registration fails
- **WHEN** two adapters attempt to register the same action ID
- **THEN** registry construction fails rather than selecting one by registration order

#### Scenario: Production registry exposes only specified combat, service, inventory, creation, exploration, dismiss, title, and persona mutations
- **WHEN** the production registry is loaded after the possession-webclient change
- **THEN** its action IDs are exactly `combat.cast`, `combat.flee`, `combat.forfeit`, `guild.register`, `guild.quest_accept`, `guild.quest_abandon`, `guild.quest_turnin`, `guild.exam_start`, `shop.buy`, `shop.sell`, `inventory.use`, `inventory.toggle_equip`, `creation.preset`, `creation.custom`, `creation.concept`, `creation.activate`, `creation.reset`, `explore.move`, `explore.look`, `explore.talk_scripted`, `explore.talk_freeform`, `explore.party_invite`, `explore.party_leave`, `explore.engage`, `explore.wait`, `explore.possess`, `explore.possess_release`, `options.dismiss`, `title.accept`, `title.decline`, `title.equip`, `title.remove`, and `character.persona.update`, each with its own exact validator and deterministic adapter

#### Scenario: Test proof action remains isolated
- **WHEN** a dispatcher test installs a synthetic proof adapter
- **THEN** that adapter exists only in the test-owned registry and does not appear in the production registry


### Requirement: Adapters may receive the authenticated session through a fixed optional third parameter

Every registered adapter SHALL declare the callable signature `adapter(actor, payload, session=None)`. The dispatcher SHALL invoke every adapter with the authenticated session as the third positional argument and SHALL never use runtime signature introspection to decide what to pass. A direct two-argument invocation of an adapter (for example in a unit test) SHALL behave exactly as before through the default. The session SHALL be used only for per-session presentation targeting (for example dismiss eviction); adapters SHALL NOT read or write character state through it, and the actor identity rule (session.puppet only) is unchanged.

#### Scenario: A dispatched adapter receives the session

- **WHEN** the dispatcher admits an action whose adapter declares the three-parameter ABI
- **THEN** the adapter is invoked exactly once with the authenticated session as the third positional argument

#### Scenario: A two-argument direct invocation remains valid

- **WHEN** an existing test calls a production adapter as `adapter(actor, payload)`
- **THEN** the call succeeds through the default with `session=None` and produces the same behavior as before this change

#### Scenario: No signature introspection at the call site

- **WHEN** the dispatcher invokes an adapter
- **THEN** it passes `(actor, payload, session)` positionally unconditionally, without inspecting the callable signature

### Requirement: Adapters preserve deterministic ownership boundaries
Every adapter SHALL re-resolve every client-referenced identity, re-authorize current domain state, and call a public API owned by the deterministic core or its explicitly named subsystem owner. An adapter SHALL NOT assign `.db`, `AttributeProperty`, traits, buffs, sexual state, map knowledge, quest state, wallet, inventory, or location directly. Presenters SHALL NOT invoke adapters.

#### Scenario: A proof adapter receives the session actor
- **WHEN** the isolated test adapter is dispatched successfully
- **THEN** it receives the exact active puppet supplied by the server session and executes through its declared callable once

#### Scenario: Presentation cannot dispatch a mutation
- **WHEN** a presenter is constructed and invoked
- **THEN** it has no dispatcher reference or action-adapter execution path

### Requirement: Stale presentation state prevents adapter invocation
Before action-specific dispatch, the request's presentation epoch and base revision SHALL exactly equal the newest values issued for the live session. A mismatch SHALL return a `stale` result, invoke no payload adapter, and emit a fresh full snapshot for recovery. Matching presentation state SHALL NOT replace domain validation.

#### Scenario: Stale revision performs no action
- **WHEN** an action carries the active epoch but an older base revision
- **THEN** the adapter call count remains zero, the result is `stale`, and the server emits current canonical state in a full snapshot

#### Scenario: Prior epoch performs no action
- **WHEN** an action from the browser's prior transport arrives after a new epoch is active
- **THEN** the adapter call count remains zero and the current transport receives stale recovery state

#### Scenario: Current revision still receives domain validation
- **WHEN** epoch and base revision match but an action-specific referenced object is no longer authorized
- **THEN** the adapter or deterministic API rejects the request without trusting the rendered preview

### Requirement: Completed request IDs are deduplicated within a bounded session cache
The dispatcher SHALL retain a bounded insertion-ordered cache of completed action results for each live transport-and-puppet presentation sequence. Repeating a cached request ID SHALL return its prior result without revalidation or adapter execution. Eviction SHALL remove the oldest completed entries. Transport replacement or puppet change SHALL atomically retire the old epoch and discard its completed-result cache and in-flight marker.

#### Scenario: Duplicate successful request executes once
- **WHEN** the same valid request ID is submitted twice during one live session
- **THEN** the adapter executes once and the second submission receives the cached first result

#### Scenario: Request cache remains bounded
- **WHEN** more completed unique requests arrive than the configured cache capacity
- **THEN** the cache never exceeds that capacity and evicts the oldest completed result

#### Scenario: Reconnect does not reuse the old cache
- **WHEN** the transport disconnects and a new transport starts a new epoch
- **THEN** the prior transport's request-result cache is unavailable to the new session sequence

#### Scenario: Puppet change does not replay another puppet's result
- **WHEN** one WebSocket changes from puppet A to puppet B and resubmits a request ID completed by puppet A
- **THEN** puppet A's cached result is not replayed and no result or presentation from the retired sequence is published to puppet B

### Requirement: Each session admits only one mutation in flight
The server SHALL permit at most one distinct UI mutation in flight per live transport-and-puppet sequence, regardless of browser control state. A concurrent distinct action SHALL return outcome `rejected` with code `busy` and the current revision without adapter invocation or disturbing the admitted request. `ui_sync` SHALL remain available while an action is in flight. Coordinator publication SHALL serialize sync snapshots and action completion so a sync may occur before or after, but not between, a completion presentation and its result.

#### Scenario: Concurrent mutation is rejected server-side
- **WHEN** one proof adapter is held in flight and the same session submits a different request ID
- **THEN** the second adapter does not run and receives the stable busy result

#### Scenario: Sync remains available during mutation
- **WHEN** a valid `ui_sync` arrives while an action is in flight
- **THEN** the server may return a full read-only snapshot without cancelling or duplicating the mutation

#### Scenario: Internal failure unlocks the session
- **WHEN** an adapter raises an unexpected exception
- **THEN** the server logs a correlation ID, returns a generic error, emits recovery state, and permits a later distinct action

#### Scenario: Sync cannot interleave completion publication
- **WHEN** `ui_sync` and an admitted action Deferred complete concurrently
- **THEN** their presentation revisions are unique and ordered, and no sync snapshot is emitted between the action's completion presentation and matching result

#### Scenario: Retired sequence completion cannot cross puppet boundary
- **WHEN** an old puppet's already-started adapter settles after the session adopts a new puppet and epoch
- **THEN** its captured deterministic call is not retried or redirected and it publishes no result or panel state into the new sequence

### Requirement: Admitted action completion publishes canonical state before unlocking
After an admitted non-duplicate action settles, the coordinator SHALL build presentation from committed canonical state and allocate exactly one next revision inside one publication critical section. Success or domain rejection with a declared nonempty affected-panel set SHALL emit one update; stale, internal error, or an empty affected-panel set SHALL emit one full snapshot. The server SHALL send that presentation before an exact `ui_action_result` naming the same revision and SHALL release the server in-flight marker only after both sends. The browser SHALL release its mutation lock only after receiving the result and accepting presentation state at or above `presentation_revision`. A cached duplicate MAY replay its prior result without a new presentation, and a busy pre-admission rejection SHALL NOT alter the admitted request's lock.

An action whose committed effect retires the session's presentation and dispatch sequence — a puppet change — SHALL NOT perform that effect inside its adapter, because a retired sequence publishes nothing into its replacement and the request would receive no result at all. Such an action SHALL instead decide and report synchronously and schedule its effect to run only after its result has been sent and both the server in-flight marker and the browser mutation lock have been released. Its result SHALL report the outcome of the authorization decision, which SHALL be complete before the result is sent. The scheduled effect SHALL re-validate that decision against committed state, SHALL verify that the effect actually took hold rather than assuming an API that can refuse silently succeeded, SHALL report any failure to the player through the ordinary message channel at a severity matching how far the failure got, and SHALL publish recovery presentation whenever a puppet remains to render it for. Such an action SHALL declare no affected panels and SHALL emit no completion presentation, so no state derived from the retiring puppet is published at the retiring epoch.

#### Scenario: Successful completion refreshes before result
- **WHEN** a proof adapter commits successfully and declares an affected panel
- **THEN** the server emits one newer panel update, then its success result with the same revision, and only then admits a later mutation

#### Scenario: Client waits for declared presentation revision
- **WHEN** an action result naming revision 12 arrives while the accepted client store remains at revision 11
- **THEN** the browser records the result but keeps mutation controls locked until it accepts revision 12 or a later recovery snapshot

#### Scenario: Concurrent sync does not cause a stale next action
- **WHEN** sync and action completion publications occur close together and the player immediately chooses a later action after unlock
- **THEN** the later action uses the newest accepted revision and is not stale solely because result and refresh arrived out of order

#### Scenario: A sequence-retiring action delivers its result before its effect
- **WHEN** an admitted action whose committed effect is a puppet change completes
- **THEN** its exact `ui_action_result` is sent and the in-flight marker released at the still-live epoch, and only afterwards does the puppet change retire the sequence

#### Scenario: A sequence-retiring adapter that transitions inline is a defect
- **WHEN** an adapter performs a puppet change before returning
- **THEN** the completion guard finds the sequence retired and sends no result, leaving the request unanswered — which is why such an effect is required to be scheduled after the result instead

#### Scenario: A scheduled effect's failure is reported outside the retired sequence
- **WHEN** a scheduled puppet change fails after its success result was sent
- **THEN** the player is informed through the ordinary message channel, an operational error event is emitted, and recovery presentation is published for whatever puppet the session still holds, rather than the failure being silently swallowed

#### Scenario: A silently refused effect is not reported as done
- **WHEN** the scheduled effect calls an API that refuses by returning without raising
- **THEN** the verification step detects that the effect did not take hold and the recovery path runs, rather than the transition proceeding as though it had succeeded

### Requirement: Action results are safe and disconnects are never retried automatically
Every admitted action whose transport-and-puppet sequence remains active through publication SHALL resolve with the exact result envelope defined by the OOB protocol. A retired sequence SHALL publish nothing into its replacement. Internal results SHALL expose no traceback, local path, raw exception, or raw payload. If transport loss makes an outcome uncertain, the browser SHALL NOT automatically resubmit the request and SHALL show an uncertain-result notice after canonical resynchronization.

#### Scenario: Domain rejection is stable and safe
- **WHEN** a deterministic API rejects a request
- **THEN** the browser receives outcome `rejected`, a stable code and Traditional Chinese message, and no internal exception details

#### Scenario: Disconnect after submit does not duplicate mutation
- **WHEN** the WebSocket closes after sending an action but before receiving its result
- **THEN** the reconnected browser requests a full snapshot, does not resend the prior request automatically, and displays that its outcome could not be confirmed

### Requirement: Dispatch rejects no-puppet actions with a bounded response

The action dispatcher SHALL return a bounded rejection (stable code, no character data) for actions submitted without a puppeted actor, instead of silently dropping them.

#### Scenario: No-puppet action returns a stable rejection

- **WHEN** `ui_action` is dispatched while `session.puppet` is None
- **THEN** the client receives a rejection with a stable code and no character state

### Requirement: combat.cast payload carries an optional bounded scale
The `combat.cast` payload validator SHALL accept an optional `scale` field alongside `skill_key`,
`target_ids`, and `target_shorthand`. The value SHALL be a JSON number exactly equal to one member of
the `freeform_cast_scales` table (`0.25`, `0.5`, `1.0`, `2.0`, `4.0`); a boolean, a non-number, or a
non-member number SHALL be rejected as `malformed_payload` without adapter invocation. An absent
field SHALL default to `1.0`. The field MAY accompany every target form (NONE, SELF, SINGLE, and
AREA, including shorthands). The adapter SHALL thread the validated scale into
`revalidate_submission` and `submit_player_action`, so a scale the deterministic gate forbids is
rejected before initiative with the stable `SCALED_CAST_FORBIDDEN` code.

#### Scenario: A member scale is accepted on every target form
- **WHEN** a client submits `combat.cast` with `scale: 2.0` together with an explicit SINGLE
  `target_ids` list, and separately with an AREA `target_shorthand`
- **THEN** both payloads pass validation and the adapter revalidates and resolves the cast at
  `scale == 2.0`

#### Scenario: A non-member scale is rejected as malformed
- **WHEN** a client submits `scale: 3.0`, `scale: "2"`, or `scale: true`
- **THEN** the payload is rejected with `malformed_payload` and no adapter runs

#### Scenario: An absent scale defaults to one
- **WHEN** a client submits a valid `combat.cast` without a `scale` field
- **THEN** the adapter behaves exactly as before this change (`scale == 1.0`)

### Requirement: A non-success action result surfaces its message exactly once

When the client recognizes a matching non-success `ui_action_result` — outcome `rejected`, `stale`, or `error`, carrying the same request id and epoch as its in-flight dispatch — and the creation overlay is not the presenting surface, it SHALL make the envelope's server-authored message visible to the player exactly once per recognized result, rendered as one narrative error line carrying that message verbatim through the bounded narrative path. The client SHALL NOT paraphrase, translate, or synthesize replacement text while the envelope carries a message, and SHALL show a single stable fallback line when a recognized non-success result carries none. A successful result SHALL surface no additional line. While the creation overlay is mounted it SHALL be the presenting surface: the overlay SHALL render the recognized non-success result's message verbatim in an always-reachable result region across every wizard stage, and no narrative line SHALL be appended for that result. Surfacing SHALL NOT alter the in-flight lock, the revision-gated release (including the `stale` rule that holds the lock until the recovery snapshot commits), the uncertain-result notice, or the no-automatic-resubmit rule.

#### Scenario: A rejected move explains itself in the feed

- **WHEN** a dispatched action receives a matching rejected result carrying a server-authored message while exploration mode is presented
- **THEN** exactly one narrative line shows that message verbatim, the player keeps keyboard focus without any modal, and no result echo line accompanies it beyond the pre-existing dispatch command echo

#### Scenario: A stale admission speaks through the recovery

- **WHEN** the client dispatches against a superseded `base_revision` and receives a matching `stale` result followed by the recovery snapshot
- **THEN** the stale message appears once as a narrative error line, the lock still releases only when the recovery revision commits, and the client never resubmits automatically

#### Scenario: One recognized result yields one line

- **WHEN** the same non-success result is delivered or re-observed by the client more than once, including with another request's result observed in between
- **THEN** the narrative shows the message once and a successful result appends no error line

#### Scenario: Creation mode keeps one presenting surface

- **WHEN** a non-success result arrives while the creation overlay is mounted
- **THEN** the overlay shows the envelope's message verbatim in its result region and the narrative feed gains no duplicate line

#### Scenario: A message-less non-success still speaks

- **WHEN** a recognized non-success result carries no usable message
- **THEN** the narrative shows the single stable fallback line rather than failing silently
