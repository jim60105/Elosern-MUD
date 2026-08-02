## Purpose

Versioned WebSocket OOB envelopes, epoch/revision ordering, authenticated synchronization, presenter isolation, and degraded text-mode recovery.

## Requirements


### Requirement: Elosern OOB messages use exact versioned envelopes
The WebClient foundation SHALL carry each Elosern OOB message as exactly one JSON object in the first positional argument of Evennia's existing command/args/kwargs transport triple. Protocol version 1 SHALL define client messages `ui_sync` and `ui_action` and server messages `ui_snapshot`, `ui_update`, `ui_action_result`, and `ui_protocol_error`. Every envelope SHALL reject unknown fields, invalid scalar types, non-finite numbers, canonical UTF-8 JSON over 65,536 bytes, nesting deeper than 8, an object with more than 64 fields, a list with more than 128 items, a generic string over 2,048 Unicode code points, or an integer outside `0..9,007,199,254,740,991`; field-specific limits SHALL be equal or smaller.

#### Scenario: A version-1 message uses the Evennia transport
- **WHEN** the server emits a valid version-1 full snapshot
- **THEN** the transport command is `ui_snapshot`, its first positional argument is the complete envelope object, and no protocol field is encoded as a transport keyword argument

#### Scenario: An exact envelope rejects additional input
- **WHEN** a client sends an otherwise valid `ui_sync` or `ui_action` object with an unknown field, a boolean in an integer field, or a value over a global bound
- **THEN** the server rejects the message before synchronization or adapter dispatch and returns a safe protocol error without a traceback or raw payload

### Requirement: Full snapshots and updates have registered replacement semantics
A version-1 `ui_snapshot` SHALL contain exactly `protocol_version`, `presentation_epoch`, `revision`, `mode`, `panels`, `layout_version`, and `server_time`. A `ui_update` SHALL contain the same exact top-level field set, with a nonempty registered subset in `panels`. `protocol_version` SHALL be integer 1; epoch SHALL be exactly 22 URL-safe ASCII characters generated from 128 random bits; snapshot/update revisions SHALL be positive safe integers excluding booleans; mode SHALL be `creation`, `exploration`, or `combat`; layout version SHALL be in `1..65,535`; panel names SHALL be 1..64 lowercase identifier characters; and panel count SHALL not exceed 32. `server_time` SHALL contain exactly `year`, `season_index`, `season_label`, `day_in_season`, `hour`, `minute`, and `second`, bounded respectively to the safe non-negative integer range, `0..3`, 1..32 Unicode code points, `1..90`, `0..23`, `0..59`, and `0..59`. Every included update panel SHALL completely replace the prior value; the protocol SHALL NOT use JSON Patch or merge unknown nested state.

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

### Requirement: Result and protocol-error envelopes are exact and non-overlapping
A version-1 `ui_action_result` SHALL contain exactly `protocol_version`, `presentation_epoch`, `request_id`, `outcome`, `code`, `message`, and `presentation_revision`, plus `correlation_id` only when outcome is `error`. Outcome SHALL be `success`, `rejected`, `stale`, or `error`; busy SHALL use outcome `rejected` and code `busy`. A version-1 `ui_protocol_error` SHALL contain exactly `protocol_version`, `code`, `message`, and boolean `reload_required`, plus `correlation_id` only when code is `internal_error`. Request IDs SHALL be 1..64 characters from ASCII letters, digits, colon, underscore, and hyphen; stable codes SHALL be 1..64 lowercase dotted or underscored identifier characters; messages SHALL be 1..512 Unicode code points; and correlation IDs SHALL be exactly 32 lowercase hexadecimal characters. Protocol errors SHALL contain no actor, panel, epoch, revision, request payload, exception, or local path.

#### Scenario: Internal action error has one safe correlation field
- **WHEN** an admitted adapter fails unexpectedly
- **THEN** its result uses outcome `error`, contains one bounded correlation ID and generic Traditional Chinese message, and contains no exception or presentation payload

#### Scenario: Protocol error cannot disclose presentation state
- **WHEN** synchronization is rejected for an unsupported version or unavailable presentation prerequisite
- **THEN** `ui_protocol_error` identifies the server protocol version, stable code, safe message, and reload requirement without an epoch, revision, panel, actor, or request payload

#### Scenario: Conditional correlation field is exact
- **WHEN** a non-error result or non-internal protocol error includes `correlation_id`, or an internal error omits it
- **THEN** exact envelope validation rejects the message

### Requirement: Every panel payload has an exact availability discriminator
Each registered panel schema SHALL define an available form and the common unavailable form. The unavailable form SHALL contain exactly `schema_version`, `available: false`, and `reason`; reason SHALL contain bounded `code` and safe Traditional Chinese `message`, plus a bounded `correlation_id` only for an internal presenter failure. Available payloads SHALL contain `available: true` and only fields defined by their panel schema.

#### Scenario: Missing canonical data uses a safe unavailable value
- **WHEN** a presenter cannot read required canonical data without mutation
- **THEN** its panel uses the common unavailable form with a stable non-internal reason and no correlation ID

#### Scenario: Presenter exception uses correlated unavailable value
- **WHEN** a presenter raises an unexpected exception
- **THEN** its unavailable reason uses a generic message and bounded correlation ID matching the server log without exposing exception details

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
The presentation registry SHALL reject duplicate panel names and SHALL expose only registered stable panel names to the coordinator. Each presenter SHALL receive session-derived read context, SHALL return JSON-safe panel data without invoking mutation APIs, and SHALL execute independently so one presenter failure cannot suppress other panels or narrative output.

#### Scenario: Duplicate presenter registration fails
- **WHEN** two presenters attempt to register the same stable panel name
- **THEN** registry construction fails rather than selecting one by import order

#### Scenario: One presenter exception is isolated
- **WHEN** one registered presenter raises while a full snapshot is built
- **THEN** the server logs its panel name and correlation ID, emits the common schema-valid unavailable value through that panel's registered schema metadata, and continues building every other panel

#### Scenario: Presentation does not mutate canonical state
- **WHEN** a full snapshot and a panel update are built for an actor
- **THEN** the actor's traits, buffs, sexual state, combat record, location, wallet, quests, and world-clock tick remain unchanged

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
