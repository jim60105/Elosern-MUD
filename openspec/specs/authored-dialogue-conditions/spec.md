# authored-dialogue-conditions Specification

## Purpose
Provide actor identity, inventory, present companion, time, skills and exposure conditions through deterministic, independently testable behavior while preserving authoritative game ownership and offline play.

## Requirements

### Requirement: Generated physical references retain canonical and package scope
Every physical condition SHALL apply equally to static/generated scenes. Package-role companion references SHALL resolve only a permitted role in the current package and require authoritative current membership and actor-local presence. Foreign, detached, cancelled or remote role bindings SHALL fail closed.

#### Scenario: Same role ID in a foreign package grants nothing
- **WHEN** a different package has a present companion with the same local role ID
- **THEN** it cannot satisfy the current package-scoped companion condition

### Requirement: Physical conditions use the acting body and canonical readers
Race, social identity, carried item, skill and exposure conditions SHALL use the acting body. Companion conditions SHALL require current owner membership and actor-local presence. Time conditions SHALL use in-world daypart bounds. Evaluation SHALL be read-only and SHALL fail closed on invalid authoritative state.

#### Scenario: Commander inventory grants nothing
- **WHEN** an owner carries the required item while its possessed actor does not
- **THEN** the actor carrying condition fails and no item is consumed

#### Scenario: Worn bias changes exposure eligibility
- **WHEN** an equipment commit changes the acting body effective exposure across an inclusive bound
- **THEN** the next evaluation changes through the canonical effective-exposure reader without creating a sexual handler

### Requirement: Combination hints and complete-scene variants share declarations
Conjunction, disjunction and requirement hints SHALL use the same typed conditions and canonical labels. Highest explicit matching variant priority SHALL select a complete scene with a general fallback; current playback SHALL not change midway.

#### Scenario: World time wraps midnight
- **WHEN** an interval runs from dusk to dawn and the world clock is at midnight, dawn and noon
- **THEN** it matches midnight, excludes dawn and noon, with zero wall-clock reads

#### Scenario: Skill boundary and present companion
- **WHEN** an actor owns a skill at its threshold and a named bound companion is remote
- **THEN** the skill condition passes, companion condition fails, and the all/any hint explains that same tree

#### Scenario: Possessed race scene is visible
- **WHEN** a lawfully possessed elf body selects a race-qualified synthetic topic with models disabled
- **THEN** the actor portrait and full elf variant appear while its human owner retains progression ownership

### Requirement: Generated progression references use the shared owner semantics
Generated scenes SHALL qualify owner rank, quest lifecycle/claim and host affinity through the same canonical readers as static scenes. Quest references SHALL be permitted canonical definitions or the authorized current package's compiled definition; static registry membership SHALL not be required for a package definition.

#### Scenario: Package quest lifecycle qualifies without static registration
- **WHEN** the owner has a permitted current-package quest record and another package has a similarly named definition
- **THEN** the matching current-package state qualifies and the foreign definition grants nothing

### Requirement: Progression conditions resolve the owner and host relationship
Guild rank and quest conditions SHALL read the owning player. Affinity conditions SHALL read the conversation host relationship toward that owner. Canonical rank and affinity-stage order SHALL govern thresholds, and public hints SHALL omit private relationship numbers.

#### Scenario: Actor rank cannot substitute
- **WHEN** the possessed body has a qualifying rank but owner has no registration
- **THEN** guild qualification fails and no protected formal scene is delivered

#### Scenario: Public relationship hint
- **WHEN** a topic needs a canonical host-to-owner affinity stage
- **THEN** the hint names that stage without disclosing the current or threshold numeric relationship value

### Requirement: Quest predicates distinguish lifecycle and reward claims
Quest qualification SHALL distinguish absence, in-progress, completed, reward-claimed, failed and invalidated states. A claimed predicate SHALL require the matching completed record and its authoritative shared claim receipt; reading acknowledgement SHALL never grant that receipt.

#### Scenario: Completed before and after payment
- **WHEN** a matching completed quest is first unclaimed and then claimed
- **THEN** completed qualifies both times while reward-claimed qualifies only after the claim commits

#### Scenario: Repeatable and unrelated records
- **WHEN** one matching quest instance is failed, another is in-progress and an unrelated quest has a claim
- **THEN** in-progress qualifies, failed qualifies and reward-claimed does not qualify for the named definition
