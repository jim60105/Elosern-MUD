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

### Requirement: Completed quest and passed examination facts are durable
Committed quest completion and passed guild examinations SHALL produce source-keyed deterministic facts with actual outcomes. Quest facts SHALL identify the quest and completed objective, including its destination and relevant bound identities with readable roles and required relation. Examination facts SHALL identify the examination and attained rank. Acceptance and partial progress SHALL NOT establish completion. Completion evidence SHALL be finalized before terminal bindings are cleared.

#### Scenario: Only actual completion
- **WHEN** a quest is accepted, partially progressed and then completed
- **THEN** only completion creates its completion fact with actual objective and outcome

#### Scenario: Passed exam retains rank
- **WHEN** a nonlethal examination passes and grants a rank title
- **THEN** its fact records the exam and attained rank with associated award results

#### Scenario: Producer failure aborts settlement
- **WHEN** a required fact write fails inside quest or exam settlement
- **THEN** the source gameplay and associated titles roll back with no committed fact

#### Scenario: Completed objective survives terminal binding cleanup
- **WHEN** a reach, delivery or escort objective completes and its runtime bindings are cleared
- **THEN** the immutable completion fact retains its actual destination and relevant bound target or participant identities, readable roles and required relation from the satisfied objective

#### Scenario: Automatic completion chains preserve each result
- **WHEN** one real inventory or reward settlement completes multiple quest stages or quests in an automatic chain
- **THEN** only actual completed quests produce facts and each completion retains its own pre-cleanup objective/result snapshot

#### Scenario: Discarded completion plan has no effects
- **WHEN** an inventory, delivery, arrival or action plan predicts completion but is discarded or rejected before its owner writes
- **THEN** no completion fact, completion notification or nomination request is produced

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
Settled skill and adult actions SHALL yield deterministic facts naming the skill or act, actual actor, recipients and actual committed results, with adult evidence holding equal standing. Proximity or party membership SHALL NOT imply participation; skill names or repetition SHALL NOT establish rescue, exceptional difficulty or merit. An absent optional resistance roll SHALL be normal. Producer and consumer SHALL share one committed-result vocabulary, so no supported effect is lost over a name.

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

#### Scenario: Auto-compliance has no resistance roll
- **WHEN** a legal resistible action auto-complies and its authoritative resistance result has no roll
- **THEN** the normal gameplay result and deed commit without a parsing failure, and the evidence retains the actual verdict without inventing willingness

#### Scenario: Production effect vocabulary survives persistence
- **WHEN** real settled skill or adult effects apply pleasure gain, a target or self buff, or cleansing
- **THEN** each committed effect is represented with its actual actor, recipient and result; no supported effect disappears because producer and adapter vocabulary differ

#### Scenario: Actual bounded effect remains actual
- **WHEN** an effect requests a change greater than the recipient can actually receive
- **THEN** its deed states the actual committed result rather than the requested magnitude and leaves an untouched recipient unchanged

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

### Requirement: Combat deed provenance reaches every settlement path
Combat deeds SHALL carry authoritative engagement identity and the applicable round and action-slot ordinals. Ordinary, opening, compressed and examination execution SHALL preserve that provenance. A malformed combat source SHALL NOT be relabeled as an out-of-combat cast.

#### Scenario: Ordinary and compressed sources share one identity convention
- **WHEN** ordinary and compressed execution commit actions or upkeep for different engagements
- **THEN** sources retain their real engagement and occurrence ordinals without inferring identity from narration text

#### Scenario: Examination has its own occurrence identity
- **WHEN** an examination and hostile engagement settle under otherwise matching time and participants
- **THEN** their evidence retains distinct encounter identity and examination results remain simulated

### Requirement: Visibility does not grant adult content knowledge
A narrative event's visibility SHALL govern whether a consumer may read the occurrence. It SHALL NOT grant authority to every content field. Skill and adult producers SHALL preserve field-level knowledge boundaries for every consumer, including shared memory projection.

#### Scenario: A public occurrence still requires field authorization
- **WHEN** a mixed-visibility adult occurrence is eligible for a public narrative consumer
- **THEN** the occurrence may be consumed while another participant's private fields remain excluded unless separately knowable

#### Scenario: Production composition preserves the boundary
- **WHEN** an adult action records public visibility because a third entity is present
- **THEN** nomination and memory use the same recipient parameterization rather than the event visibility flag as field authorization
