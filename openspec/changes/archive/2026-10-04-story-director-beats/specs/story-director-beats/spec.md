## Purpose

Generates bounded beat proposals from eligible continuity or confirmed direction and applies only implemented deterministic effects with stale-state and concurrency gates.

## ADDED Requirements

### Requirement: Director schedules at most one eligible beat

Each decision SHALL use bounded attention candidates or a confirmed valid creative request and SHALL schedule at most one new beat, including choosing none. Proposals SHALL be limited to follow-up, letter, clue, invitation or quest seed with implemented deterministic capability. Automatic unrelated stories SHALL be rejected.

#### Scenario: Two proposals compete
- **WHEN** one decision produces multiple competing arrangements
- **THEN** no more than one new beat schedules

#### Scenario: Nothing validates
- **WHEN** validation/retry exhausts or no candidate is eligible
- **THEN** no new content is fabricated and thread state remains intact

#### Scenario: Unsupported effect
- **WHEN** a proposal asks for an effect with no deterministic owner implementation
- **THEN** it is rejected without placeholder execution

### Requirement: Beat application preserves owner and snapshot boundaries

Before apply the deterministic core SHALL revalidate relevant state/revisions and prevent conflicting concurrent arrangements within one thread. Narrative SHALL apply only narrative-owned data; relationships/actions SHALL route to rules, quests to quests, rooms/instances to maps. world/ai SHALL propose only. Restart/repeated source processing SHALL NOT duplicate scheduled beats.

#### Scenario: Old snapshot conflicts
- **WHEN** the thread or executable state changes before generated proposal settlement
- **THEN** revalidation rejects the conflict without partial state

#### Scenario: Concurrent same-thread decisions
- **WHEN** two decision settlements target one thread revision
- **THEN** serialization permits no conflicting arrangements

#### Scenario: Repeated scheduling after restart
- **WHEN** the same accepted decision source settles again
- **THEN** one scheduled beat exists

#### Scenario: Generator tries cross-owner write
- **WHEN** a proposal claims direct trait/quest/room mutation
- **THEN** validation rejects it and all unauthorized state remains unchanged

### Requirement: Collaborator and director contexts remain separate

StoryDirector SHALL have its own capability schema, prompt version, immutable snapshot and context permissions; hidden planning facts SHALL not enter collaborator/NPC contexts merely because capabilities share a model.

#### Scenario: One deployment profile is shared
- **WHEN** collaborator and director use the same model endpoint
- **THEN** their histories/snapshots and permitted facts remain separate

