# companion-field-actions Specification

## Purpose
Let a present party member, chosen explicitly by the player, perform out-of-combat field actions with that member's own skills, items, costs and growth.

## Requirements

### Requirement: A field cast names its caster explicitly
An out-of-combat field cast SHALL carry an explicit caster member, authorized for the acting purpose, and SHALL resolve with that member as the actor: the member's owned skills, resource costs, SELF binding, practice award and disabled reasons apply.

#### Scenario: A companion heals the commander
- **WHEN** the commander has companion 艾拉 cast 治癒之光 on the commander out of combat
- **THEN** 艾拉's MP pays the cost, the commander's HP rises, and 艾拉 receives the practice award for 治癒之光

#### Scenario: SELF binds to the caster
- **WHEN** 艾拉 casts a SELF buff in the field
- **THEN** the buff lands on 艾拉, never on the commander

#### Scenario: A skill the caster does not own is refused
- **WHEN** the commander asks 卡恩 to cast a spell only 艾拉 owns
- **THEN** the cast is rejected with the existing unowned-skill reason and nothing changes

### Requirement: Companion field casts cost the commander's time and settle the party
A companion field cast SHALL charge the same command time as the commander casting the same skill, settled over the present party scope.

#### Scenario: Time cost equals the commander's
- **WHEN** 艾拉 casts a six-second field skill
- **THEN** the world clock advances exactly six seconds once, settling every present member

### Requirement: Unfit casters are refused with stable reasons
A caster that is knocked out SHALL be rejected with `member_cannot_act`; an absent caster with `member_not_present`; a non-member with `not_party_member`; a caster blocked by an existing action gate SHALL receive that gate's existing reason.

#### Scenario: A knocked-out caster is refused
- **WHEN** the commander asks 卡恩 at stored HP 1 to cast a field skill
- **THEN** the cast is rejected with `member_cannot_act` and nothing changes

### Requirement: The text cast command accepts a caster suffix
`cast <skill>[@<scale>][=<targets>] 由 <成員>` SHALL cast with the named member as caster outside combat; during an active combat session the suffix SHALL save that member's skill command through the existing actor command path instead of casting. Both player command documents SHALL describe the suffix.

#### Scenario: Text companion cast matches the rule
- **WHEN** the player types `cast healing_light=莉瑟 由 艾拉` out of combat
- **THEN** the result equals the rule-level companion cast with the same caster, target and scale

#### Scenario: In combat the suffix saves a draft entry
- **WHEN** the player types `cast healing_light=莉瑟 由 艾拉` during command selection
- **THEN** 艾拉's draft entry is saved exactly as `combat command` for 艾拉 would save it, and no time passes

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

### Requirement: Indivisible field actions complete before collapse
An initially eligible indivisible field action SHALL commit its full effects, costs and elapsed time once. Each present member SHALL settle its sampled interval posture/activity for that full duration, then enter forced sleep if depleted. No remainder SHALL become retrospective sleep recovery; prompts SHALL follow durable commit.

#### Scenario: Caster collapse
- **WHEN** an awake caster has 12 reserve units and completes a six-second field action
- **THEN** all effects and costs commit with six seconds; reserve clamps to zero and forced sleep begins afterwards with no recovered remainder

#### Scenario: Unselected companion collapse
- **WHEN** only an unselected awake companion has 12 units when another member casts the same action
- **THEN** the full caster result and six seconds commit; only the depleted companion collapses and sends a status notice without stealing control

#### Scenario: Already sleeping actor
- **WHEN** a sleeping actor attempts the action
- **THEN** preflight rejects with zero effects, costs and time
