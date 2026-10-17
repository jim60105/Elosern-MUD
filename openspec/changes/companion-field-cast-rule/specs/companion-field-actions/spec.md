# Spec Delta

## Purpose

Let a present party member, chosen explicitly by the player, perform out-of-combat field actions with that member's own skills, items, costs and growth.

## ADDED Requirements

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

### Requirement: Companions cannot open combat from the field
A field cast whose caster is not the commander SHALL NOT open combat: a monster anchor or a monster-normalizing target SHALL be rejected with `companion_cannot_open` before any resource, roll, session or clock access.

#### Scenario: A companion's attack spell on a monster is refused
- **WHEN** the commander asks 艾拉 to cast 冰錐術 at a monster in the room
- **THEN** the cast is rejected with `companion_cannot_open`, no combat session exists, and 艾拉's MP is unchanged

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
