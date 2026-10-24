## REMOVED Requirements

### Requirement: The waiting surface offers exactly three operations
**Reason**: The three operations are no longer three rows plus a back row on one card; the place card's 休息 now opens a first choice between 等待 and 睡眠 and then that mode's form, so the row and back-row scenarios no longer hold.
**Migration**: Replaced by "The waiting surface offers three operations through two layers", which keeps every other scenario's contract. Tests annotated with this requirement are re-mounted to the replacement identifier the traceability tool generates after sync.

## ADDED Requirements

### Requirement: The waiting surface offers three operations through two layers
The place-card rest entry SHALL retain dawn wait, sleep and custom-duration wait, offered first as a choice between 等待 and 睡眠 and then as that mode's form. Sleep SHALL offer recovery or explicit-duration mode, dispatch once, then show the server-accepted contextual handoff and owner-only optional dream decisions before recovery. No client-side dream-before-sleep question or combined dream/initial-sleep dispatch SHALL remain, and in-flight/revision locks SHALL apply throughout.

#### Scenario: The rest entry renders the three operations in two layers
- **WHEN** the player opens the rest entry
- **THEN** its first layer offers 等待 and 睡眠, 等待 leads to dawn wait and custom-duration wait, 睡眠 leads to recovery or explicit-duration sleep, every layer has a visible way back or out, and no separate dream option exists

#### Scenario: The hours form dispatches whole seconds exactly once
- **WHEN** the player confirms 1.5 hours of ordinary waiting
- **THEN** exactly one `explore.wait` submits `seconds: 5400`, the form closes and no resulting time is fabricated before the snapshot

#### Scenario: An out-of-bounds hours value errors without dispatching
- **WHEN** the custom-duration value is empty or outside existing bounds
- **THEN** localized validation shows, no request dispatches and correction remains possible

#### Scenario: Locked controls cannot start a skip
- **WHEN** an action is in flight or its presentation revision is pending
- **THEN** keyboard and pointer cannot submit another wait/sleep/selection action

#### Scenario: The tiles and forms keep visible focus treatment
- **WHEN** the rest entry renders either layer
- **THEN** each tile, form control, and corner button shows a visible focus ring, and the focused tile's badge takes the active treatment

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

#### Scenario: No premature rest-entry teardown
- **WHEN** sleep entry, handoff or dream response awaits its authoritative revision
- **THEN** presentation retains enough operation identity to process the resulting selection/recovery surface and never drops the request through an early narrative-only success
