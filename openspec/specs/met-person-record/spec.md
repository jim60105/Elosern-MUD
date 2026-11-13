# met-person-record Specification

## Purpose
Record, per character, which named NPCs the character has interacted with,
where and when, through one deterministic writer, so the gallery can list the
people a player has a reason to know.

## Requirements

### Requirement: Each character owns one met-person record keyed by portrait stable key
Each character SHALL own one record holding at most one entry per named NPC, keyed by the NPC's portrait stable key and carrying the NPC's identity, the place key and the time of the last interaction. Only an NPC with a named portrait policy SHALL be recorded. Exactly one module SHALL write the record.

#### Scenario: A named NPC is recorded once
- **WHEN** the writer records two interactions of character C with the named synthetic NPC `t_npc_a`
- **THEN** C's record holds one entry for `t_npc_a` with the time of the second interaction

#### Scenario: A generic NPC is not recorded
- **WHEN** the writer is asked to record an interaction with an NPC on the generic portrait policy
- **THEN** the record is unchanged

#### Scenario: Records belong to their character
- **WHEN** character C records `t_npc_a` and character D of the same account records nothing
- **THEN** D's record is empty

### Requirement: The place is the settlement, else the wilderness region
The place of an interaction SHALL be the settlement whose map holds the room, else the wilderness region of the cell, resolving an instance room through its origin room. A district SHALL never be a place. Every interaction SHALL update the time; the stored place SHALL be rewritten only when the new place is known and differs.

#### Scenario: Moving inside a settlement keeps the place
- **WHEN** two interactions happen in two rooms of the same synthetic settlement map
- **THEN** the entry's place is that settlement and only its time changed

#### Scenario: A wilderness interaction records the region
- **WHEN** an interaction happens on a synthetic wilderness cell of region `t_region`
- **THEN** the entry's place is `t_region`

#### Scenario: An unknown place keeps the stored place
- **WHEN** an interaction happens in a room with no derivable place for an NPC already recorded
- **THEN** the stored place is kept and the time is updated

### Requirement: Possessed interactions are recorded for the owning character
An interaction made while the actor is a possessed companion SHALL be recorded in the record of the character that owns that companion.

#### Scenario: The owner receives the entry
- **WHEN** character C possesses companion K and K interacts with `t_npc_a`
- **THEN** C's record holds the entry and K holds no record

### Requirement: Vanished NPCs are skipped on read and dropped on write
A read SHALL omit entries whose NPC no longer exists or no longer carries the recorded stable key. The writer SHALL drop such entries whenever it writes the record. No cleanup job SHALL exist.

#### Scenario: A deleted NPC disappears from reads
- **WHEN** `t_npc_a` is deleted after being recorded
- **THEN** reading C's record omits it, and the next write for C removes its entry

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
