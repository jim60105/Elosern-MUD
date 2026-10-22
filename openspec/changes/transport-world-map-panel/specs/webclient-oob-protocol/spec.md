# Spec Delta

## MODIFIED Requirements

### Requirement: Elosern OOB messages use exact versioned envelopes
The WebClient foundation SHALL carry each Elosern OOB message as exactly one JSON object in the first positional argument of Evennia's existing command/args/kwargs transport triple. Protocol version 1 SHALL define client messages ui_sync and ui_action and server messages ui_snapshot, ui_update, ui_action_result and ui_protocol_error. Every envelope SHALL reject unknown fields, invalid scalar types and non-finite numbers. The measured, bounded world_map panel SHALL have a panel-specific size/collection exception sufficient for real continental data; unrelated panels including local_map SHALL retain existing bounds. Transport SHALL deliver one complete replacement or bounded parts reassembled atomically under the same epoch/revision, never partial visible state.

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
- **WHEN** a non-exempt message exceeds the existing 65536-byte or other generic structural limits, or a world-map message exceeds its separately measured declared bounds
- **THEN** both validators reject it before dispatch/adoption, retaining all non-size scalar safety rules and panel-local bounds

#### Scenario: Field-specific limits stay within global bounds
- **WHEN** a registered field defines a field-specific limit
- **THEN** it is no larger than its applicable enclosing bound, with the sole world_map size/collection exception explicitly scoped and unrelated panel budgets unchanged

## ADDED Requirements

### Requirement: Continental map transport is measured end to end
The real authored continental map payload SHALL be measured in canonical UTF-8 bytes, including common layers, all district outlines, maximum lit details and bounded trail/quest data. A documented bound SHALL be enforced on both server and browser. The actual Evennia WebSocket transport SHALL carry and adopt the representative payload above 64 KB; if its frame path cannot, bounded parts SHALL be used without losing the existing epoch/revision safety contract.

#### Scenario: Real continental data exceeds the local map envelope
- **WHEN** generated production geography and the final landmark roster are serialized into representative and supported worst-case world-map payloads
- **THEN** their measured sizes and the selected bound are recorded, a payload at that supported size travels through the real socket and browser validator/store intact, and local_map remains limited to 65536 bytes

#### Scenario: Multipart delivery never exposes incomplete state
- **WHEN** measured frame limitations require parts and a part is missing, duplicated, malformed, superseded or from an old epoch
- **THEN** the browser never adopts an incomplete/mixed map, retains or safely invalidates its prior complete map, bounds assembly memory and discards old-epoch data
