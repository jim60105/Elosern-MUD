# Spec Delta

## ADDED Requirements

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

