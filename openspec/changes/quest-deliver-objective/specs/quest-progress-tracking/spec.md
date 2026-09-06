# Delta spec: quest-progress-tracking (quest-deliver-objective)

## MODIFIED Requirements

### Requirement: Stage completion advances exactly once and releases obsolete runtime bindings
When progress reaches an objective's quantity, the runtime SHALL release the current stage's instance
pin, clear all current-stage runtime bindings, reset progress, and either enter the next contiguous stage
or mark the quest `COMPLETED` if the objective was final. One event, room hook, or committed item
transfer SHALL transition a given quest at most once even when its quantity exceeds the remaining
amount. Terminal records SHALL ignore later matching events, hooks, and transfers.

#### Scenario: Intermediate objective enters the next stage
- **WHEN** a matching event satisfies a non-final stage
- **THEN** the record advances by one stage, resets progress to zero, clears bindings, and remains active

#### Scenario: Final objective completes the quest
- **WHEN** a matching event satisfies the final stage
- **THEN** state becomes `COMPLETED`, progress is capped at the objective quantity, and bindings are
  cleared

#### Scenario: Instance pin is released on stage exit
- **WHEN** a bound-instance stage advances or completes
- **THEN** its exact quest pin is absent before the transition returns, while room deletion and promotion
  remain exclusively owned by map-instance reclamation

#### Scenario: One transfer advances a delivery stage at most once
- **WHEN** a single committed transfer carries more of the objective's item than the delivery stage
  still needs
- **THEN** the stage advances exactly once, progress is capped at the objective quantity, and the
  surplus does not carry into the next stage

#### Scenario: A terminal record ignores a later matching transfer
- **WHEN** the objective's item is transferred to the former recipient after the quest is `COMPLETED`
  or `FAILED`
- **THEN** the record is unchanged
