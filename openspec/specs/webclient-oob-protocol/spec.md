## Purpose

Versioned WebSocket OOB envelopes, epoch/revision ordering, authenticated synchronization, presenter isolation, and degraded text-mode recovery.

## Requirements


### Requirement: Elosern OOB messages use exact versioned envelopes
The WebClient foundation SHALL carry each Elosern OOB message as exactly one JSON object in the first positional argument of Evennia's existing command/args/kwargs transport triple. Protocol version 1 SHALL define client messages `ui_sync` and `ui_action` and server messages `ui_snapshot`, `ui_update`, `ui_action_result`, and `ui_protocol_error`. Every envelope SHALL reject unknown fields, invalid scalar types, non-finite numbers, canonical UTF-8 JSON over 65,536 bytes, nesting deeper than 8, an object with more than 64 fields, a list with more than 128 items, a generic string over 2,048 Unicode code points, or an integer outside
`-9,007,199,254,740,991..9,007,199,254,740,991` (the full JavaScript-safe range); field-specific
limits SHALL be equal or smaller.

#### Scenario: A version-1 message uses the Evennia transport
- **WHEN** the server emits a valid version-1 full snapshot
- **THEN** the transport command is `ui_snapshot`, its first positional argument is the complete envelope object, and no protocol field is encoded as a transport keyword argument

#### Scenario: An exact envelope rejects additional input
- **WHEN** a client sends an otherwise valid `ui_sync` or `ui_action` object with an unknown field, a boolean in an integer field, or a value over a global bound
- **THEN** the server rejects the message before synchronization or adapter dispatch and returns a safe protocol error without a traceback or raw payload

#### Scenario: Negative safe integers pass the global bound
- **WHEN** an OOB envelope carries a negative integer within the JavaScript-safe range, such as a signed combat modifier value (`defense: -15` or `accuracy: -10`)
- **THEN** the global JSON-safety check accepts it and the value reaches the client unchanged

#### Scenario: Integers outside the safe range are rejected
- **WHEN** an OOB envelope carries an integer below `-9,007,199,254,740,991` or above `9,007,199,254,740,991`
- **THEN** the envelope is rejected before dispatch or adoption

### Requirement: Full snapshots and updates have registered replacement semantics
A version-1 `ui_snapshot` SHALL contain exactly `protocol_version`, `presentation_epoch`, `revision`, `mode`, `panels`, `layout_version`, and `server_time`. A `ui_update` SHALL contain the same exact top-level field set, with a nonempty registered subset in `panels`. `protocol_version` SHALL be integer 1; epoch SHALL be exactly 22 URL-safe ASCII characters generated from 128 random bits; snapshot/update revisions SHALL be positive safe integers excluding booleans; mode SHALL be `creation`, `exploration`, `combat`, or `dialogue`; layout version SHALL be in `1..65,535`; panel names SHALL be 1..64 lowercase identifier characters; and panel count SHALL not exceed 32. `server_time` SHALL contain exactly `year`, `season_index`, `season_label`, `day_in_season`, `hour`, `minute`, and `second`, bounded respectively to the safe non-negative integer range, `0..3`, 1..32 Unicode code points, `1..90`, `0..23`, `0..59`, and `0..59`. Every included update panel SHALL completely replace the prior value; the protocol SHALL NOT use JSON Patch or merge unknown nested state. Because an update's `mode` is recomputed at publication time, the committed mode SHALL NOT diverge from the committed dialogue panel: a `ui_update` whose recomputed mode is `dialogue` SHALL name the `dialogue` panel in its subset, so the client can never hold a dialogue-mode presentation while its stored dialogue panel is stale.

#### Scenario: Full synchronization replaces the complete store
- **WHEN** the browser accepts a valid `ui_snapshot`
- **THEN** it atomically replaces every prior panel and the prior mode, layout version, and server-time display with the snapshot values

#### Scenario: A panel update is a full replacement
- **WHEN** the browser accepts a newer `ui_update` containing the `status` panel
- **THEN** the new status object completely replaces the previous status object without retaining omitted nested fields

#### Scenario: Unknown panel names are rejected
- **WHEN** a snapshot or update contains a panel name absent from the registered panel allowlist
- **THEN** the client rejects that presentation message and does not render or merge the unknown panel

#### Scenario: Update metadata is complete
- **WHEN** the server emits a valid `ui_update`
- **THEN** it includes the active mode, current server time, and layout version together with its epoch, new revision, and nonempty panel subset

#### Scenario: A dialogue-mode update always carries the dialogue panel
- **WHEN** an affected-panel update is published while the viewer's recomputed mode resolves to `dialogue` and its named subset omits the `dialogue` panel
- **THEN** the emitted update still carries a freshly rendered `dialogue` panel alongside the named subset, and the client never commits mode `dialogue` over a stale dialogue panel

