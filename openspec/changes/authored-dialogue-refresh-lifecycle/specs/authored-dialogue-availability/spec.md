# Spec Delta

## ADDED Requirements

### Requirement: Progression and world lifecycle refresh every relevant conversation
Owner guild, quest, claim and host-affinity changes, bound companion membership/presence changes and world-time commits SHALL refresh affected current dialogue contexts. Phase or control retirement SHALL clear obsolete delivery/receipts. No-session or another-connection origins SHALL preserve these semantics.

#### Scenario: Another companion departs
- **WHEN** a conversation host remains but a required bound companion leaves the actor room
- **THEN** the conversation topic relocks immediately after the move commit, without waiting for another topic selection

#### Scenario: Noncompletion quest transition
- **WHEN** a named quest is accepted, fails, invalidates or is abandoned by its owner through another connection
- **THEN** current topic eligibility is refreshed for that exact saved lifecycle state

#### Scenario: World time beyond action scope
- **WHEN** a clock commit crosses a daypart boundary and a different valid owner conversation depends on time
- **THEN** that conversation receives current availability without relying on WebClient command observation

### Requirement: Committed state changes refresh eligibility without rewriting playback
Relevant committed state changes SHALL refresh dialogue availability from canonical state. Failed or rolled-back changes SHALL publish no false opening. Ordinary eligibility refresh SHALL preserve a delivered scene variant, while host, phase or control invalidation SHALL retire it.

#### Scenario: Equipped exposure refreshes choices
- **WHEN** a lawful equipment commit crosses a topic exposure boundary during a scene
- **THEN** choices reflect new availability while playing wording remains fixed

#### Scenario: Every condition source refreshes
- **WHEN** item holdings, social identity, skills, owner rank/quest/claim/affinity, companion presence or world time commits a change
- **THEN** the next committed dialogue projection reflects that source without another topic selection

