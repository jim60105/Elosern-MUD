## ADDED Requirements

### Requirement: Companions assist the player's quest objectives
A bound companion's contributions SHALL count toward the quest owner's active objectives: a
DEFEAT entry produced by a bound companion's action SHALL advance the owner's matching DEFEAT
stage through the same commit-time planner rules as the owner's own kills (same aggregation,
cap, and one-transition rules), only while the binding is valid in both directions (the actor
appears in the owner's valid party list and the actor's back-reference points to the owner) and
the actor is not knocked out; a knocked-out companion's, unbound NPC's, or mismatched binding's
entries SHALL NOT count, and a credit decision without an active battlefield SHALL fail closed.
A REACH or ESCORT arrival SHALL advance when the player arrives at the destination and at least
one bound companion is present in the destination room — already there or arriving with the
player; ESCORT SHALL keep requiring every protected entity alive and present. The arrival
observation SHALL run again after companions complete their follow moves, so co-presence on the
first arrival is visible, and the one-transition rule SHALL make the repeated observation
idempotent. Unbound entities, other players' companions, and monster kills SHALL grant no credit.
The player's active quest record SHALL be the only record advanced; companions SHALL have no quest
log of their own.

#### Scenario: A companion's kill advances the owner's DEFEAT objective
- **WHEN** a bound companion's action lethally defeats a monster matching the owner's active DEFEAT stage, with a valid bidirectional binding and an active battlefield
- **THEN** the owner's quest progress advances in the same action, capped and transitioned exactly once

#### Scenario: A knocked-out companion's kill grants no credit
- **WHEN** a knocked-out companion's action defeats a matching monster
- **THEN** the owner's quest progress is unchanged

#### Scenario: An unbound NPC's kill grants no credit
- **WHEN** an NPC that is not a bound companion defeats a matching monster
- **THEN** the owner's quest progress is unchanged

#### Scenario: A mismatched binding grants no credit
- **WHEN** an NPC whose back-reference points to the owner but who is absent from the owner's party list defeats a matching monster
- **THEN** the owner's quest progress is unchanged

#### Scenario: Companion co-presence satisfies an arrival objective
- **WHEN** the player arrives at the destination and at least one bound companion is present there, and the follow moves have completed
- **THEN** a matching REACH or ESCORT arrival advances exactly once

#### Scenario: Escort still requires every protected entity alive and present
- **WHEN** a companion is present at an ESCORT destination but a protected entity is absent or dead
- **THEN** the stage remains unchanged

### Requirement: Completing a quest rewards each then-in-party companion with affinity
Quest reward settlement SHALL grant +2 affinity (source `quest_completion`, exempt from the daily
cap) to every companion in the player's party at turn-in, through the sole-writer affinity API
(`world/rules/affinity.py`), committed atomically with the reward transaction: wallet, inventory,
merit, ACQUIRE progress, claims, and every affected companion's affinity record SHALL commit
together, and a fault at any write position SHALL restore all surfaces including the affinity
records and their in-process caches. Companions SHALL receive no XP, items, or merit.

#### Scenario: Turn-in rewards the party with affinity
- **WHEN** a player turns in a completed quest with two bound companions in the party
- **THEN** each companion's affinity value rises by 2, alongside the ordinary reward surfaces, in
  one committed operation

#### Scenario: Only then-in-party companions earn the bonus
- **WHEN** a player turns in a quest while one bound companion is in the party and another is not
- **THEN** only the in-party companion's affinity rises by 2

#### Scenario: A quest-completion gain bypasses the daily cap
- **WHEN** a companion's interaction budget is exhausted for the day and a turn-in grants the bonus
- **THEN** the +2 applies and the daily interaction counter is unchanged

#### Scenario: A failed reward write restores every surface
- **WHEN** any reward or affinity write is fault-injected after preceding writes
- **THEN** wallet, inventory, merit, quest log, claims, and every companion's affinity record — and
  their in-process caches — equal their pre-turn-in values
