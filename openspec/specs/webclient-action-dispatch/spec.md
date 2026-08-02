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
The action registry SHALL bind each stable action ID to one exact payload validator and one adapter, SHALL reject duplicate registration, and SHALL reject unknown action IDs. This foundation SHALL register no production game action; tests SHALL use an isolated test-only proof adapter that cannot be reached in production configuration.

#### Scenario: Unknown action cannot become a command
- **WHEN** a client submits an unregistered action ID or a string resembling an Evennia command
- **THEN** the dispatcher rejects it with a schema-valid `ui_action_result` (outcome `rejected`, stable code `unknown_action`) carrying the request ID, and it is not routed through the text command parser

#### Scenario: Malformed action payload rejects without a protocol error
- **WHEN** a client submits a globally valid `ui_action` envelope whose registered action payload fails its exact schema
- **THEN** the dispatcher sends a schema-valid `ui_action_result` (outcome `rejected`, stable code `malformed_payload`) without invoking the adapter and without emitting a `ui_protocol_error`

#### Scenario: Duplicate action registration fails
- **WHEN** two adapters attempt to register the same action ID
- **THEN** registry construction fails rather than selecting one by registration order

#### Scenario: Foundation production registry is mutation-empty
- **WHEN** the foundation action registry is loaded outside tests
- **THEN** it exposes no production gameplay adapter while the dispatcher and validation infrastructure remain available

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

#### Scenario: Successful completion refreshes before result
- **WHEN** a proof adapter commits successfully and declares an affected panel
- **THEN** the server emits one newer panel update, then its success result with the same revision, and only then admits a later mutation

#### Scenario: Client waits for declared presentation revision
- **WHEN** an action result naming revision 12 arrives while the accepted client store remains at revision 11
- **THEN** the browser records the result but keeps mutation controls locked until it accepts revision 12 or a later recovery snapshot

#### Scenario: Concurrent sync does not cause a stale next action
- **WHEN** sync and action completion publications occur close together and the player immediately chooses a later action after unlock
- **THEN** the later action uses the newest accepted revision and is not stale solely because result and refresh arrived out of order

### Requirement: Action results are safe and disconnects are never retried automatically
Every admitted action whose transport-and-puppet sequence remains active through publication SHALL resolve with the exact result envelope defined by the OOB protocol. A retired sequence SHALL publish nothing into its replacement. Internal results SHALL expose no traceback, local path, raw exception, or raw payload. If transport loss makes an outcome uncertain, the browser SHALL NOT automatically resubmit the request and SHALL show an uncertain-result notice after canonical resynchronization.

#### Scenario: Domain rejection is stable and safe
- **WHEN** a deterministic API rejects a request
- **THEN** the browser receives outcome `rejected`, a stable code and Traditional Chinese message, and no internal exception details

#### Scenario: Disconnect after submit does not duplicate mutation
- **WHEN** the WebSocket closes after sending an action but before receiving its result
- **THEN** the reconnected browser requests a full snapshot, does not resend the prior request automatically, and displays that its outcome could not be confirmed
