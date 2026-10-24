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

### Requirement: Player-facing text names the reserve 精力
Every player-facing surface that names a body's mental reserve SHALL call it 精力: the status panel's fatigue row, the travel refusal for predicted pre-destination depletion, the sleep-handoff candidate label shared by the text and browser clients, and the player command documentation. No player-facing text SHALL use 精神儲備, and 精力 SHALL name nothing but the reserve; text that means SP SHALL call it 耐力. Fatigue stage labels SHALL stay unchanged.

#### Scenario: The status row names 精力
- **WHEN** the status panel renders a fatigue row for 艾倫 at 80% with the stage label 精神充沛
- **THEN** the row reads `艾倫：精力 80%（精神充沛）` and does not contain 精神儲備

#### Scenario: The travel refusal names 精力
- **WHEN** a departure is refused because a present traveller is predicted to exhaust the reserve before the destination
- **THEN** the refusal message is exactly `隊伍成員的精力不足以支撐這趟旅行。`

#### Scenario: The handoff candidates name 精力
- **WHEN** the sleep-handoff list offers the return to the owner's body at 100% and an awake companion 清醒同伴 at 100%
- **THEN** the labels read `回到自己的身體（精力 100%）` and `接手 清醒同伴（精力 100%）` in both the text listing and the browser roster

#### Scenario: Stage labels are unchanged
- **WHEN** a body is at any fatigue stage
- **THEN** its stage label is still one of 精神充沛, 輕度疲勞, 中度疲勞, 重度疲勞, 強制睡眠, or 沉睡

#### Scenario: The guild exam start names SP 耐力
- **WHEN** a guild rank exam starts for rank E (the text command and the browser action share one start message)
- **THEN** the message reads `升階考核（E）開始。這是模擬戰，雙方在開戰前與結束後都會恢復全部的體力、法力與耐力。` and does not contain 精力

#### Scenario: The player docs use 精力
- **WHEN** `docs/game/commands.md` and `docs/game/command-reference.md` are searched for 精神儲備 and 滿儲備
- **THEN** there is no match, the sleep descriptions say 精力全滿 instead of 滿儲備, and the `狀態` entry's 說明 names 精力 together with 疲勞階段 and 無法行動
