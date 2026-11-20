# Spec Delta

## MODIFIED Requirements

### Requirement: Activity rates are exact net per-second effects
Ordinary awake activity, waiting and study SHALL consume 4 units/second; foot travel 8; awake combat 12; actual sleep SHALL restore 12. Qualifying paid sleep SHALL restore 24 units/second; qualifying well-rested foot travel SHALL consume 6 units/second for the remaining allowance. Effects SHALL clamp to [0,360000], use each member's declared activity, and never add ordinary awake cost again. Terrain SHALL add no exertion multiplier.

#### Scenario: Calibration
- **WHEN** a full member walks six hours without a walking allowance, spends ten further hours awake and sleeps eight hours without paid lodging
- **THEN** reserve successively becomes 187200 (52%), 43200 (12%), and 360000

#### Scenario: Exact partitions
- **WHEN** an unchanged awake activity interval is split into 1 and 2 seconds or settled as 3 seconds
- **THEN** both yield exactly 12 units consumed; equivalent sleep partitions saturate identically at full

#### Scenario: No midnight reset
- **WHEN** continuous full-reserve walking without a walking allowance spans midnight for 45000 seconds
- **THEN** reserve reaches zero from its activity cost without a daily quota or refill

#### Scenario: Paid and ordinary sleep in the same interval
- **WHEN** two bodies with sufficient reserve deficit each sleep for 10 seconds, one in qualifying paid sleep and one in ordinary sleep
- **THEN** the paid sleeper recovers 240 units and the ordinary sleeper recovers 120 units
