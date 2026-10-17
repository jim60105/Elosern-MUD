# Spec Delta

## ADDED Requirements

### Requirement: A companion's field cast may open combat under the commander's session
A field cast whose caster is a present companion and whose target is a co-located living monster (an explicit anchor or a normalized single monster target) SHALL open combat through the existing field-initiation path exactly as the commander's cast would, with the session owned by the commander and the opening skill seeded as the caster's draft entry; the caster's resources and practice are accounted once when that entry resolves.

#### Scenario: A companion's spell opens combat
- **WHEN** the commander has 艾拉 cast 冰錐術 at a monster in the room out of combat
- **THEN** one hostile session owned by the commander is persisted, 冰錐術 is saved as 艾拉's opening draft entry, no command time is charged, and 艾拉's MP and practice change only when that entry resolves in the round

#### Scenario: A forged or stale caster cannot open combat
- **WHEN** the caster names an NPC outside the party, or a companion that has left the room
- **THEN** the cast is rejected with `not_party_member` or `member_not_present` before any session, resource, roll or clock access, and the commander is not used in its place

#### Scenario: The commander still has to command
- **WHEN** a companion opened combat
- **THEN** the round resolves only once every required member, the commander included, has a confirmed draft entry, exactly as for a commander-opened encounter

#### Scenario: A possessed caster opens the commander's encounter
- **WHEN** the player, possessing 艾拉, casts 冰錐術 at a room monster
- **THEN** the session is owned by the commander, 艾拉's opening entry is seeded, and the commander and 卡恩 are required actors

#### Scenario: A commanded companion caster opens the commander's encounter
- **WHEN** the commander, not possessing anyone, has 艾拉 cast 冰錐術 at a room monster
- **THEN** the same commander-owned session and 艾拉 opening entry result as in the possessed case
