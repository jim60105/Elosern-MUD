# Spec Delta

## MODIFIED Requirements

### Requirement: Elosern OOB messages use exact versioned envelopes
Each Elosern OOB message SHALL be exactly one JSON object in the first positional argument of Evennia's command/args/kwargs triple. Version 1 SHALL define ui_sync, ui_action, ui_snapshot, ui_update, ui_action_result and ui_protocol_error. Envelopes SHALL reject unknown fields, invalid scalars and non-finite numbers. world_map SHALL retain its own size exception; v3 dialogue publications SHALL use their declared finite scoped allowance; unrelated panels SHALL retain their bounds. Transport SHALL deliver one complete replacement or parts reassembled atomically.

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
- **THEN** both validators reject it before dispatch/adoption, retaining all non-size scalar safety rules and panel-local bounds

#### Scenario: Field-specific limits stay within global bounds
- **WHEN** a registered field defines a field-specific limit
- **THEN** it is no larger than its applicable enclosing bound, with world_map, reassembled area_map and v3 dialogue publications using only their explicitly scoped finite logical bounds, and unrelated panel budgets unchanged

#### Scenario: Multilingual chain fits the real outer transport
- **WHEN** a maximum valid CJK primary scene and public successor are published then replayed after reconnect
- **THEN** both production validators and protocol-store admission accept the same bounded complete frame, while any over-budget body rejects before effect/session publication