### Requirement: Result and protocol-error envelopes are exact and non-overlapping
A version-1 `ui_action_result` SHALL contain exactly `protocol_version`, `presentation_epoch`, `request_id`, `outcome`, `code`, `message`, and `presentation_revision`, plus `correlation_id` only when outcome is `error`, plus the optional `data` slot only when outcome is `success` and the admitted adapter explicitly returns one. `data` SHALL be a JSON object of at most 8 fields, each field name 1..64 lowercase identifier characters and each value a JSON-safe scalar, object, or list within the global envelope bounds measured from the envelope root, and the canonical JSON size of the whole `data` object SHALL fit a fixed budget that reserves room for the seven standard envelope fields under the global canonical byte ceiling so an emitted envelope can never exceed it. It SHALL carry no actor, session, epoch, revision, exception, local path, or live object reference: the validator SHALL reject, recursively at every nesting level, any field name equal to a reserved state key (`actor`, `session`, `epoch`, `revision`, `presentation_epoch`, `presentation_revision`, `correlation_id`, `exception`, `traceback`, `local_path`) or containing one as a dot-separated segment, and JSON-safety SHALL reject live objects and unsupported value types structurally. Outcome SHALL be `success`, `rejected`, `stale`, or `error`; busy SHALL use outcome `rejected` and code `busy`. A version-1 `ui_protocol_error` SHALL contain exactly `protocol_version`, `code`, `message`, and boolean `reload_required`, plus `correlation_id` only when code is `internal_error`. Request IDs SHALL be 1..64 characters from ASCII letters, digits, colon, underscore, and hyphen; stable codes SHALL be 1..64 lowercase dotted or underscored identifier characters; messages SHALL be 1..512 Unicode code points; and correlation IDs SHALL be exactly 32 lowercase hexadecimal characters. Protocol errors SHALL contain no actor, panel, epoch, revision, request payload, exception, or local path.

#### Scenario: Internal action error has one safe correlation field
- **WHEN** an admitted adapter fails unexpectedly
- **THEN** its result uses outcome `error`, contains one bounded correlation ID and generic Traditional Chinese message, and contains no exception or presentation payload

#### Scenario: Protocol error cannot disclose presentation state
- **WHEN** synchronization is rejected for an unsupported version or unavailable presentation prerequisite
- **THEN** `ui_protocol_error` identifies the server protocol version, stable code, safe message, and reload requirement without an epoch, revision, panel, actor, or request payload

#### Scenario: Conditional correlation field is exact
- **WHEN** a non-error result or non-internal protocol error includes `correlation_id`, or an internal error omits it
- **THEN** exact envelope validation rejects the message

#### Scenario: A success result may carry an adapter data slot
- **WHEN** an admitted adapter returns a success result with a data payload
- **THEN** the emitted `ui_action_result` carries the bounded `data` object beside the standard fields, and both the server validator and the mirrored browser validator accept it while the browser store surfaces it to the requesting view

#### Scenario: A non-success result cannot carry a data slot
- **WHEN** a `rejected`, `stale`, or `error` result includes `data`, or a result's `data` is not an object, exceeds 8 fields, or carries a field over the global bound
- **THEN** exact envelope validation rejects the message on both the server emitter and the mirrored browser validator

#### Scenario: A data slot carries no state-identity key
- **WHEN** a result's `data` contains a reserved state key name (`actor`, `session`, `epoch`, `revision`, `presentation_epoch`, `presentation_revision`, `correlation_id`, `exception`, `traceback`, `local_path`) at any nesting level, directly or as a dot-separated segment of a composite key
- **THEN** exact envelope validation rejects the message on both the server validator and the mirrored browser validator

#### Scenario: Adapters without a data payload keep byte-identical envelopes
- **WHEN** any currently registered adapter completes with a result that returns no `data`
- **THEN** the emitted `ui_action_result` contains exactly the prior seven-field envelope (plus `correlation_id` when the outcome is `error`) with no `data` key present

### Requirement: Every panel payload has an exact availability discriminator
Each registered panel schema SHALL define an available form and the common unavailable form. The unavailable form SHALL contain exactly `schema_version`, `available: false`, and `reason`; reason SHALL contain bounded `code` and safe Traditional Chinese `message`, plus a bounded `correlation_id` only for an internal presenter failure. The unavailable form's `schema_version` SHALL equal the panel's registered schema version — the same version the panel's available form carries — so the client's registered-version gate accepts it. Available payloads SHALL contain `available: true` and only fields defined by their panel schema.

