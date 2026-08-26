## MODIFIED Requirements

### Requirement: Elosern OOB messages use exact versioned envelopes
The WebClient foundation SHALL carry each Elosern OOB message as exactly one JSON object in the first positional argument of Evennia's existing command/args/kwargs transport triple. Protocol version 1 SHALL define client messages `ui_sync` and `ui_action` and server messages `ui_snapshot`, `ui_update`, `ui_action_result`, and `ui_protocol_error`. Every envelope SHALL reject unknown fields, invalid scalar types, non-finite numbers, canonical UTF-8 JSON over 65,536 bytes, nesting deeper than 8, an object with more than 64 fields, a list with more than 128 items, a generic string over 2,048 Unicode code points, or an integer outside `-9,007,199,254,740,991..9,007,199,254,740,991` (the full JavaScript-safe range); field-specific limits SHALL be equal or smaller.

#### Scenario: Negative safe integers pass the global bound
- **WHEN** an OOB envelope carries a negative integer within the JavaScript-safe range, such as a signed combat modifier value (`defense: -15` or `accuracy: -10`)
- **THEN** the global JSON-safety check accepts it and the value reaches the client unchanged

#### Scenario: Integers outside the safe range are rejected
- **WHEN** an OOB envelope carries an integer below `-9,007,199,254,740,991` or above `9,007,199,254,740,991`
- **THEN** the envelope is rejected before dispatch or adoption
