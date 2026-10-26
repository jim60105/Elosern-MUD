## Purpose

Versioned WebSocket OOB envelopes, epoch/revision ordering, authenticated synchronization, presenter isolation, and degraded text-mode recovery.

## Requirements

### Requirement: Elosern OOB messages use exact versioned envelopes
Each Elosern OOB message SHALL be one JSON object in Evennia's command/args/kwargs first positional argument. Version 1 SHALL define ui_sync, ui_action, ui_snapshot, ui_update, ui_action_result, ui_protocol_error and ui_publication_part. Envelopes SHALL reject unknown fields, invalid scalars, non-finite numbers. Scoped allowances bind world_map and v3 dialogue; other panels keep theirs. General delivery is intact within its frame allowance or atomically reassembled in a distinct logical ceiling.

#### Scenario: A version-1 message uses the Evennia transport
- **WHEN** the server emits a valid version-1 full snapshot
- **THEN** the transport command is ui_snapshot, its first positional argument is the complete envelope object, and no protocol field is encoded as a transport keyword argument

#### Scenario: An exact envelope rejects additional input
- **WHEN** a client sends an otherwise valid ui_sync or ui_action object with an unknown field, a boolean in an integer field, or a value over its applicable bound
- **THEN** the server rejects the message before synchronization or adapter dispatch and returns a safe protocol error without a traceback or raw payload

#### Scenario: Negative safe integers pass the global bound
- **WHEN** an OOB envelope carries a negative integer within the JavaScript-safe range
- **THEN** the global JSON-safety check accepts it and the value reaches the client unchanged

#### Scenario: Integers outside the safe range are rejected
- **WHEN** an OOB envelope carries an integer outside -9007199254740991..9007199254740991
- **THEN** the envelope is rejected before dispatch or adoption

#### Scenario: Global structural bounds reject oversized envelopes
- **WHEN** a non-exempt message exceeds the existing 65536-byte or other generic structural limits, or a world-map message exceeds its separately measured declared bounds, or a dialogue publication exceeds its 98304-byte whole-envelope, 24576-byte dialogue or 65536-byte dialogue-removed envelope bound
- **THEN** both frame validators reject the oversized intact frame before dispatch/adoption; a general publication may instead use individually bounded parts, whose reassembled document keeps logical/schema/panel bounds without reapplying the generic frame ceiling

#### Scenario: Field-specific limits stay within global bounds
- **WHEN** a registered field defines a field-specific limit
- **THEN** it is no larger than its applicable enclosing bound, with specialized maps and v3 dialogue retaining their scoped panel limits, general reassembly using its finite logical aggregate limit, and unrelated panel budgets unchanged

#### Scenario: Multilingual chain fits the real outer transport
- **WHEN** a maximum valid CJK primary scene and public successor are published then replayed after reconnect
- **THEN** both production validators and protocol-store admission accept the same bounded complete frame, while any over-budget body rejects before effect/session publication

### Requirement: Full snapshots and updates have registered replacement semantics
A version-1 ui_snapshot SHALL retain its seven exact metadata/panel fields. A ui_update SHALL add exact base_revision and removed_panels fields, permitting empty panels. Included panels SHALL replace complete values; removed eager names SHALL be explicit and disjoint. Snapshots SHALL replace all eager membership while retaining same-epoch on-demand maps. No JSON Patch is used.

#### Scenario: Full synchronization replaces the complete store
- **WHEN** the browser accepts a valid `ui_snapshot`
- **THEN** it atomically replaces every eager panel and the prior mode, layout version and server-time display, preserves separate on-demand maps in the same epoch, and clears all maps on a new epoch

#### Scenario: A panel update is a full replacement
- **WHEN** the browser accepts a newer `ui_update` containing the `status` panel
- **THEN** the new status object completely replaces the previous status object without retaining omitted nested fields

#### Scenario: Unknown panel names are rejected
- **WHEN** a snapshot or update contains a panel name absent from the registered panel allowlist
- **THEN** the client rejects that presentation message and does not render or merge the unknown panel

#### Scenario: Update metadata is complete
- **WHEN** the server emits a valid `ui_update`
- **THEN** it includes the active mode, current server time, and layout version together with its epoch, new revision, and a possibly empty panel subset plus exact base_revision and removed_panels

#### Scenario: A dialogue-mode update always carries the dialogue panel
- **WHEN** an affected-panel update is published while the viewer's recomputed mode resolves to `dialogue` and its named subset omits the `dialogue` panel
- **THEN** the staged committed presentation always carries the correct dialogue panel: the server freshly renders it as a candidate, transmits it when changed, and the client validates mode/dialogue consistency against the staged state even when equal dialogue is omitted from the wire

