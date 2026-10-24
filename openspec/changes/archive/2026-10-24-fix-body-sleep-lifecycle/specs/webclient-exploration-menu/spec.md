# Spec Delta

## MODIFIED Requirements

### Requirement: explore.wait obeys the shared skip safety and clock API
`explore.wait` SHALL accept daypart wait, duration wait or sleep. Sleep SHALL use `sleep: true`, `sleep_scope: self|party` and `sleep_mode: recovery|duration`; scope/mode SHALL default to self/recovery. Only duration sleep SHALL add bounded positive integer `seconds`. Unknown, contradictory or extra fields SHALL reject before writes. All modes SHALL use shared text rules, current safety and actual receipts; dream behavior SHALL follow its owning capability.

#### Scenario: Wait until dawn advances to the next occurrence
- **WHEN** a safe actor submits `explore.wait` with `daypart: "dawn"`
- **THEN** the clock advances only to the first relevant boundary within the next dawn interval and the summary reports actual elapsed time

#### Scenario: An unsafe skip rejects before any clock advance
- **WHEN** an actor in a room with a living monster submits `explore.wait`
- **THEN** the matching safety reason rejects with unchanged tick and no settlement

#### Scenario: A custom duration is parsed server-side
- **WHEN** a safe actor submits ordinary wait `seconds: 3600` without `sleep`
- **THEN** the shared operation advances at most 3600 seconds to its first boundary; values above the protocol bound reject before advance

#### Scenario: The duration bound is protocol-only
- **WHEN** the browser `seconds` bound is documented
- **THEN** the documented WebClient maximum applies without changing text command bounds

#### Scenario: Skip safety rejects combat and co-located monsters
- **WHEN** the adapter rechecks current canonical skip safety
- **THEN** active combat or a co-located living monster rejects before entry or clock writes

#### Scenario: The shared skip helper keeps command and WebClient computations identical
- **WHEN** the adapter selects daypart wait, ordinary duration wait, recovery sleep or duration sleep
- **THEN** it delegates the declared mode and target to the same rules operations as text; sleeping scope never comes from SKIP alone

#### Scenario: The wait summary is presented and one newer snapshot published
- **WHEN** the shared clock operation returns actual committed events
- **THEN** the adapter publishes escaped actual elapsed summary and one newer full snapshot, without advancing time itself; zero-time entry reports an accepted sleeping view rather than a completed interval

#### Scenario: An unsafe or malformed wait rejects without advancing the clock
- **WHEN** combat/location is unsafe, a daypart is unknown, seconds are invalid or payload fields contradict the declared operation
- **THEN** the adapter rejects with stable code/message and no posture, receipt or time writes

#### Scenario: Sleep payload grammar
- **WHEN** requests separately submit `{sleep: true}`, `{sleep: true, sleep_scope: "party", sleep_mode: "recovery"}` or `{sleep: true, sleep_scope: "self", sleep_mode: "duration", seconds: 7200}`
- **THEN** they respectively select self recovery, party recovery and self duration with deadline entry tick plus 7200; absent scope/mode default self/recovery

#### Scenario: Contradictory fields reject
- **WHEN** a payload combines daypart with sleep/seconds, puts seconds on recovery sleep, omits seconds for duration sleep, carries sleep scope/mode on ordinary wait, uses `sleep: false`, unknown scope/mode, boolean seconds or an extra key
- **THEN** it rejects as malformed with no operation or state write