#### Scenario: Missing canonical data uses a safe unavailable value
- **WHEN** a presenter cannot read required canonical data without mutation
- **THEN** its panel uses the common unavailable form with a stable non-internal reason and no correlation ID

#### Scenario: Presenter exception uses correlated unavailable value
- **WHEN** a presenter raises an unexpected exception
- **THEN** its unavailable reason uses a generic message and bounded correlation ID matching the server log without exposing exception details

#### Scenario: Unavailable character payload carries the registered version
- **WHEN** the character presenter reports the common unavailable form for a character panel registered at schema version 3
- **THEN** the unavailable payload carries `schema_version: 3` and the client accepts it, and a payload carrying any other version (`schema_version: 2`) is rejected without replacing or merging the stored panel

### Requirement: Presentation ordering is scoped by transport and puppet epoch
The server SHALL generate a bounded cryptographically unpredictable presentation epoch for each live WebSocket transport and active-puppet sequence. Reconnection and puppet change SHALL create a new epoch and reset the ephemeral revision sequence. On each browser `connection_open`, the client SHALL begin a new local transport generation, retire the prior active epoch in bounded memory, clear presentation state, and enter `awaiting_initial_snapshot`. Only the first valid full snapshot delivered for the current generation with a non-retired epoch SHALL establish the active epoch; updates and results SHALL NOT establish it. Once active, every different-epoch presentation on that same transport SHALL be discarded. Epochs, generations, revisions, and retired-epoch memory SHALL NOT be persisted to Accounts, characters, Scripts, localStorage, or any canonical game record.

#### Scenario: Reconnect accepts a lower revision in a new epoch
- **WHEN** a browser previously rendered epoch A revision 40 and receives the first valid full snapshot for its reconnected transport as epoch B revision 1
- **THEN** it clears the old client state, atomically adopts epoch B revision 1, and renders the new snapshot

#### Scenario: A delayed prior-epoch message is discarded
- **WHEN** epoch B is active and a delayed snapshot or update from epoch A arrives with any revision
- **THEN** the browser discards it without changing state or requesting a mutation

#### Scenario: A non-newer revision in the active epoch is discarded
- **WHEN** the browser at epoch B revision 7 receives an epoch B snapshot or update with revision 7 or lower
- **THEN** it discards the message and retains revision 7 state

#### Scenario: Puppet change starts a distinct presentation sequence
- **WHEN** an authenticated session changes from one puppet to another
- **THEN** the server creates a new epoch and emits a full snapshot derived only from the new puppet

#### Scenario: Different epoch snapshot on one active socket is rejected
- **WHEN** epoch B is active for the current transport generation and that same generation receives a valid full snapshot for unknown epoch C
- **THEN** the browser rejects epoch C and retains epoch B state

#### Scenario: Prior receiver generation cannot establish state
- **WHEN** a message callback tagged with an older local transport generation fires after reconnection
- **THEN** the browser discards it before epoch or revision evaluation

### Requirement: Synchronization requires an authenticated WebSocket puppet
`ui_sync` SHALL accept exactly `{protocol_version: 1}` from an authenticated WebSocket session with an active puppet. Actor identity SHALL be obtained only from the session. Anonymous sessions, sessions without a puppet, unsupported protocol versions, non-WebSocket sessions, and client-supplied actor identity SHALL receive no character presentation state.

#### Scenario: A puppeted WebSocket session synchronizes
- **WHEN** an authenticated WebSocket session with an active puppet sends a valid version-1 `ui_sync`
- **THEN** the coordinator returns a full snapshot for that session's puppet

#### Scenario: A session without a puppet cannot read status
- **WHEN** an anonymous session or logged-in session without a puppet sends `ui_sync`
- **THEN** no snapshot containing actor, location, resource, condition, or combat state is emitted

#### Scenario: Telnet does not receive graphical OOB state
- **WHEN** a Telnet session sends normal commands or attempts the UI synchronization message
- **THEN** its ordinary text behavior remains available and it receives no Elosern graphical snapshot

### Requirement: Presenter registration and execution are isolated and read-only
The presentation registry SHALL reject duplicate panel names and SHALL expose only registered stable panel names to the coordinator. Each presenter SHALL receive session-derived read context, SHALL return JSON-safe panel data without invoking mutation APIs, and SHALL execute independently so one presenter failure cannot suppress other panels or narrative output. A presenter whose subject is the account owning the rendered puppet, rather than the puppet itself, SHALL derive that account from the rendered actor's own ownership link and SHALL be held to the identical read-only, isolation, and availability-discriminator contract as every puppet-subject presenter; it SHALL NOT widen the read context to the transport session and SHALL NOT read any account the rendered actor does not belong to. The registry SHALL derive each panel's registered schema version from the panel schema's single server-side constant in its presenter module, and the client's panel allowlist and per-panel schema-version re-checks SHALL mirror the same value under a dual-direction parity contract so the two never diverge.