#### Scenario: Top-level field value bounds are exact
- **WHEN** a snapshot or update envelope is validated
- **THEN** `protocol_version` SHALL be integer 1; `presentation_epoch` SHALL be exactly 22 URL-safe ASCII characters generated from 128 random bits; revisions SHALL be positive safe integers excluding booleans; `mode` — recomputed at publication time so the committed mode never diverges from the committed dialogue panel — SHALL be `creation`, `exploration`, `combat`, or `dialogue`; `layout_version` SHALL be in `1..65,535`; panel names SHALL be 1..64 lowercase identifier characters; and panel count SHALL not exceed 32

#### Scenario: Server time fields are exact and bounded
- **WHEN** a snapshot or update carries `server_time`
- **THEN** it SHALL contain exactly `year`, `season_index`, `season_label`, `day_in_season`, `hour`, `minute`, and `second`, bounded respectively to the safe non-negative integer range, `0..3`, 1..32 Unicode code points, `1..90`, `0..23`, `0..59`, and `0..59`

### Requirement: Result and protocol-error envelopes are exact and non-overlapping
A version-1 `ui_action_result` SHALL contain exactly `protocol_version`, `presentation_epoch`, `request_id`, `outcome`, `code`, `message`, and `presentation_revision`, plus `correlation_id` only when outcome is `error` and the optional `data` slot only on `success` when the admitted adapter explicitly returns one. Outcome SHALL be `success`, `rejected`, `stale`, or `error`; busy SHALL use outcome `rejected` and code `busy`. The `data` slot carries no state-identity key or live object reference.

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

#### Scenario: Data slots stay within the fixed budget
- **WHEN** a success result carries a `data` object
- **THEN** it SHALL be a JSON object of at most 8 fields, each field name 1..64 lowercase identifier characters and each value a JSON-safe scalar, object, or list within the global envelope bounds measured from the envelope root, and the canonical JSON size of the whole `data` object SHALL fit a fixed budget that reserves room for the seven standard envelope fields under the global canonical byte ceiling so an emitted envelope can never exceed it

#### Scenario: Data rejects live objects structurally
- **WHEN** a result's `data` contains a live object reference or an unsupported JSON value type
- **THEN** JSON-safety SHALL reject it structurally, so no result carries a live object reference

#### Scenario: Protocol error fields are exactly bounded
- **WHEN** a version-1 `ui_protocol_error` is validated
- **THEN** it SHALL contain exactly `protocol_version`, `code`, `message`, and boolean `reload_required`, plus `correlation_id` only when code is `internal_error`, and SHALL contain no actor, panel, epoch, revision, request payload, exception, or local path

#### Scenario: Shared identifier and text formats are exact
- **WHEN** result or protocol-error fields are validated
- **THEN** request IDs SHALL be 1..64 characters from ASCII letters, digits, colon, underscore, and hyphen; stable codes SHALL be 1..64 lowercase dotted or underscored identifier characters; messages SHALL be 1..512 Unicode code points; and correlation IDs SHALL be exactly 32 lowercase hexadecimal characters

### Requirement: Every panel payload has an exact availability discriminator
Each registered panel schema SHALL define an available form and the common unavailable form. The unavailable form SHALL contain exactly `schema_version`, `available: false`, and `reason`; reason SHALL contain bounded `code` and safe Traditional Chinese `message`, plus a bounded `correlation_id` only for an internal presenter failure. Available payloads SHALL contain `available: true` and only fields defined by their panel schema.

#### Scenario: Missing canonical data uses a safe unavailable value
- **WHEN** a presenter cannot read required canonical data without mutation
- **THEN** its panel uses the common unavailable form with a stable non-internal reason and no correlation ID

#### Scenario: Presenter exception uses correlated unavailable value
- **WHEN** a presenter raises an unexpected exception
- **THEN** its unavailable reason uses a generic message and bounded correlation ID matching the server log without exposing exception details

#### Scenario: Unavailable character payload carries the registered version
- **WHEN** the character presenter reports the common unavailable form for a character panel registered at schema version 3
- **THEN** the unavailable payload carries `schema_version: 3` and the client accepts it, and a payload carrying any other version (`schema_version: 2`) is rejected without replacing or merging the stored panel

#### Scenario: Unavailable schema versions match the registered gate
- **WHEN** an unavailable panel payload is validated against the client's registered-version gate
- **THEN** the unavailable form's `schema_version` SHALL equal the panel's registered schema version — the same version the panel's available form carries — so the gate accepts it

