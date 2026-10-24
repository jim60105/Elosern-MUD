# Spec Delta

## MODIFIED Requirements

### Requirement: sleep computes its own duration from gauge regen, capped at a configured maximum
Voluntary sleep SHALL select only the named body (default acting body), unless explicit party sleep is chosen. Default/until-recovered mode SHALL target full HP/MP/SP and mental reserve; explicit duration SHALL retain its accepted deadline despite reserve saturation. Existing skip bounds and safety SHALL apply. Entry SHALL commit at zero elapsed time before handoff or continuation, and entry alone SHALL claim no completed sleep.

#### Scenario: Full gauges with low reserve
- **WHEN** a safe actor has full HP/MP/SP and 180000 reserve units and explicitly continues recovery sleep with no earlier boundary
- **THEN** its recovery interval is 15000 seconds, not zero

#### Scenario: Sleep duration matches the slowest-regenerating gauge, when under the cap
- **WHEN** a safe actor needs 1200, 600 and 900 gauge seconds and at most 1200 reserve recovery seconds
- **THEN** uninterrupted recovery sleep targets 1200 seconds

#### Scenario: Sleep duration is capped at MAX_SLEEP_SECONDS
- **WHEN** full recovery would exceed the configured maximum
- **THEN** the accepted bounded recovery segment uses that maximum and reports its partial target truthfully; it never falsely claims full recovery

#### Scenario: No elapsed entry
- **WHEN** a possessed companion enters voluntary sleep and an awake owner is available
- **THEN** only companion posture and its accepted receipt commit; return-to-owner is offered before recovery, and choice/cancel advances zero

#### Scenario: An actor already at full hp/mp/sp sleeps for zero seconds
- **WHEN** recovery-mode sleep is requested for a safe body full in every gauge and reserve
- **THEN** no elapsed recovery is invented and the already-met target reconciles awake without claiming completed elapsed sleep

#### Scenario: sleep is blocked by the safety gate
- **WHEN** existing skip safety rejects the request
- **THEN** neither voluntary entry nor elapsed recovery commits

#### Scenario: Exact explicit duration
- **WHEN** a safe full-reserve body accepts `sleep 2h` and uninterrupted continuation begins
- **THEN** its planned wake deadline is entry tick plus 7200, and reserve saturation does not shorten it

## ADDED Requirements

### Requirement: Accepted sleep identity survives control changes
Each body SHALL retain one accepted sleep identity with its declared mode, target and committed progress until wake or explicit interruption. Continuation SHALL use that identity without replacing its target or replaying elapsed time. Reload, reconnect and control handoff SHALL preserve it without wall-clock advancement.

#### Scenario: Continue after handoff
- **WHEN** owner sleep has partially progressed through companion actions, then `sleep continue` resumes it
- **THEN** only the remaining accepted interval settles and the original deadline/target remains

#### Scenario: Retry and reload
- **WHEN** the same accepted continuation is delivered twice with reload between deliveries
- **THEN** its elapsed interval, wake and notifications commit at most once

### Requirement: Explicit party sleep selects present effective bodies atomically
An explicit party-sleep operation SHALL select all present living physiological effective members plus the owner, validate the entire set, and commit new voluntary entries atomically. Existing sleepers SHALL retain their accepted plans and forced targets. Remote members SHALL remain unchanged. SKIP, co-location and browser labels alone SHALL select nobody for sleep.

#### Scenario: Mixed party entry
- **WHEN** explicit party sleep selects an awake owner, an awake companion and an existing forced sleeper in the same room
- **THEN** the first two enter voluntary sleep with independent plans, the forced sleeper retains its target, and no elapsed time or possession transfer occurs during selection

#### Scenario: Member failure
- **WHEN** one selected awake member fails sleep preflight or a later posture/receipt write raises
- **THEN** no new entry survives on any body and persisted/cache state and tick equal their pre-request values

### Requirement: Sleep transports expose declared duration and recovery modes
Text SHALL accept `sleep [<duration>|until-recovered]`, `sleep all [<duration>|until-recovered]` and `sleep continue`, with existing localized alias and bounded duration parsing. Browser requests SHALL select the same rules modes. Malformed or ambiguous input SHALL reject before writes. Both command documents SHALL describe syntax and sleeping-view availability.

#### Scenario: Transport parity
- **WHEN** text `sleep all 2h` and a browser all-party duration request are separately issued against equivalent states
- **THEN** both create identical per-body deadlines and zero-time entries

#### Scenario: No implicit replacement
- **WHEN** `sleep 1h` is issued for a body with an active accepted plan
- **THEN** it rejects target replacement and offers continuation of that plan without resetting the deadline
