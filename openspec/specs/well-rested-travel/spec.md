# well-rested-travel Specification

## Purpose
Reward completed full lodging recovery with an exact, per-body foot-travel benefit.

## Requirements

### Requirement: A completed full paid sleep grants a nonstacking allowance
A positive-duration lodging sleep that completes with the guest awake at full HP, MP, SP, and mental reserve SHALL grant that guest two hours of well-rested foot travel. A later qualifying sleep SHALL replace the remaining allowance. Forced sleep, early wake, departure, zero elapsed time, and incomplete recovery SHALL NOT grant or refresh the allowance. A completion SHALL grant the allowance at most once across replay and reload.

#### Scenario: Qualified award and replay
- **WHEN** a guest with part of a previous allowance completes lodging sleep at full recovery and the completion is replayed after some subsequent walking
- **THEN** the original completion replaces the allowance with two hours and replay does not refill what the later walk spent

### Requirement: Foot travel consumes the allowance exactly
While allowance remains, the body's mental reserve consumption for foot travel SHALL be reduced by 25 percent. Only committed foot travel SHALL consume the allowance. Travel prediction, capacity checks, and settlement SHALL use the same allowance boundary and resulting fatigue thresholds.

#### Scenario: Exhaustion within a walking interval
- **WHEN** a traveller has five seconds left in the allowance and takes a ten-second walk spanning no other boundary
- **THEN** the first five seconds consume 30 reserve units and the last five consume 40; preview predicts the same 70-unit loss and the allowance reaches zero

#### Scenario: Nonwalking and interrupted time
- **WHEN** a guest waits, reloads, then starts a walking interval that stops early
- **THEN** the wait and reload consume no allowance and the interrupted walk consumes only its committed walking seconds