### Requirement: Presentation ordering is scoped by transport and puppet epoch
The server SHALL generate a bounded cryptographically unpredictable presentation epoch for each live WebSocket transport and active-puppet sequence. Reconnection and puppet change SHALL create a new epoch and reset the ephemeral revision sequence. On each browser `connection_open`, the client SHALL begin a new local transport generation, retire the prior active epoch in bounded memory, clear presentation state, and enter `awaiting_initial_snapshot`.

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

#### Scenario: Only the first valid snapshot establishes the epoch
- **WHEN** the current transport generation receives snapshots, updates, or results for a non-retired epoch
- **THEN** only the first valid full snapshot delivered for that generation establishes the active epoch; updates and results SHALL NOT establish it

#### Scenario: Different-epoch presentations are discarded once active
- **WHEN** an epoch is active and another presentation for a different epoch arrives on that same transport
- **THEN** every different-epoch presentation on that transport SHALL be discarded

#### Scenario: Presentation ordering state is never persisted
- **WHEN** epochs, generations, revisions, or retired-epoch memory exist during play
- **THEN** they SHALL NOT be persisted to Accounts, characters, Scripts, localStorage, or any canonical game record

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

The presentation registry SHALL reject duplicate panel names and SHALL expose only registered stable panel names to the coordinator; adding a registered panel SHALL remain a registry-registration act and SHALL NOT change any envelope schema. Each presenter SHALL receive session-derived read context, SHALL return JSON-safe panel data without invoking mutation APIs, and SHALL execute independently so one presenter failure cannot suppress other panels or narrative output.

#### Scenario: Duplicate presenter registration fails

- **WHEN** a second `PresenterSpec` is registered under an existing panel name
- **THEN** registration raises rather than replacing the first spec

#### Scenario: The gallery panel joins the registered set additively

- **WHEN** the production registry is built after this change
- **THEN** `panel_names` includes `gallery` together with every previously registered panel name, and the snapshot/update/result/error envelope schemas are unchanged

#### Scenario: The combat round record reaches only the completing publication

- **WHEN** an admitted combat action or field cast settles an ordinary combat round and the dispatcher publishes its completion, and later a reconnect snapshot and a text-command refresh are published
- **THEN** only the completion publication's context carries the round record, the later publications' contexts carry none, and the sent `ui_action_result` contains no round-record field

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

#### Scenario: Skill use selection is isolated presentation context

- **WHEN** a selected skill is rendered and the session later adopts another puppet/epoch
- **THEN** `skill_use` is registered at version 2, other registered versions remain unchanged, no gameplay state was mutated by rendering, and the new epoch receives no old selection

#### Scenario: Registered production panels join additively
- **WHEN** the production registry is built
- **THEN** the registered production set SHALL include the `gallery`, `combat_beats` and `skill_use` panels alongside the existing registered panels

#### Scenario: The combat round record is ephemeral and immutable
- **WHEN** the dispatcher's completion publication for an admitted action that settled an ordinary combat round builds its read context
- **THEN** it SHALL add the frozen record of that round to the context, every other publication path SHALL build its context without a round record, and the record SHALL be immutable, SHALL NOT be persisted, and SHALL NOT be serialized into any result envelope

#### Scenario: Account-subject presenters are derived and bounded
- **WHEN** a presenter's subject is the account owning the rendered puppet, rather than the puppet itself
- **THEN** it SHALL derive that account from the rendered actor's own ownership link, SHALL be held to the identical read-only, isolation, and availability-discriminator contract as every puppet-subject presenter, SHALL NOT widen the read context to the transport session, and SHALL NOT read any account the rendered actor does not belong to

#### Scenario: Skill use recomputes availability without mutation
- **WHEN** the `skill_use` presenter renders a selection
- **THEN** it SHALL receive only a copied caster/skill/scale presentation selection belonging to the current transport-and-puppet epoch, never the transport session itself, SHALL recompute current canonical availability without invoking a cast, creating a combat record or clock, or changing persistent state, and an absent or retired selection SHALL produce its common unavailable form
- **AND** this registration SHALL NOT change existing panel schema versions or the envelope protocol version

#### Scenario: Panel versions derive from module constants
- **WHEN** the registry registers a panel's schema version
- **THEN** it SHALL derive the registered version from the panel schema's single server-side constant in its presenter module, and the client's panel allowlist and per-panel schema-version re-checks SHALL mirror the same value under a dual-direction parity contract so the two never diverge

### Requirement: WebClient text commands refresh presentation after completion
The project `text` input function SHALL preserve ordinary command semantics and observe both callback and errback settlement without replacing the original Deferred value or Failure. Only after a WebClient command settles SHALL it compare all eager candidates from then-current canonical state, using a fresh complete snapshot when a semantic checkpoint or recovery requires it, and it SHALL emit no graphical state for Telnet commands.

