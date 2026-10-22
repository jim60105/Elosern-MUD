# Spec Delta

## MODIFIED Requirements

### Requirement: Durable source identity makes projection recoverable
Pending derived work SHALL survive interruption and be rediscoverable without a transient callback. Reprocessing a source SHALL NOT duplicate facts or progress; distinct occurrences with identical text SHALL remain distinct. Combat action and upkeep occurrences SHALL use authoritative engagement, round and applicable slot identity instead of world tick or display text, so distinct committed occurrences can never share a source.

#### Scenario: Callback never runs
- **WHEN** a process exits after commit before waking projection
- **THEN** restart discovers the pending source

#### Scenario: Equal prose is repeated
- **WHEN** two distinct committed occurrences have equal rendered text
- **THEN** their durable source identities remain distinct

#### Scenario: Same skill in distinct combat slots remains distinct
- **WHEN** one actor commits the same skill in distinct slots or rounds of one engagement while world time has not advanced
- **THEN** each committed occurrence has a distinct stable source with its own results and original award evidence

#### Scenario: Combat evidence replay reuses occurrence identity
- **WHEN** committed action or upkeep settlement evidence is notified again for the same engagement and ordinal
- **THEN** the original immutable source and projection progress are reused without another occurrence or erased awards

#### Scenario: Separate same-tick engagements remain separate
- **WHEN** two actual engagements begin under the same reusable session token and world tick
- **THEN** their terminal, action and upkeep sources remain distinct by authoritative engagement identity

## ADDED Requirements
### Requirement: Combat deed provenance reaches every settlement path
Combat deeds SHALL carry authoritative engagement identity and the applicable round and action-slot ordinals. Ordinary, opening, compressed and examination execution SHALL preserve that provenance. A malformed combat source SHALL NOT be relabeled as an out-of-combat cast.

#### Scenario: Ordinary and compressed sources share one identity convention
- **WHEN** ordinary and compressed execution commit actions or upkeep for different engagements
- **THEN** sources retain their real engagement and occurrence ordinals without inferring identity from narration text

#### Scenario: Examination has its own occurrence identity
- **WHEN** an examination and hostile engagement settle under otherwise matching time and participants
- **THEN** their evidence retains distinct encounter identity and examination results remain simulated
