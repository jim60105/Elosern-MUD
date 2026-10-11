# Spec Delta

## MODIFIED Requirements

### Requirement: Director schedules at most one eligible beat

Each decision SHALL use bounded attention candidates or a confirmed valid creative request and schedule at most one new beat, including choosing none. Proposals SHALL remain follow-up, letter, clue, invitation or quest seed with implemented deterministic capability. Confirmed dispatch SHALL validate the shown experience requirements; a quest scene SHALL use the quest-seed route with explicit scene needs. Automatic unrelated stories and unrestricted spawn effects SHALL be rejected.

#### Scenario: Two proposals compete
- **WHEN** one decision produces multiple competing arrangements
- **THEN** no more than one new beat schedules

#### Scenario: Nothing validates
- **WHEN** validation/retry exhausts or no candidate is eligible
- **THEN** no new content is fabricated, thread state remains intact and confirmed dispatch cannot be arranged

#### Scenario: Unsupported effect
- **WHEN** a proposal asks for an effect with no deterministic owner implementation
- **THEN** it is rejected without placeholder execution

#### Scenario: Readable prose omits requested roles
- **WHEN** a direction requiring actual characters/private escort receives only a private statement, letter, clue summary or unregistered quest key
- **THEN** completeness validation fails with a durable reason and no successful arrangement

### Requirement: Beat application preserves owner and snapshot boundaries

The deterministic core SHALL revalidate relevant source/version, owner, thread revisions, map references, required actors, issuance scope and executable capabilities before apply, serializing conflicting thread arrangements. Narrative, rules, quests and maps SHALL retain their respective writers; AI SHALL propose only. Accepted source replay SHALL not duplicate beats. Current room SHALL matter only for an actual declared condition, not an unrelated movement during future encounter generation.

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

#### Scenario: Player moves during generation
- **WHEN** the player leaves the south gate while a future south-gate encounter is generated and no declared condition depends on current room
- **THEN** that movement alone does not reject publication or move the encounter to the player's new room

#### Scenario: Required actor identity changes
- **WHEN** a required exact actor is removed or replaced before settlement
- **THEN** settlement rejects with the distinct actor reason without substituting a same-named actor

### Requirement: Collaborator and director contexts remain separate

StoryDirector SHALL have its own capability schema, prompt version, immutable provenance-bearing snapshot and permissions. ScenarioDirector SHALL receive only permitted immutable planning data required for the scene blueprint. Sharing a configured model SHALL NOT share collaborator, StoryDirector, ScenarioDirector or NPC histories/private knowledge. Confirmed requirements SHALL accompany planning without granting NPC authority or knowledge.

#### Scenario: One deployment profile is shared
- **WHEN** collaborator and both directors use the same model endpoint
- **THEN** recorded messages show separate histories/snapshots and permitted facts for each capability

#### Scenario: Scenario context is narrowed
- **WHEN** StoryDirector produces a supported quest scene arrangement
- **THEN** ScenarioDirector receives bounded role/locator/issuance planning context without unrelated private director history or live entity references