#### Scenario: A completed WebClient command refreshes state
- **WHEN** a puppeted WebClient submits an ordinary synchronous text command that changes canonical state
- **THEN** normal command output is delivered and changed content/metadata is published after command completion using a delta, a qualifying checkpoint uses one fresh full snapshot, and wholly unchanged presentation consumes no revision

#### Scenario: A Telnet command remains text-only
- **WHEN** a Telnet player executes the same command
- **THEN** normal output and state change occur without an Elosern graphical snapshot

#### Scenario: Idle input remains idle handling
- **WHEN** the WebClient sends Evennia's configured idle command
- **THEN** the session idle counter is updated without command execution or a fabricated gameplay refresh

#### Scenario: Command errback preserves failure semantics
- **WHEN** a WebClient command handler Deferred settles through its errback path
- **THEN** the wrapper preserves the original Failure and ordinary error output while attempting at most one safe post-settlement refresh

#### Scenario: Presentation failure never consumes a command failure
- **WHEN** the post-settlement publication attempt fails
- **THEN** the presentation failure SHALL be logged separately and SHALL NOT consume a command failure

#### Scenario: Ordinary text behaviour is untouched
- **WHEN** a puppeted WebClient submits any ordinary text command
- **THEN** idle handling, nickname replacement, command output, session counters, and text access SHALL keep working as they do without the publication wrapper

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

### Requirement: Continental map transport is measured end to end
The real authored continental map payload SHALL be measured in canonical UTF-8 bytes, including common layers, all district outlines, maximum lit details and bounded trail/quest data. A documented bound SHALL be enforced on both server and browser. The actual Evennia WebSocket transport SHALL carry and adopt the representative payload above 64 KB; if its frame path cannot, bounded parts SHALL be used without losing the existing epoch/revision safety contract.

#### Scenario: Real continental data exceeds the local map envelope
- **WHEN** generated production geography and the final landmark roster are serialized into representative and supported worst-case world-map payloads
- **THEN** their measured sizes and the selected bound are recorded, a payload at that supported size travels through the real socket and browser validator/store intact, and local_map remains limited to 65536 bytes

#### Scenario: Multipart delivery never exposes incomplete state
- **WHEN** measured frame limitations require parts and a part is missing, duplicated, malformed, superseded or from an old epoch
- **THEN** the browser never adopts an incomplete/mixed map, retains or safely invalidates its prior complete map, bounds assembly memory and discards old-epoch data

### Requirement: Deltas require the exact committed baseline
For the live transport and epoch, a delta SHALL require base_revision equal to the committed revision and a newer target. All replacements, removals and metadata SHALL validate before one atomic commit and notification. Deltas SHALL NOT establish initial state.

#### Scenario: Missing predecessor preserves committed state
- **WHEN** the browser at revision7 receives a valid delta with base6 and target8
- **THEN** it rejects base_mismatch, preserves revision7 panels/mode/time and locks mutations for complete recovery

#### Scenario: Initial delta cannot establish epoch
- **WHEN** an awaiting browser receives a delta with no complete snapshot baseline
- **THEN** it adopts nothing and cannot establish an epoch

#### Scenario: Newer target can skip unused integers
- **WHEN** the committed revision is7 and a valid delta has base7 and target10
- **THEN** the browser commits10 once; admission does not invent a predecessor9

#### Scenario: Staged failure rolls back every field
- **WHEN** one replacement or mode/dialogue relation fails validation alongside valid replacements and metadata
- **THEN** no staged panel, removal, mode, time or revision becomes observable

#### Scenario: On-demand map revision follows exact base
- **WHEN** a specialized map transfer repeats base7 and target8 across its existing map-body parts
- **THEN** no partial map changes revision7 and only complete validated map adoption commits8

### Requirement: Removal unavailable and metadata-only updates remain distinct
A delta SHALL allow empty replacements, explicit duplicate-free registered eager removals and complete metadata. Removed names SHALL be disjoint from replacements and exclude on-demand maps. Unavailable values SHALL replace panels rather than delete them.

#### Scenario: Three distinct eager operations
- **WHEN** a delta replaces status with unavailable, removes a registered eager panel and omits another
- **THEN** status remains present as unavailable, the removed key is absent and the omitted panel is unchanged

#### Scenario: Invalid removals reject atomically
- **WHEN** removals contain an unknown name, map name, duplicate or replacement overlap
- **THEN** both validators reject the entire delta

#### Scenario: Metadata-only adoption
- **WHEN** a delta has empty panels/removals with changed server time or mode consistent with staged panels
- **THEN** the browser atomically commits metadata and revision without deleting existing panels
