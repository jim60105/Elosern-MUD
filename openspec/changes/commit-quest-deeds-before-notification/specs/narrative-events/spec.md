# Spec Delta

## MODIFIED Requirements

### Requirement: Completed quest and passed examination facts are durable
Committed quest completion and passed guild examinations SHALL produce source-keyed deterministic facts with actual outcomes. Quest facts SHALL identify the quest and completed objective, including its destination and relevant bound participant identities, readable roles and required relation. Examination facts SHALL identify the examination and attained rank. Acceptance and partial progress SHALL NOT establish completion. Completion evidence SHALL be finalized before terminal bindings are cleared.

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
