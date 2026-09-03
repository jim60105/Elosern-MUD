# webclient-oob-protocol — Delta Spec

## MODIFIED Requirements

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
