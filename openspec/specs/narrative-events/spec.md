# narrative-events Specification

## Purpose
Makes selected committed narrative facts durable and gives derived work restart-safe identities without replacing the transient gameplay event log.

## Requirements

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

### Requirement: Completed quest and passed examination facts are durable
Committed quest completion and passed guild examinations SHALL produce source-keyed deterministic facts with actual outcomes. Quest facts SHALL identify the quest and completed objective. Examination facts SHALL identify the examination and attained rank. Acceptance and partial progress SHALL NOT establish completion.

#### Scenario: Only actual completion
- **WHEN** a quest is accepted, partially progressed and then completed
- **THEN** only completion creates its completion fact with actual objective and outcome

#### Scenario: Passed exam retains rank
- **WHEN** a nonlethal examination passes and grants a rank title
- **THEN** its fact records the exam and attained rank with associated award results

#### Scenario: Producer failure aborts settlement
- **WHEN** a required fact write fails inside quest or exam settlement
- **THEN** the source gameplay and associated titles roll back with no committed fact

### Requirement: Completed combat evidence preserves the actual encounter outcome
Completed combat facts SHALL summarize actual victory, defeat or escape with durable participants, opponents and encounter mode. Nonlethal examination outcomes SHALL NOT become lethal victories. Replayed terminal settlement SHALL NOT duplicate occurrences. Existing protection consumers SHALL remain unchanged.

#### Scenario: Terminal outcomes are distinct
- **WHEN** hostile victory, defeat and escape settle in separate encounters
- **THEN** each fact states its actual outcome and participant roles without inferring protection

#### Scenario: Compressed encounter is retained
- **WHEN** a completed encounter used compressed rounds
- **THEN** its terminal fact retains stable provenance without per-hit encounter claims

#### Scenario: Outer rollback and replay
- **WHEN** terminal settlement is first rolled back and later committed and replayed
- **THEN** rollback leaves no fact or title grant and replay leaves one immutable source with original awards

### Requirement: Settled skill and adult actions retain deterministic roles and results

Settled skill and adult actions SHALL produce deterministic facts identifying the skill or act, actual actor, recipients and committed effects. Adult actions SHALL have equal evidence standing. Proximity or party membership SHALL NOT imply participation. Skill names and repeated casting SHALL NOT establish rescue, exceptional difficulty or merit.

#### Scenario: Concrete skill effects
- **WHEN** a skill heals a recipient without protection evidence
- **THEN** the record states actual actor, recipient and effect without a rescue claim

#### Scenario: Adult outcome retains meaning
- **WHEN** an adult action settles structured transition, counter and resistance results
- **THEN** the record retains the established act, roles and actual outcomes without reversing resistance or inferring willingness

#### Scenario: Untouched recipient is excluded
- **WHEN** a nearby party member receives no action or effect
- **THEN** the member is not attributed an adult participation role

#### Scenario: Action rollback and replay
- **WHEN** a source fails after deed/title writes, then later commits and replays
- **THEN** the failed transaction leaves no effects or evidence and the replay retains one committed occurrence and its original award results

### Requirement: Adult milestones record newly crossed transitions

New adult experience, actually crossed unlocks and significant state transitions SHALL be recorded at their authoritative transition tick with stable source identity. Existing lifetime counters or state SHALL NOT be dated as recent occurrences. Repeated settlement SHALL NOT duplicate milestones.

#### Scenario: New threshold is recorded once
- **WHEN** a synthetic adult threshold is crossed and its settlement is replayed
- **THEN** one milestone records the actual crossing with the action provenance

#### Scenario: Old lifetime state has no recency
- **WHEN** an existing counter or experience set is merely read or reconstructed
- **THEN** no recent milestone is created

### Requirement: Adult evidence does not invent consent or public standing

Adult facts SHALL preserve actual roles and knowability. Numerical arousal, climax and automatic compliance SHALL NOT establish affection, willingness or commitment. Private experience SHALL NOT establish public notoriety, witnesses or public recognition.

#### Scenario: Resistance remains resistance
- **WHEN** a committed resistance outcome accompanies arousal or climax
- **THEN** evidence retains resistance and makes no consent or relationship inference

#### Scenario: Private experience stays personal
- **WHEN** a player has accessible private personal experience
- **THEN** it can support personal nomination without a public recognition claim or title-display policy change
