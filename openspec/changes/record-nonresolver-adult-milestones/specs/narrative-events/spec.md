# Spec Delta

## ADDED Requirements

### Requirement: Non-resolver adult milestones are recorded at transition time
Combat upkeep, accepted item use and defeat-aftermath adult transitions SHALL record newly crossed milestones or actual eligible adult-action outcomes in the transaction that applies them, using an authoritative operation or encounter identity and the actual world tick. A pre-existing threshold SHALL NOT be recorded as recent. Later clock reads SHALL NOT substitute for a missed transition.

#### Scenario: Upkeep buff reaction crossing is retained once
- **WHEN** a committed upkeep buff reaction raises pleasure across an onset or unlock threshold before the later state snapshot
- **THEN** that crossing is recorded once under the upkeep occurrence and a subsequent clock read records no duplicate milestone

#### Scenario: Accepted item use crossing uses the accepted operation
- **WHEN** one accepted item use raises several recipients across an onset or unlock threshold
- **THEN** only actual affected recipients receive transition-time evidence under that accepted operation, while an unaffected control remains untouched and a later clock read adds nothing

#### Scenario: Combat item use joins its own accepted operation
- **WHEN** an item is used inside a combat slot while another slot later consumes a similar effect
- **THEN** each accepted operation retains a distinct source and the combat encounter join without collapsing or duplicating milestones

#### Scenario: Defeat aftermath records actual adult outcomes once
- **WHEN** a defeat aftermath applies an adult attempt whose declared outcome lands or is resisted for a selected victim
- **THEN** the eligible adult action and its actual resistance outcome are recorded under the unique engagement attempt, with newly crossed victim milestones and no invented participation for unselected or untouched allies

#### Scenario: Owner rollback removes evidence with the gameplay
- **WHEN** the item or defeat-aftermath writer fails after recording its adult evidence but before the owning transaction commits
- **THEN** consumption, effects, counters, milestone evidence and memory work roll back together

#### Scenario: Replayed owner settlement does not create another crossing
- **WHEN** committed upkeep or defeat evidence is notified again for the same operation and ordinal
- **THEN** the original evidence and crossing are reused without applying gameplay or creating a second milestone
