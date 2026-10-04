# correspondence-npc-replies Specification

## Purpose
Lets NPCs propose free-text replies from delivered-letter cognition without making delivery depend on generation or granting face-to-face action authority.

## Requirements

### Requirement: Replies use delivered inputs and remain optional

NPC reply generation SHALL use only delivered incoming letters and owner-permitted cognition. Replies SHALL retain reply-to and immutable source snapshot. Failed generation SHALL leave durable work pending without fabricating text or blocking delivery. Successful outgoing send SHALL begin its own one-game-hour delay at commit.

#### Scenario: Services unavailable at delivery
- **WHEN** an NPC letter becomes delivered while generation is offline
- **THEN** delivery succeeds and reply work remains pending with no invented response

#### Scenario: Delayed reply generation
- **WHEN** a response validates long after incoming delivery
- **THEN** its outgoing due tick is one hour after its own send commit

#### Scenario: Restart repeats reply work
- **WHEN** successful reply settlement is replayed after interruption
- **THEN** the same source creates only one outgoing letter

### Requirement: Correspondence cannot execute physical or quest actions

Channel affordances SHALL allow speech/information, memories, clues and invitations as statements plus deterministically validated relationship proposals. They SHALL NOT accept quests, satisfy objectives, confirm appointments, transfer items or execute physical actions. Relationship effects SHALL route through the existing rules owner; face-to-face co-location and full intent whitelists SHALL NOT be reused unchanged.

#### Scenario: Letter offers or claims quest completion
- **WHEN** a reply proposes offer_quest or says an objective is done
- **THEN** the channel rejects the effect and quest state remains unchanged

#### Scenario: Remote relationship proposal
- **WHEN** a permitted relation proposal validates between remote correspondents
- **THEN** the rules owner revalidates/budgets its own change without a face-to-face co-location requirement

#### Scenario: Willingness is speech only
- **WHEN** a reply states willingness to meet
- **THEN** it remains a remembered statement and creates no formal appointment
