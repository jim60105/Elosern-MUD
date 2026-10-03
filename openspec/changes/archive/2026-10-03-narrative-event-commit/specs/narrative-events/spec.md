## Purpose

Makes selected committed narrative facts durable and gives derived work restart-safe identities without replacing the transient gameplay event log.

## ADDED Requirements

### Requirement: Narrative facts commit atomically with covered gameplay

The system SHALL durably record selected covered gameplay facts and pending projection progress in the same outer database transaction as the committed result. Each fact SHALL carry structured content, participants, applicable location, world tick, visibility, salience, and a stable source identity. Rejected or rolled-back actions SHALL expose no durable fact.

#### Scenario: Successful protection survives restart
- **WHEN** a synthetic protection encounter commits and the process restarts
- **THEN** its fact and pending projection work retain persistent participant identities

#### Scenario: Outer settlement fails
- **WHEN** a later operation in the covered outer transaction fails
- **THEN** gameplay, events, progress, and cached state return to their prior state

#### Scenario: Compressed encounter retains sources
- **WHEN** the protection encounter uses compressed rather than ordinary rounds
- **THEN** selected facts have stable identities and are not lost with narration compression

### Requirement: Durable source identity makes projection recoverable

Pending derived work SHALL survive interruption and be rediscoverable without a transient callback. Reprocessing a source SHALL NOT duplicate facts or progress; distinct occurrences with identical text SHALL remain distinct.

#### Scenario: Callback never runs
- **WHEN** a process exits after commit before waking projection
- **THEN** restart discovers the pending source

#### Scenario: Equal prose is repeated
- **WHEN** two distinct committed occurrences have equal rendered text
- **THEN** their durable source identities remain distinct

