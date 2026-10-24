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