#### Scenario: Duplicate presenter registration fails
- **WHEN** two presenters attempt to register the same stable panel name
- **THEN** registry construction fails rather than selecting one by import order

#### Scenario: One presenter exception is isolated
- **WHEN** one registered presenter raises while a full snapshot is built
- **THEN** the server logs its panel name and correlation ID, emits the common schema-valid unavailable value through that panel's registered schema metadata, and continues building every other panel

#### Scenario: Presentation does not mutate canonical state
- **WHEN** a full snapshot and a panel update are built for an actor
- **THEN** the actor's traits, buffs, sexual state, combat record, location, wallet, quests, and world-clock tick remain unchanged

#### Scenario: An account-subject presenter reads only the rendered actor's own account
- **WHEN** the account-subject panel is rendered for an actor while other accounts own characters in the same world
- **THEN** the payload names only characters belonging to the rendered actor's own account, and no other account's data is read or emitted

#### Scenario: Panel schema versions stay equal across server and client
- **WHEN** the parity contract compares, for every registered panel, the presenter module's schema-version constant, the registry's registered value, the client allowlist's mirrored value, and the client per-panel available-form re-check literal
- **THEN** all are numerically equal, and no registered panel stores a literal schema version that can drift from its module constant

### Requirement: WebClient text commands refresh presentation after completion
The project `text` input function SHALL preserve Evennia's ordinary command semantics and SHALL observe both callback and errback settlement without replacing the original Deferred value or Failure. It SHALL attempt a full snapshot from then-current canonical state only after a WebClient command settles and SHALL NOT emit graphical state for Telnet commands. Presentation failure SHALL be logged separately and SHALL NOT consume a command failure. Idle handling, nickname replacement, command output, session counters, and text access SHALL remain functional.

#### Scenario: A completed WebClient command refreshes state
- **WHEN** a puppeted WebClient submits an ordinary synchronous text command that changes canonical state
- **THEN** normal command output is delivered and a full snapshot reflecting the committed state is emitted after command completion

#### Scenario: A Telnet command remains text-only
- **WHEN** a Telnet player executes the same command
- **THEN** normal output and state change occur without an Elosern graphical snapshot

#### Scenario: Idle input remains idle handling
- **WHEN** the WebClient sends Evennia's configured idle command
- **THEN** the session idle counter is updated without command execution or a fabricated gameplay refresh

#### Scenario: Command errback preserves failure semantics
- **WHEN** a WebClient command handler Deferred settles through its errback path
- **THEN** the wrapper preserves the original Failure and ordinary error output while attempting at most one safe post-settlement refresh

### Requirement: Protocol failures degrade without disabling text play
Before a valid full snapshot, the WebClient SHALL disable graphical mutation controls. A malformed panel SHALL disable only that renderer and request at most one full resynchronization for the same failure episode. An incompatible protocol SHALL disable all graphical mutation controls and offer reload. OOB initialization failure SHALL leave narrative output and ordinary text input usable.

#### Scenario: Repeated malformed panel does not loop synchronization
- **WHEN** a malformed status payload is received again after the renderer's single recovery sync
- **THEN** the status surface remains unavailable and no additional automatic sync loop starts

#### Scenario: Protocol mismatch preserves command access
- **WHEN** the browser receives an unsupported protocol version
- **THEN** graphical mutations are locked and a reload notice is shown while ordinary text input remains usable

### Requirement: Unpuppet retires the active presentation and dispatch sequence

When a session unpuppets (OOC), the system SHALL retire the session's presentation coordinator and dispatch sequence (epoch, request cache, in-flight marker) and SHALL notify the client to clear character panels and lock mutations until the next puppet.

#### Scenario: OOC clears character UI and mutation access

- **WHEN** a WebClient session executes `ooc` (unpuppet)
- **THEN** the client receives a state transition that clears character panels and blocks further mutations, and the server retires the old sequence

#### Scenario: Repuppet of the same character starts a fresh sequence

- **WHEN** a session unpuppets and later repuppets the same character
- **THEN** the server publishes a new epoch/revision, does not reuse the old completed-result cache or in-flight marker, and the client applies the fresh snapshot

### Requirement: No-puppet actions receive a bounded rejection

When a `ui_action` arrives without a puppet, the system SHALL respond with a bounded protocol rejection (no character state) so the client can release its in-flight mutation lock.

#### Scenario: Stale click after OOC releases the client lock

- **WHEN** the client sends a `ui_action` while the session has no puppet
- **THEN** the server returns a bounded rejection envelope, and the client's mutation lock is released
