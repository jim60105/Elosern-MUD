# mental-reserve Specification

## Purpose
Own exact persistent mental reserve and sleep posture with deterministic activity effects, fatigue thresholds and pure prediction for rules consumers.

## Requirements

### Requirement: Each body owns exact persistent mental reserve
Each player character and effective companion SHALL own integer reserve in [0, 360000], with 3600 units per percentage point, independent of HP/MP/SP and account state. Writes SHALL reject invalid types, booleans and out-of-range values before mutation.

#### Scenario: Independent reserves
- **WHEN** two members have different reserves and one restores SP
- **THEN** only SP changes; neither reserve is refilled or shared

#### Scenario: Reject corrupt state
- **WHEN** an accepted action encounters malformed reserve or posture
- **THEN** it fails before effects/time writes with a stable error; it never silently refills reserve

### Requirement: Construction establishes full awake physiology
Ordinary deterministic entity construction and authored synchronization SHALL explicitly establish full reserve and awake posture. Repeated synchronization SHALL preserve valid existing fatigue. Reads SHALL create or repair no physiology.

#### Scenario: Construction and reload
- **WHEN** a new ordinary entity is constructed and reloaded
- **THEN** reserve is 360000 and posture awake

#### Scenario: Repeat synchronization
- **WHEN** an authored entity at 120000 units is synchronized again
- **THEN** its valid reserve remains 120000; status reads write nothing

### Requirement: Posture and forced-sleep hysteresis are body scoped
Posture SHALL persist as awake, voluntary sleep or forced sleep, separate from defeat and knockout. Zero at an accepted boundary SHALL latch forced sleep. Natural release SHALL require at least 72000 units and no live combat. Explicit future effects SHALL remain representable without adding one now.

#### Scenario: Latch and wake
- **WHEN** a body reaches zero then recovers to 1, 71999 and 72000 outside combat
- **THEN** it remains forced asleep at the first two positive values and wakes at 72000 into moderate fatigue

#### Scenario: Reload
- **WHEN** a forced sleeper at 71999 is reloaded
- **THEN** posture and eligibility remain asleep; knockout/defeat sets are unchanged

### Requirement: Activity rates are exact net per-second effects
Ordinary awake activity, waiting and study SHALL consume 4 units/second; foot travel 8; awake combat 12; actual sleep SHALL restore 12. Effects SHALL clamp to [0,360000], use each member's declared activity, and never add ordinary awake cost again. Terrain SHALL add no exertion multiplier.

#### Scenario: Calibration
- **WHEN** a full member walks six hours, spends ten further hours awake and sleeps eight hours
- **THEN** reserve successively becomes 187200 (52%), 43200 (12%), and 360000

#### Scenario: Exact partitions
- **WHEN** an unchanged awake activity interval is split into 1 and 2 seconds or settled as 3 seconds
- **THEN** both yield exactly 12 units consumed; equivalent sleep partitions saturate identically at full

#### Scenario: No midnight reset
- **WHEN** continuous full-reserve walking spans midnight for 45000 seconds
- **THEN** reserve reaches zero from its activity cost without a daily quota or refill

### Requirement: Fatigue stages have exact exclusive thresholds
Awake reserve SHALL select normal at 252000..360000, light at 144000..251999, moderate at 72000..143999, severe at 1..71999. Foot-speed scales SHALL respectively be 1, 0.90, 0.75 and 0.50. Latched forced sleep SHALL replace the ordinary stage and forbid travel/actions while permitting targeting.

#### Scenario: Boundary truth
- **WHEN** reserves 252000, 251999, 144000, 143999, 72000, 71999 and 1 are queried
- **THEN** exactly the corresponding normal/light/light/moderate/moderate/severe/severe stage is returned; display rounding changes none

### Requirement: Pure prediction exposes interval and travel boundaries
Rules consumers SHALL obtain validated immutable state, exact interval effects, next threshold/depletion/wake boundaries, stage and foot-speed scale without writes. Prediction SHALL distinguish interruptible intervals, indivisible completion and terminal combat so consumers cannot reinterpret exhaustion as retroactive sleep.

#### Scenario: Pre-destination depletion
- **WHEN** a sparse-edge consumer predicts a route exhausting a travelling member before the next node
- **THEN** prediction reports depletion before arrival without moving, spending or ticking any body

#### Scenario: Changing speed
- **WHEN** a 4.5 km/h human continuously walks six hours from full reserve
- **THEN** piecewise prediction crosses 70% after 13500 seconds and covers 25987.5 metres, not 27000

#### Scenario: Sleep boundary
- **WHEN** a zero-reserve forced sleeper is predicted outside combat
- **THEN** its first natural wake is 6000 seconds away; no world time passes during prediction

### Requirement: Physiology settlement is atomic and observable after commit
Reserve/posture writes SHALL occur through deterministic rules with complete affected-member validation and rollback participation. Transition events SHALL use the observability facade after durable commit with available member, commander, room, tick, session and reason context; technical failures SHALL propagate without fabricated success.

#### Scenario: Multi-member failure
- **WHEN** a write fails after the second member reserve changes
- **THEN** all durable and in-process reserve/posture/cache state equals its pre-settlement snapshot and no transition success is emitted
