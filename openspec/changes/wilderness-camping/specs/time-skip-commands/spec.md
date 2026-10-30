## MODIFIED Requirements

### Requirement: sleep computes its own duration from gauge regen, capped at a configured maximum
Voluntary sleep SHALL select the acting body unless party sleep is explicit, commit entry at zero time, and retain safety/bounds. Recovery SHALL target full gauges/reserve; duration SHALL retain its deadline. Until-dawn SHALL retain a deadline at the next configured dawn, capped by maximum sleep, regardless of early full recovery. Entry SHALL claim no completed sleep.

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

#### Scenario: Strict next dawn and cap
- **WHEN** safe until-dawn sleep begins before dawn, exactly at dawn, after dawn or across midnight
- **THEN** the accepted interval is the strictly future configured dawn interval capped by maximum sleep; a full-reserve body still retains that deadline

#### Scenario: Dawn mode remains interruptible
- **WHEN** an interaction or safety interruption precedes an until-dawn deadline
- **THEN** only the safe prefix commits and due events, retained identity and resume behavior match existing sleep continuation

### Requirement: Sleep transports expose declared duration and recovery modes
Text SHALL accept `sleep [all] [<duration>|until-recovered|until-dawn] [dream]`, `sleep continue` and `camp [<duration>|until-recovered|until-dawn] [dream]`, with existing aliases and dawn tokens 睡到天亮 / 天亮. Browser sleep SHALL select the same modes. Malformed input SHALL reject before writes. Camp SHALL use explicit party scope and the shared daypart default. Both command documents SHALL describe syntax and sleeping availability.

#### Scenario: Transport parity
- **WHEN** text `sleep all 2h` and a browser all-party duration request are separately issued against equivalent states
- **THEN** both create identical per-body deadlines and zero-time entries

#### Scenario: No implicit replacement
- **WHEN** `sleep 1h` is issued for a body with an active accepted plan
- **THEN** it rejects target replacement and offers continuation of that plan without resetting the deadline

#### Scenario: Dawn transport and localized parity
- **WHEN** equivalent states receive `sleep all until-dawn`, the same syntax with either localized dawn token, or browser party dawn selection
- **THEN** their per-body accepted deadlines and zero-time entries match

#### Scenario: Camp alias and default
- **WHEN** `camp` is issued at dusk/night or dawn/day, or with a valid explicit mode and optional dream token
- **THEN** it invokes the same whole-party camp operation as the browser, defaults to dawn at dusk/night and recovery otherwise, and keeps explicit mode/dream intent

#### Scenario: Malformed suffix
- **WHEN** mode tokens conflict, dream repeats, or a duration is malformed
- **THEN** input rejects before safety checks, sleep writes or clock advancement

