# Spec Delta

## MODIFIED Requirements

### Requirement: Full snapshots and updates have registered replacement semantics
A version-1 `ui_snapshot` SHALL contain exactly `protocol_version`, `presentation_epoch`, `revision`, `mode`, `panels`, `layout_version`, and `server_time`. A `ui_update` SHALL contain the same exact top-level field set, with a nonempty registered subset in `panels`. Every included eager update panel SHALL completely replace its prior value. On-demand map bodies SHALL be omitted from eager snapshots, kept separately within an epoch, and cleared on a new epoch. No JSON Patch is used.

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
- **THEN** it includes the active mode, current server time, and layout version together with its epoch, new revision, and nonempty panel subset

#### Scenario: A dialogue-mode update always carries the dialogue panel
- **WHEN** an affected-panel update is published while the viewer's recomputed mode resolves to `dialogue` and its named subset omits the `dialogue` panel
- **THEN** the emitted update still carries a freshly rendered `dialogue` panel alongside the named subset, and the client never commits mode `dialogue` over a stale dialogue panel

#### Scenario: Top-level field value bounds are exact
- **WHEN** a snapshot or update envelope is validated
- **THEN** `protocol_version` SHALL be integer 1; `presentation_epoch` SHALL be exactly 22 URL-safe ASCII characters generated from 128 random bits; revisions SHALL be positive safe integers excluding booleans; `mode` — recomputed at publication time so the committed mode never diverges from the committed dialogue panel — SHALL be `creation`, `exploration`, `combat`, or `dialogue`; `layout_version` SHALL be in `1..65,535`; panel names SHALL be 1..64 lowercase identifier characters; and panel count SHALL not exceed 32

#### Scenario: Server time fields are exact and bounded
- **WHEN** a snapshot or update carries `server_time`
- **THEN** it SHALL contain exactly `year`, `season_index`, `season_label`, `day_in_season`, `hour`, `minute`, and `second`, bounded respectively to the safe non-negative integer range, `0..3`, 1..32 Unicode code points, `1..90`, `0..23`, `0..59`, and `0..59`

### Requirement: Elosern OOB messages use exact versioned envelopes
The WebClient foundation SHALL carry each Elosern OOB message as exactly one JSON object in the first positional argument of Evennia's command/args/kwargs triple. Version 1 SHALL define client messages `ui_sync` and `ui_action` and server messages `ui_snapshot`, `ui_update`, `ui_action_result`, and `ui_protocol_error`. Every envelope SHALL reject unknown fields, invalid scalar types and non-finite numbers. Map part frames keep per-frame bounds; reassembled area_map uses finite schema bounds.

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

#### Scenario: Global structural bounds reject oversized envelopes
- **WHEN** a message is canonical UTF-8 JSON over 65,536 bytes, nests deeper than 8, holds an object with more than 64 fields, a list with more than 128 items, a generic string over 2,048 Unicode code points, or an integer outside `-9,007,199,254,740,991..9,007,199,254,740,991` (the full JavaScript-safe range)
- **THEN** every wire-frame validator rejects it before dispatch/adoption; reassembled logical area_map data instead uses its finite measured panel bounds, while retaining exact-field/scalar safety

#### Scenario: Field-specific limits stay within global bounds
- **WHEN** a registered field defines a field-specific limit
- **THEN** that limit SHALL be equal to or smaller than the applicable enclosing bound; reassembled logical area_map uses its declared schema-specific bounds and all unrelated payloads retain generic bounds
