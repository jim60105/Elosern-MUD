# Spec Delta

## ADDED Requirements

### Requirement: A field item use names its user explicitly
An out-of-combat item use SHALL carry an explicit user member, authorized for the acting purpose, and SHALL consume the item from that member's own bag, bind SELF effects to that member, and charge the same six-second time as the commander using it, settled over the present party scope.

#### Scenario: A companion drinks her own potion
- **WHEN** the commander has companion 艾拉 use a mana potion from 艾拉's bag out of combat
- **THEN** 艾拉's potion count drops by one, 艾拉's MP rises, the commander's bag is unchanged, and the clock advances six seconds once

#### Scenario: A knocked-out user is refused
- **WHEN** the commander asks companion 卡恩 at stored HP 1 to use a potion
- **THEN** the use is rejected with `member_cannot_act` and nothing is consumed

### Requirement: Combat item use stays on the actor command flow
During an active combat session a member item use SHALL NOT resolve through the field path; the graphical action SHALL reject and the text command SHALL save the member's item command through the existing actor command path.

#### Scenario: The graphical use is refused in combat
- **WHEN** `inventory.use` naming 艾拉 arrives during an active session
- **THEN** it is rejected without mutation and nothing is consumed
