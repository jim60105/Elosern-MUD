# narrative-story-threads Specification

## Purpose
Maintains continuity across committed events, cognition, and correspondence without conflating factual history, unfulfilled plans, or quest lifecycle.

## Requirements

### Requirement: Thread lifecycle preserves facts separately from plans

Threads SHALL retain origin, participants, factual summary, unresolved questions, gameplay-established commitments, memory references and development ticks. States SHALL be active, dormant, resolved or abandoned. Inactivity SHALL NOT imply abandonment and quest completion SHALL NOT automatically resolve a parent thread.

#### Scenario: Quest completes with open questions
- **WHEN** a linked quest finishes while the thread has unresolved continuity
- **THEN** the quest finishes through its owner and the thread remains appropriately active/dormant

#### Scenario: Long inactivity
- **WHEN** a thread receives no development for several game days
- **THEN** it is not marked abandoned solely for inactivity

#### Scenario: Letter willingness is linked
- **WHEN** a correspondence statement expresses willingness
- **THEN** it is linked as speech/plan, not a gameplay-established commitment

### Requirement: Real linkage revisions invalidate future context

Events, memories, letters and preserved dialogue SHALL support real thread linkage with durable provenance. Effective thread changes SHALL increase a thread revision and invalidate new retrieval snapshots, while old captured snapshots SHALL keep their read revision. Explicit thread recall scope SHALL filter before ranking.

#### Scenario: Thread revision changes during generation
- **WHEN** thread linkage or factual summary changes after capture
- **THEN** new context uses the new revision and historical capture retains the previous one

#### Scenario: Requested thread is private
- **WHEN** an owner requests retrieval scoped to an inaccessible thread
- **THEN** no private thread or source content enters recall
