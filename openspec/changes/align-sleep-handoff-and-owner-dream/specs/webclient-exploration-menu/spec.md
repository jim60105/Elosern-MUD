# Spec Delta

## MODIFIED Requirements

### Requirement: The waiting surface offers exactly three operations
The place-card wait surface SHALL retain dawn wait, sleep and custom-duration wait. Sleep SHALL offer recovery or explicit-duration mode using existing bounded input conventions, dispatch once, then show server-accepted contextual handoff and owner-only optional dream decisions before recovery. No client-side dream-before-sleep question or dream/initial-sleep combined dispatch SHALL remain. In-flight/revision locks SHALL apply throughout.

#### Scenario: The waiting frame renders the three operations
- **WHEN** the player opens the wait card
- **THEN** dawn wait, sleep and custom-duration wait remain with back navigation, no separate dream row and existing active-row treatment

#### Scenario: The hours form dispatches whole seconds exactly once
- **WHEN** the player confirms 1.5 hours of ordinary waiting
- **THEN** exactly one `explore.wait` submits `seconds: 5400`, the form closes and no resulting time is fabricated before the snapshot

#### Scenario: An out-of-bounds hours value errors without dispatching
- **WHEN** the custom-duration value is empty or outside existing bounds
- **THEN** localized validation shows, no request dispatches and correction remains possible

#### Scenario: Locked controls cannot start a skip
- **WHEN** an action is in flight or its presentation revision is pending
- **THEN** keyboard and pointer cannot submit another wait/sleep/selection action

#### Scenario: The frame shows three cards plus a back row with focused treatment
- **WHEN** the wait card renders
- **THEN** the existing three operation rows and back row retain focus and active-descendant conventions

#### Scenario: The custom hours form bounds, converts, and dispatches once
- **WHEN** the existing custom wait form is submitted
- **THEN** fractional hours convert once to whole seconds between one second and the existing twelve-hour WebClient bound

#### Scenario: The form shows no resulting world time and reports bounds in Chinese
- **WHEN** duration input is edited or rejected
- **THEN** the client derives no resulting clock time and displays Traditional Chinese validation without dispatch on rejection

#### Scenario: The surrounding skip vocabulary is unchanged
- **WHEN** the sleep correction is applied
- **THEN** existing server skip maximum and four daypart payload vocabulary remain unchanged

#### Scenario: Sleep duration and accepted ordering
- **WHEN** browser sleep duration/recovery is confirmed
- **THEN** one authoritative entry request is sent, acceptance opens contextual selection automatically, and dream eligibility comes from the resulting owner/control view

#### Scenario: No premature wait-card teardown
- **WHEN** sleep entry, handoff or dream response awaits its authoritative revision
- **THEN** presentation retains enough operation identity to process the resulting selection/recovery surface and never drops the request through an early narrative-only success

### Requirement: explore.wait obeys the shared skip safety and clock API
`explore.wait` SHALL retain daypart/duration wait and `sleep: true` with `sleep_scope: self|party`, `sleep_mode: recovery|duration` (default self/recovery), adding bounded positive integer `seconds` only for duration sleep. Contradictory/extra fields SHALL reject. Shared rules/current safety SHALL govern entry and elapsed receipts. Owner sleep with no possession SHALL offer optional dreams before recovery via a separate receipt-bound answer, without positive elapsed; entry SHALL publish contextual handoff.

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
- **THEN** they respectively select self recovery, party recovery and self duration with deadline entry tick plus 7200; sleep scope defaults self and mode defaults recovery

#### Scenario: Contradictory fields reject
- **WHEN** a payload combines daypart with sleep/seconds, puts seconds on recovery sleep, omits seconds for duration sleep, carries sleep scope/mode on ordinary wait, uses `sleep: false`, unknown scope/mode, boolean seconds or an extra key
- **THEN** it rejects as malformed with no operation or state write

#### Scenario: Accepted zero-time owner sleep
- **WHEN** the owner accepts positive-target sleep at zero elapsed time with no companion possession, even while a companion is awake
- **THEN** the authoritative view offers owner dream entry before recovery; a separate stale/wrong-owner/possessed answer rejects without a dream or interval write

#### Scenario: Combined sleep and dream is removed
- **WHEN** an initial sleep payload includes a dream flag
- **THEN** it rejects as malformed; the accepted-view answer operation is the sole dream entry surface
