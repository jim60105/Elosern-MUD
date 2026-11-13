## ADDED Requirements

### Requirement: Four player-initiated interactions write the met-person record
The met-person record SHALL be written exactly when a player-initiated interaction names a named NPC as its target: talking to it, looking at it, using one of its services, or inviting it to the party, through the webclient or the text commands. An interaction the NPC initiates, such as attacking or addressing the player, SHALL write nothing.

#### Scenario: Looking at a named NPC records it
- **WHEN** character C looks at the named synthetic NPC `t_npc_a` through the webclient look action or the text look command
- **THEN** C's record holds `t_npc_a`

#### Scenario: Opening a conversation records it
- **WHEN** C opens a conversation with `t_npc_a` through the webclient talk action or the text talk command
- **THEN** C's record holds `t_npc_a`

#### Scenario: Using a service records the provider
- **WHEN** C buys from the named merchant `t_npc_m` through the webclient service action
- **THEN** C's record holds `t_npc_m`

#### Scenario: Inviting records the invitee whatever the answer
- **WHEN** C invites `t_npc_a` to the party and the invitation is declined
- **THEN** C's record holds `t_npc_a`

#### Scenario: Being addressed writes nothing
- **WHEN** a story scene opens a conversation in which `t_npc_b` addresses C
- **THEN** C's record does not hold `t_npc_b`

#### Scenario: A refused interaction writes nothing
- **WHEN** C's talk action is rejected because `t_npc_a` is not present
- **THEN** C's record is unchanged
